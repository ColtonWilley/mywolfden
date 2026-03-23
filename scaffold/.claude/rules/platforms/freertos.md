---
paths:
  - "**/FreeRTOS*/**"
  - "**/freertos*"
---

# FreeRTOS Platform Patterns

## Integration
- Define `FREERTOS` and `WOLFSSL_USER_SETTINGS` in user_settings.h
- wolfSSL uses FreeRTOS mutexes for thread safety (unless `SINGLE_THREADED`)
- Memory: uses `pvPortMalloc()` / `vPortFree()` by default with FreeRTOS
- Threading: `WOLFSSL_FREERTOS` enables FreeRTOS-specific threading primitives

## Common Issues

### Task Stack Sizing
**Most common FreeRTOS + wolfSSL issue.**
- TLS handshake with RSA 2048: need 24KB+ task stack
- TLS handshake with ECC P-256: need 16KB+ task stack
- With `WOLFSSL_SMALL_STACK`: reduces by ~30-40%
- `uxTaskGetStackHighWaterMark()` to check remaining stack at runtime
- `configCHECK_FOR_STACK_OVERFLOW` = 2 for best overflow detection

### Heap Exhaustion
- FreeRTOS heap implementations (heap_1 through heap_5) have different behaviors
- heap_4 recommended for wolfSSL (supports malloc/free with coalescence)
- `xPortGetFreeHeapSize()` / `xPortGetMinimumEverFreeHeapSize()` to monitor
- TLS handshake peak: 40-60KB heap (RSA), 20-30KB heap (ECC)

### Time Functions
- wolfSSL needs `time()` for certificate validation
- FreeRTOS doesn't provide `time()` by default
- Solutions:
  - Implement `time()` using `xTaskGetTickCount()` + known epoch offset
  - Use SNTP to set time at boot
  - Define `NO_ASN_TIME` to skip cert date validation
  - Define `USER_TICKS` for custom time source

### Mutex / Thread Safety
- `SINGLE_THREADED` — no mutexes, single-task only
- Default: uses FreeRTOS mutexes for session cache, CA cache
- `wolfSSL_SetMutexCb()` for custom mutex implementation
- **Common bug**: accessing same WOLFSSL* from multiple tasks → undefined behavior (one WOLFSSL* per task)

## Recommended user_settings.h for FreeRTOS
```c
#define FREERTOS
#define WOLFSSL_USER_SETTINGS
#define WOLFSSL_SMALL_STACK
#define NO_FILESYSTEM            // If no filesystem available
#define NO_WRITEV                // FreeRTOS doesn't have writev
#define HAVE_ECC                 // Prefer ECC for memory
#define HAVE_TLS_EXTENSIONS
#define HAVE_SNI
```
