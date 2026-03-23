---
paths:
  - "**/port/**"
  - "**/IDE/**"
  - "**/user_settings*"
  - "**/callbacks*"
  - "**/*_uart*"
  - "**/*_spi*"
  - "**/*_i2c*"
---

# wolfSSL Embedded Implementation Methodology

This file covers transport integration, ISR patterns, shared-state
management, and embedded verification for hardware port implementations.
For general API implementation patterns (analog replication, OPENSSL_EXTRA
dual paths, public API conventions), see `coding-standards.md`.

## Transport / Environment Characterization

Before designing I/O callbacks or any transport integration, characterize the
transport along these dimensions. Each characteristic has direct design
implications — do not start coding until you can answer each question.

### Dimension Checklist

**Duplex mode**: Can TX and RX happen simultaneously?
- Full-duplex (e.g., TCP socket, separate UART TX/RX lines): TX and RX are
  independent. Send and receive callbacks operate without coordination.
- Half-duplex (e.g., shared UART line, shared SPI bus): sending blocks
  receiving. Long transmissions starve the receive path. Design implication:
  chunk large sends into bounded segments and yield to the receive path
  between segments. The chunk size is a design parameter — balance latency
  against throughput.

**Reliability**: Does the transport guarantee ordered, complete delivery?
- Reliable ordered stream (TCP, USB bulk, UART with hardware flow control):
  TLS is appropriate. Bytes arrive in order; lost bytes cause a detectable
  error.
- Unreliable / datagram (UDP, raw radio, lossy serial): DTLS is appropriate.
  TLS assumes reliability — if bytes are silently lost or reordered, TLS
  state machines will break in hard-to-diagnose ways.
- Partially reliable: characterize the actual failure modes. If data loss is
  possible but rare (e.g., UART without flow control, ring buffer overflow),
  decide whether the failure rate is acceptable for TLS or whether DTLS
  reliability mechanisms are needed.

**Blocking behavior**: Does the underlying I/O API block or return immediately?
- Non-blocking: I/O callbacks return WOLFSSL_CBIO_ERR_WANT_READ/WANT_WRITE
  when data is unavailable. The application event loop retries.
- Blocking with timeout: I/O callbacks wait internally up to a deadline, then
  return WANT_READ/WANT_WRITE if the deadline expires.
- Pure blocking: I/O callbacks block indefinitely. This is simpler but
  prevents the application from doing other work and eliminates the ability
  to implement timeouts at the wolfSSL layer.

**Buffer constraints**: What is the maximum message size the transport handles
in one operation?
- UART FIFO depth, USB endpoint buffer size, radio MTU, DMA transfer limit.
- wolfSSL default TLS record size is 16 KB. If the transport buffer is
  smaller, configure `HAVE_MAX_FRAGMENT` to negotiate smaller records.
  Without this, a single TLS record from the peer can overflow the receive
  buffer.
- For DTLS, set the MTU via `wolfSSL_dtls_set_mtu()` to match the transport.

**Interrupt context**: Does the transport use ISR-driven or DMA-driven I/O?
- If yes: identify EVERY variable shared between ISR and non-ISR context.
  See "Shared State Invariants" below.
- If no (polling or blocking): shared-state concerns are simpler but still
  apply if multiple threads access the transport.

### Design Decision: TLS vs DTLS

This is a forcing function — explicitly choose before proceeding and document
the choice in a comment at the top of the implementation file.

- Stream-oriented reliable transport → TLS
- Datagram-oriented or unreliable transport → DTLS
- Custom transport: characterize its actual delivery guarantees and map to
  the closest model. If the transport provides ordered reliable delivery
  (even if not TCP), TLS works. If not, DTLS.
- If unsure: default to DTLS. It is strictly more tolerant of transport
  imperfections. The cost is additional protocol overhead and code size.

## Non-Blocking Operation Completeness

### The Universal Rule

Every wolfSSL API that performs I/O can return `WOLFSSL_ERROR_WANT_READ` or
`WOLFSSL_ERROR_WANT_WRITE` when non-blocking I/O callbacks are configured.
This is NOT limited to data transfer — it applies to:

- `wolfSSL_connect()` / `wolfSSL_accept()` — handshake
- `wolfSSL_read()` / `wolfSSL_write()` — application data
- `wolfSSL_shutdown()` — close_notify exchange

**The most common oversight is `wolfSSL_shutdown()`.** Developers implement
non-blocking retry for connect and read/write but call shutdown once without
retry. Shutdown sends a close_notify alert and waits for the peer's response
— it does I/O and needs the same retry pattern.

### The Universal Retry+Timeout Pattern

Every non-blocking operation needs both a retry mechanism and a timeout
bound. An unbounded retry loop will hang forever if the peer disappears:

