# Embedded Common Patterns

> One-line summary: cross-platform embedded constraints and wolfSSL configuration patterns that apply regardless of specific RTOS or MCU.

**When to read**: any embedded/RTOS port, bare-metal integration, or when diagnosing memory/stack/RNG failures on constrained targets.

---

## WOLFSSL_USER_SETTINGS Pattern

Every non-autoconf build requires `user_settings.h` with `WOLFSSL_USER_SETTINGS` defined globally. Start from `wolfssl/IDE/<platform>/user_settings.h` if one exists.

## Essential Embedded Defines

| Define | Purpose |
|--------|---------|
| `WOLFSSL_USER_SETTINGS` | Include user_settings.h instead of autoconf |
| `NO_FILESYSTEM` | Disable fopen/fread -- load certs from C arrays via `*_buffer()` APIs |
| `NO_WRITEV` | No writev() on most RTOS |
| `SINGLE_THREADED` | Skip mutex layer (or provide mutex callbacks instead) |
| `WOLFSSL_SMALL_STACK` | Move large arrays from stack to heap -- critical on embedded |
| `NO_DEV_RANDOM` | No /dev/urandom -- required on all embedded |
| `WOLFSSL_USER_IO` | Disable default BSD socket I/O; use custom send/recv callbacks |
| `ALT_ECC_SIZE` | Reduce ECC point struct size |
| `SMALL_SESSION_CACHE` / `NO_SESSION_CACHE` | Reduce RAM for session storage |

## Stack Sizing Guidelines

| Scenario | Minimum Stack |
|----------|---------------|
| TLS client with `WOLFSSL_SMALL_STACK` | 8-16 KB |
| TLS server with `WOLFSSL_SMALL_STACK` | 12-24 KB |
| Without `SMALL_STACK` | 40+ KB |

Reduce further with: `ALT_ECC_SIZE`, SP math (default in 5.x), lower `MAX_CHAIN_DEPTH`.

## Heap Budget

| Operation | Approximate Peak Heap |
|-----------|----------------------|
| TLS handshake (RSA 2048) | 40-60 KB |
| TLS handshake (ECC P-256) | 20-30 KB |
| Steady-state TLS session | 30-50 KB |

Use `--enable-trackmemory` during development to measure actual peak usage.

## Time Source

wolfSSL requires a time source for certificate validation. Three options:

1. **Custom callback** (preferred): `#define USER_TIME` and implement `time_t myTime(time_t* t)`
2. **NTP/SNTP**: Sync time before `wolfSSL_connect()`. Most RTOS have NTP clients.
3. **Disable checks** (dev only): `#define NO_ASN_TIME`

Missing time setup is the #1 cause of `ASN_AFTER_DATE_E` (-213) / `ASN_BEFORE_DATE_E` (-212).

## Random Number Generation

wolfSSL REQUIRES a cryptographic entropy source. Never use `rand()`/`srand()`.

- **Hardware TRNG** (preferred): `#define CUSTOM_RAND_GENERATE_BLOCK myRngFunc`
- **OS-provided**: platform-dependent (FreeRTOS has none; Zephyr has `CONFIG_ENTROPY_GENERATOR`)

## Threading / Mutex Callbacks

| Platform | Defines | Mutex API |
|----------|---------|-----------|
| FreeRTOS | `FREERTOS`, `WOLFSSL_FREERTOS` | `xSemaphoreCreateMutex()` |
| Zephyr | `WOLFSSL_ZEPHYR` | `k_mutex_init()` |
| ThreadX | `THREADX`, `WOLFSSL_THREADX` | `tx_mutex_create()` |
| VxWorks | `VXWORKS` | `semMCreate()` |

## I/O Callback Design

Register custom send/recv: `wolfSSL_CTX_SetIOSend(ctx, fn)` / `wolfSSL_CTX_SetIORecv(ctx, fn)`.

Critical transport considerations:
- **Half-duplex** (shared UART/SPI): chunk large sends, yield to receive path between chunks
- **Buffer budget**: configure `HAVE_MAX_FRAGMENT` to match transport buffer (default TLS record is 16 KB)
- **Non-blocking**: ALL wolfSSL operations must be retried (`connect`, `accept`, `read`, `write`, `shutdown`)
- **ISR-driven I/O**: protect all shared state; disable interrupts before zeroing state on re-init

## Certificate Loading Without Filesystem

```c
wolfSSL_CTX_load_verify_buffer(ctx, ca_cert, sizeof(ca_cert), SSL_FILETYPE_ASN1);
wolfSSL_CTX_use_certificate_buffer(ctx, dev_cert, sizeof(dev_cert), SSL_FILETYPE_ASN1);
wolfSSL_CTX_use_PrivateKey_buffer(ctx, dev_key, sizeof(dev_key), SSL_FILETYPE_ASN1);
```

Use DER format (smaller than PEM). Convert with `xxd -i cert.der > cert.h`.

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| `MEMORY_E` at runtime | Heap too small or fragmented | Increase heap, enable `WOLFSSL_SMALL_STACK` |
| `RNG_FAILURE_E` (-199) | No entropy source configured | Implement `CUSTOM_RAND_GENERATE_BLOCK` |
| `ASN_AFTER_DATE_E` (-213) | System clock not set / no NTP | Sync time before TLS, or implement `USER_TIME` |
| Stack overflow / hard fault during handshake | Task stack too small | Enable `WOLFSSL_SMALL_STACK`, increase task stack |
| `undefined reference to 'time'` | No time source linked | Define `USER_TIME` and implement callback |
| `undefined reference to 'send'`/`'recv'` | No socket I/O | Define `WOLFSSL_USER_IO` + register callbacks |
| `undefined reference to 'pthread_*'` | Threading assumed | Define `SINGLE_THREADED` or provide callbacks |

## What This File Does NOT Cover

Platform-specific details (HW accel, variant tables, HAL integration) -- see individual platform files. Standard Linux/POSIX builds. Algorithm selection guidance.
