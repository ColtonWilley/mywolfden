# Embedded Transport / Custom I/O

> One-line summary: wolfSSL I/O callback contracts, non-blocking retry rules, and DTLS differences that are not obvious from the API headers.

**When to read**: Implementing custom `wolfSSL_CTX_SetIORecv` / `wolfSSL_CTX_SetIOSend` callbacks, porting wolfSSL to a non-socket transport (UART, SPI, radio, USB), or debugging hangs in non-blocking TLS/DTLS.

---

## I/O Callback Registration

| Function | Purpose |
|----------|---------|
| `wolfSSL_CTX_SetIORecv(ctx, cb)` | Register receive callback (ctx-wide) |
| `wolfSSL_CTX_SetIOSend(ctx, cb)` | Register send callback (ctx-wide) |
| `wolfSSL_SetIOReadCtx(ssl, ptr)` | Per-session context passed to recv cb |
| `wolfSSL_SetIOWriteCtx(ssl, ptr)` | Per-session context passed to send cb |

Requires `WOLFSSL_USER_IO` to be defined. Without it, wolfSSL compiles in default BSD socket I/O that either fails to link on bare-metal or silently overrides your callbacks.

The `void *ctx` parameter should carry a context struct, not NULL. This enables multi-instance support and avoids globals.

## Callback Signatures and Return Values

Receive: `int myRecvCb(WOLFSSL *ssl, char *buf, int sz, void *ctx)`
Send:    `int mySendCb(WOLFSSL *ssl, char *buf, int sz, void *ctx)`

| Return value | Meaning |
|-------------|---------|
| `> 0` | Number of bytes transferred (may be less than `sz`) |
| `WOLFSSL_CBIO_ERR_WANT_READ` | No data available now, retry later |
| `WOLFSSL_CBIO_ERR_WANT_WRITE` | Cannot send now, retry later |
| `WOLFSSL_CBIO_ERR_GENERAL` | Fatal error, connection will be torn down |
| `WOLFSSL_CBIO_ERR_CONN_RST` | Connection reset |
| `WOLFSSL_CBIO_ERR_CONN_CLOSE` | Connection closed |

## Non-Blocking: The Universal Rule

**Every** wolfSSL API that performs I/O can return `WOLFSSL_ERROR_WANT_READ` or `WOLFSSL_ERROR_WANT_WRITE`. This includes:

- `wolfSSL_connect()` / `wolfSSL_accept()` (handshake)
- `wolfSSL_read()` / `wolfSSL_write()` (application data)
- `wolfSSL_shutdown()` (close_notify exchange)

The most common oversight is `wolfSSL_shutdown()`. Developers implement retry for connect/read/write but call shutdown once without retry. Shutdown does I/O and needs the same retry pattern.

## Retry + Timeout Pattern

Every non-blocking operation needs both retry and a wall-clock timeout (not iteration count -- speed varies by platform). An unbounded retry loop hangs if the peer disappears. The loop must: check `wolfSSL_get_error()` for WANT_READ/WANT_WRITE, break on other errors, enforce a wall-clock deadline, and yield (feed watchdog, `osDelay`, `vTaskDelay`) to avoid starving other tasks.

## Partial-Progress (Async TX) Contract

When a send callback returns `WOLFSSL_CBIO_ERR_WANT_WRITE`, wolfSSL guarantees it will retry with the **same buffer pointer and size** on the next call. This enables async transmit:

1. First call: start async TX (e.g., `HAL_UART_Transmit_IT`), return `WANT_WRITE`.
2. Subsequent calls: if TX still in progress, return `WANT_WRITE`. If complete, report bytes sent.

wolfSSL advances its internal offset by the reported count and calls again with the remainder. The callback must accurately track bytes in-flight.

## DTLS I/O Callback Differences

| Concern | TLS | DTLS |
|---------|-----|------|
| Transport model | Stream (TCP) | Datagram (UDP, raw radio) |
| MTU awareness | Not needed | Set via `wolfSSL_dtls_set_mtu()` |
| Record fragmentation | Handled by stream | Must fit in one datagram |
| Timeout/retransmit | Transport layer | DTLS layer (wolfSSL handles internally) |

For DTLS, the recv callback must return complete datagrams. Partial reads corrupt the DTLS record parser. The send callback must transmit each buffer as a single datagram.

## TLS vs DTLS Decision

- Reliable ordered transport (TCP, USB bulk, UART with flow control) --> TLS
- Unreliable / datagram transport (UDP, raw radio, lossy serial) --> DTLS
- If unsure, default to DTLS: more tolerant of transport imperfections at the cost of overhead and code size

## Transport Characterization

Before implementing callbacks, determine: (1) **Duplex** -- half-duplex requires chunking sends to yield to the receive path; (2) **Buffer limits** -- if smaller than 16 KB, configure `HAVE_MAX_FRAGMENT`; (3) **ISR-driven** -- if yes, use SPSC ring buffers for data, word-sized `volatile` flags for status. Re-initialization must disable ISR/DMA before zeroing shared state to avoid corruption races.

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| Connection hangs after transport error | Error callback resets RX state but leaves TX-in-flight flags set; send cb returns WANT_WRITE forever | Your send callback |
| `wolfSSL_shutdown()` blocks indefinitely | No non-blocking retry around shutdown | Application code |
| TLS record parse errors on constrained transport | Default 16 KB records overflow receive buffer; need `HAVE_MAX_FRAGMENT` | `user_settings.h` |
| Custom callbacks silently ignored | `WOLFSSL_USER_IO` not defined; default socket I/O compiled in | `user_settings.h` |
| DTLS record corruption | Recv callback returns partial datagram instead of complete one | Your recv callback |

## What This File Does NOT Cover

- BSD socket programming or standard POSIX I/O (wolfSSL handles that by default)
- Platform-specific HAL details (see `platforms/` knowledge files)
- Certificate loading and session configuration (separate concern from transport)
- DTLS 1.3 connection ID extensions