```
start = platform_get_time()
do {
    ret = wolfSSL_operation(ssl, ...)
    if (ret succeeds)
        break
    err = wolfSSL_get_error(ssl, ret)
    if (err != WANT_READ && err != WANT_WRITE)
        handle_error(err)
        break
    if (platform_get_time() - start > TIMEOUT)
        handle_timeout()
        break
    /* yield: feed watchdog, delay, or do other work */
} while (1)
```

Key points:
- The timeout must use wall-clock time, not iteration count — iteration
  speed varies by platform and transport speed.
- On embedded systems with watchdogs, the yield point inside the loop must
  feed the watchdog or the device will reset during long handshakes.
- Under RTOS, yield to the scheduler (`osDelay`, `vTaskDelay`) to avoid
  starving other tasks.

### Partial-Progress Tracking

When an I/O callback returns WOLFSSL_CBIO_ERR_WANT_WRITE, wolfSSL guarantees
it will retry with the **same buffer pointer and size** on the next call.
This guarantee enables asynchronous transmit patterns:

1. First call: start async TX (e.g., HAL_UART_Transmit_IT), record bytes
   in flight, return WANT_WRITE.
2. Subsequent calls: if TX still in progress, return WANT_WRITE. If TX
   completed (set by ISR), report the number of bytes sent.

The key invariant: the callback must track how many bytes are in-flight and
report them accurately when the async operation completes. wolfSSL advances
its internal offset by the reported count and calls again with the remainder.

## Shared State Invariants

### Identifying Shared State

When a system has multiple execution contexts (ISR + main thread, RTOS tasks,
library callbacks), explicitly list every piece of mutable state shared
between them:

- Data buffers (ring buffers, FIFOs)
- Status/progress flags (tx_complete, tx_inflight, rx_ready)
- Hardware peripheral state (mode registers, enable bits)
- Counters (bytes sent, bytes received, error counts)

If you cannot enumerate every shared variable, the design is not yet
complete enough to implement.

### The Reset Invariant

For every piece of shared state, define its **reset state** — the condition
it must return to when an operation completes or an error occurs. Then verify
that EVERY exit path restores it:

- Success path: operation completed normally
- Error path: transport error, HAL failure, timeout
- Abort path: re-initialization, connection teardown

**The most common failure pattern:** an error callback resets some flags but
not others. Example: a UART error callback clears RX state and re-arms
reception, but leaves TX-in-flight flags set. The send callback sees stale
"TX in progress" state and returns WANT_WRITE forever. The connection hangs
with no visible error.

Audit: for each shared variable, grep every callback (RX complete, TX
complete, error, abort) and verify the variable is handled in every one.

### Safe Re-initialization

When re-initializing a subsystem (reconnection, error recovery):

1. **Disable** the interrupt source or abort the DMA transfer
2. **Wait** for any in-progress operation to confirm completion or abort
3. **Zero** shared state (memset, individual assignments)
4. **Re-configure** the subsystem (set callbacks, prepare buffers)
5. **Re-enable** the interrupt source

Zeroing state while an ISR is active creates a race: the ISR reads partially
zeroed state, writes to a partially valid buffer, or increments a counter
that was just reset. The window is small but the consequence is data
corruption or a hard fault.

### ISR / Main Context Communication Patterns

- **ISR → main (data)**: lock-free single-producer single-consumer (SPSC)
  ring buffer. ISR writes to head; main reads from tail. Only head and tail
  indices need to be `volatile` — the buffer data is implicitly synchronized
  by the index ordering on architectures without store reordering (ARM
  Cortex-M). On architectures with weak memory ordering, add memory barriers
  between data write and index update.

- **ISR → main (status)**: `volatile` flags or counters. Keep them
  word-sized to ensure atomic reads/writes on the target architecture.
  Do not use structs or multi-word values for ISR-to-main signaling.

- **Main → ISR (control)**: avoid sending complex data. Set simple flags
  (abort, pause) that the ISR checks on its next invocation.

## Compile-Time Validation

### Required Configuration Guards

When your implementation depends on specific wolfSSL configuration macros,
validate at compile time. Silent misconfiguration — where the code compiles
but uses an unintended code path — is the hardest class of bug to diagnose
on embedded targets.

```c
#ifndef WOLFSSL_USER_IO
    #error "This implementation requires WOLFSSL_USER_IO — custom I/O " \
           "callbacks will not override default socket I/O without it"
#endif
```

### Common Guards for Embedded Implementations

- `WOLFSSL_USER_IO` — custom I/O callbacks. Without it, wolfSSL compiles in
  default BSD socket send/recv, which either fails to link on bare-metal or
  silently overrides your callbacks.
- `NO_FILESYSTEM` — buffer-based certificate loading. Without it, wolfSSL
  may try to use `fopen()` in paths you don't expect.
- `WOLFSSL_USER_SETTINGS` — user_settings.h inclusion. Without it, wolfSSL
  uses its default configuration which rarely matches embedded requirements.

### Feature Guards

If your implementation uses optional wolfSSL features, guard against their
absence:

