---
paths:
  - "**/user_settings.h"
  - "**/IDE/**"
---

# Embedded Platform Integration Checklist

Cross-platform checklist for porting wolfSSL to any RTOS or bare-metal platform.
Extracted from patterns across all platform guides.

## 1. user_settings.h

Every non-autoconf build needs `user_settings.h` with `WOLFSSL_USER_SETTINGS` defined.

Key defines to set:
- `WOLFSSL_USER_SETTINGS` — tells wolfSSL to include user_settings.h
- `NO_FILESYSTEM` — almost always needed on embedded (no fopen/fread)
- `NO_WRITEV` — no writev() on most RTOS
- `SINGLE_THREADED` — or provide mutex callbacks (see Threading below)
- `WOLFSSL_SMALL_STACK` — use heap instead of large stack arrays
- `SMALL_SESSION_CACHE` or `NO_SESSION_CACHE` — reduce RAM usage

Template: start from `wolfssl/IDE/<platform>/user_settings.h` if one exists.

## 2. Threading / Mutex

Multi-threaded platforms need mutex callbacks OR define `SINGLE_THREADED`.

Callback registration:
```c
wolfSSL_SetAllocators(myMalloc, myFree, myRealloc);
```

Platform-specific mutex patterns:
- **FreeRTOS**: `xSemaphoreCreateMutex()`, `xSemaphoreTake()`/`xSemaphoreGive()`
  - Define: `FREERTOS`, `WOLFSSL_FREERTOS`
- **ThreadX**: `tx_mutex_create()`, `tx_mutex_get()`/`tx_mutex_put()`
  - Define: `THREADX`, `WOLFSSL_THREADX`
- **Zephyr**: `k_mutex_init()`, `k_mutex_lock()`/`k_mutex_unlock()`
  - Define: `WOLFSSL_ZEPHYR`
- **Mbed OS**: `rtos::Mutex`, `lock()`/`unlock()`
  - Define: `WOLFSSL_MBED`
- **VxWorks**: `semMCreate()`, `semTake()`/`semGive()`
  - Define: `VXWORKS`
- **Nucleus**: `NU_Create_Semaphore()`
  - Define: `WOLFSSL_NUCLEUS`
- **QNX**: Uses pthreads natively — no special defines needed

## 3. Memory Allocation

Most RTOS need custom allocators. Register via:
```c
wolfSSL_SetAllocators(myMalloc, myFree, myRealloc);
```

Or define at compile time:
```c
#define XMALLOC(s,h,t)  pvPortMalloc(s)   /* FreeRTOS */
#define XFREE(p,h,t)    vPortFree(p)
#define XREALLOC(p,n,h,t) /* implement or avoid */
```

Typical wolfSSL TLS session RAM: 30-50 KB (depends on features enabled).
Use `--enable-trackmemory` during development to measure peak usage.

## 4. I/O Callbacks (Network)

wolfSSL needs send/receive callbacks for the network stack:
```c
wolfSSL_CTX_SetIORecv(ctx, myRecv);
wolfSSL_CTX_SetIOSend(ctx, mySend);
```

Callback signatures:
```c
int myRecv(WOLFSSL* ssl, char* buf, int sz, void* ctx);
int mySend(WOLFSSL* ssl, char* buf, int sz, void* ctx);
```

Return values: bytes read/written on success, `WOLFSSL_CBIO_ERR_WANT_READ`/`WRITE` for non-blocking, `WOLFSSL_CBIO_ERR_GENERAL` for error.

Common patterns:
- **lwIP**: `lwip_recv()`/`lwip_send()` (raw sockets)
- **FreeRTOS+TCP**: `FreeRTOS_recv()`/`FreeRTOS_send()`
- **Zephyr**: `zsock_recv()`/`zsock_send()`
- **mbed TLS socket**: Wrap `TCPSocket::recv()`/`send()`

Define `WOLFSSL_USER_IO` to disable the default BSD socket I/O.

### Transport Design Considerations

Before writing I/O callbacks, characterize the transport:

1. **Duplex mode** — Can TX and RX happen simultaneously? Half-duplex
   transports (shared UART line, shared SPI bus) require coordination:
   long sends prevent receiving. Chunk large transmissions and yield
   to the receive path between chunks.

2. **Buffer budget** — What is the largest message the transport handles
   in one operation? Configure `HAVE_MAX_FRAGMENT` to match. Default TLS
   records are 16 KB — if the transport buffer is smaller, records will
   overflow it.