```c
#ifndef HAVE_MAX_FRAGMENT
    #warning "HAVE_MAX_FRAGMENT not defined — TLS records may exceed " \
             "transport buffer capacity"
#endif
```

Use `#warning` (not `#error`) for features that are strongly recommended but
not strictly required.

## Cryptographic Primitive Reuse Patterns

### Init / Operation / Final Lifecycle

wolfCrypt primitives follow a consistent lifecycle:
- **Init** (e.g., `wc_HmacInit`, `wc_AesInit`) — allocate/prepare context
- **SetKey** — configure key and algorithm
- **Update** (0 or more) — feed data incrementally
- **Final** — produce output
- **Free** — release resources

### Reuse After Final

Callers frequently reuse primitive objects in tight loops WITHOUT calling
Init or Free between iterations. The most important examples:

- **TLS PRF / HKDF Expand**: Calls HMAC Update → Final repeatedly with
  the same key. Each iteration reuses the same Hmac object.
- **PBKDF2**: Similar iterative HMAC reuse.
- **CBC-MAC / CMAC**: Reuses cipher objects across multiple messages.

**Design implication for hardware acceleration**: After Final produces
output, the hardware state is consumed. The implementation must leave the
object in a state where the next Update/Final cycle works immediately
without the caller re-calling SetKey. If the hardware requires
re-initialization between uses, the implementation must handle this
internally — either eagerly (re-run setup in Final) or lazily (detect
and re-run setup at the start of the next Update).

### Verification

When implementing hardware acceleration for a primitive:
- **Search for loop callers**: Grep for the primitive's SetKey/Update/Final
  in `wolfcrypt/src/` and `src/` to find tight-loop usage patterns
- **Read the software path completely**: Before writing the hardware path,
  read the full software implementation of SetKey, Update, and Final.
  Understand what state flags it sets, clears, and checks — your hardware
  path must maintain the same state contracts
- **Match the software path's reuse contract**: If the software path
  supports SetKey-once-then-loop, the hardware path must too

## Observability

### Debug Output

Every implementation should include conditional debug output gated on
`DEBUG_WOLFSSL` or an application-specific debug macro:

```c
#ifdef DEBUG_WOLFSSL
    WOLFSSL_MSG("uart_send_cb: starting TX, bytes requested");
#endif
```

wolfSSL's internal debug infrastructure uses `WOLFSSL_MSG()` for text and
`WOLFSSL_BUFFER()` for hex dumps. Use the same macros for consistency — they
route through the same output mechanism the developer has already configured.

Include debug output at minimum for:
- Entry to each I/O callback with the requested size
- Completion of async operations (bytes transferred, status)
- Error conditions with both the wolfSSL error code and the transport status
- State transitions (e.g., switching duplex direction)

### Error Reporting

In error paths, report enough information to diagnose without a debugger:
- Which operation failed (function name or callback name)
- The wolfSSL error code (from `wolfSSL_get_error()`)
- The transport-level status (HAL return code, errno, RTOS error)
- Relevant state (bytes in flight, buffer occupancy, peripheral status)

On embedded targets without a console, consider storing the last N errors in
a circular buffer that can be inspected via debugger or read out over a
management interface.

## Implementation Verification Checklist

After writing implementation code, verify each item. These are ordered by
the frequency with which they are overlooked:

- [ ] `wolfSSL_shutdown()` is handled non-blocking (retry + timeout), not
      just called once
- [ ] Every retry loop has a wall-clock timeout, not just an iteration limit
- [ ] Every error callback / error path resets ALL shared state, not just the
      state for the operation that errored
- [ ] Re-initialization disables ISRs/DMA before zeroing shared state
- [ ] Transport characteristics (duplex, reliability, buffer size) are
      documented in a comment at the top of the file
- [ ] TLS vs DTLS choice is explicitly stated and justified
- [ ] Required configuration macros are validated with `#error` guards
- [ ] `DEBUG_WOLFSSL` enables meaningful diagnostic output
- [ ] If half-duplex: sends are chunked to avoid starving the receive path
- [ ] If buffered transport: `HAVE_MAX_FRAGMENT` is configured to keep TLS
      records within the buffer capacity
- [ ] The `void *ctx` parameter in I/O callbacks carries a context struct
      (not NULL) — enables multi-instance support and avoids globals
- [ ] If modeled on an analog function: all markers (`WOLFSSL_ABI`,
      `WOLFSSL_API`) on the analog are present on the new function
- [ ] If the analog has `#ifdef OPENSSL_EXTRA` code paths, the new
      function handles both native and OpenSSL-compat paths
- [ ] Every callee's current signature was verified — no stale call sites
      with wrong argument counts from signature changes
- [ ] If hardware-accelerating a primitive: the implementation supports
      the same reuse patterns as the software path (grep for loop callers)
- [ ] The hardware path maintains the same state flags and contracts as
      the software path (read the software path to identify them)