3. **Non-blocking completeness** — If returning `WOLFSSL_CBIO_ERR_WANT_READ`
   / `WANT_WRITE`, ALL wolfSSL operations must be retried: `wolfSSL_connect`,
   `wolfSSL_accept`, `wolfSSL_read`, `wolfSSL_write`, **and `wolfSSL_shutdown`**.
   Each retry loop needs a timeout to prevent infinite hangs.

4. **Shared state** — If using ISR-driven I/O, every variable shared between
   ISR and callback context needs an access protocol. Error callbacks must
   reset ALL shared state (TX and RX), not just partial state.

5. **Safe init/teardown** — Disable interrupts before zeroing shared state
   on re-init. ISRs still firing during memset creates race conditions.

## 5. Time Source

wolfSSL needs a time source for certificate validation. Options:

1. **Custom time callback** (preferred on embedded):
   ```c
   #define USER_TIME
   // implement: time_t myTime(time_t* t)
   ```

2. **Disable time checks** (development only — NOT production):
   ```c
   #define NO_ASN_TIME
   ```

3. **SNTP/NTP**: Many RTOS have NTP clients (lwIP SNTP, Zephyr NET_CONFIG). Sync time before wolfSSL_connect().

Common mistake: forgetting to set the RTC or call NTP before TLS handshake — leads to `ASN_AFTER_DATE_E` (-213) or `ASN_BEFORE_DATE_E` (-212).

## 6. Random Number Generation

wolfSSL REQUIRES a good entropy source. Options:

1. **Hardware RNG** (best): Most MCUs have a TRNG peripheral.
   ```c
   #define CUSTOM_RAND_GENERATE_BLOCK myRngFunc
   ```

2. **OS-provided**: FreeRTOS does NOT provide one — you must supply it.
   - Zephyr: `CONFIG_ENTROPY_GENERATOR=y` + `sys_csrand_get()`
   - ThreadX: Hardware-dependent

3. **NO_DEV_RANDOM**: Define this on all embedded (no /dev/urandom).

**NEVER** use `rand()`/`srand()` — this is a critical security vulnerability.

## 7. Certificate Loading (No Filesystem)

Without a filesystem, load certificates from C arrays:
```c
wolfSSL_CTX_load_verify_buffer(ctx, ca_cert, sizeof(ca_cert), SSL_FILETYPE_ASN1);
wolfSSL_CTX_use_certificate_buffer(ctx, dev_cert, sizeof(dev_cert), SSL_FILETYPE_ASN1);
wolfSSL_CTX_use_PrivateKey_buffer(ctx, dev_key, sizeof(dev_key), SSL_FILETYPE_ASN1);
```

Convert PEM to C array: `xxd -i cert.der > cert.h`
Or use DER format directly (smaller, no Base64 overhead).

To generate test certs at build time, use wolfSSL's `certs_test.h` for development.

## 8. Stack Sizing

wolfSSL can use significant stack space. Guidelines:
- **TLS client**: 8-16 KB stack minimum (with `WOLFSSL_SMALL_STACK`)
- **TLS server**: 12-24 KB stack minimum
- **Without SMALL_STACK**: 40+ KB may be needed

Reduce stack usage:
- Define `WOLFSSL_SMALL_STACK` — moves large arrays to heap
- Define `ALT_ECC_SIZE` — reduces ECC struct size
- Use `SP_MATH` (default in 5.x) instead of normal math
- Reduce `MAX_CHAIN_DEPTH` if deep cert chains aren't needed

FreeRTOS: Set task stack in `xTaskCreate()` accordingly.
Zephyr: Set `CONFIG_MAIN_STACK_SIZE` and thread stack sizes.

## 9. Endianness

wolfSSL auto-detects on most compilers, but for cross-compilation:
- Big-endian: Define `BIG_ENDIAN_ORDER`
- Little-endian: Usually auto-detected; define `LITTLE_ENDIAN_ORDER` if issues

## 10. Common Build Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `undefined reference to 'time'` | No time source | Define `USER_TIME` and implement callback |
| `undefined reference to 'send'`/`'recv'` | No socket I/O | Define `WOLFSSL_USER_IO` + set callbacks |
| `undefined reference to 'pthread_*'` | Threading assumed | Define `SINGLE_THREADED` or provide callbacks |
| `MEMORY_E` at runtime | Heap too small | Increase heap or enable `WOLFSSL_SMALL_STACK` |
| `RNG_FAILURE_E` (-199) | No entropy source | Implement `CUSTOM_RAND_GENERATE_BLOCK` |
| `ASN_AFTER_DATE_E` (-213) | System clock not set | Sync time via NTP before TLS connect |
| Stack overflow at runtime | Stack too small | Enable `WOLFSSL_SMALL_STACK`, increase task stack |
