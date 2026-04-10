# FreeRTOS Platform

> One-line summary: FreeRTOS-specific threading, heap, and task stack patterns for wolfSSL integration.

**When to read**: integrating wolfSSL with FreeRTOS on any MCU, debugging heap exhaustion or stack overflows during TLS, or selecting FreeRTOS heap implementation.

---

## Core Defines

| Define | Purpose |
|--------|---------|
| `FREERTOS` | Platform identification |
| `WOLFSSL_FREERTOS` | Enable FreeRTOS threading primitives (mutexes via `xSemaphore*`) |
| `WOLFSSL_SMALL_STACK` | Essential -- reduces task stack requirement by ~30-40% |

## Task Stack Sizing

| Scenario | Minimum Task Stack |
|----------|-------------------|
| TLS handshake, RSA 2048 | 24 KB+ (6144 words) |
| TLS handshake, ECC P-256 | 16 KB+ (4096 words) |
| With `WOLFSSL_SMALL_STACK` | ~30-40% less than above |

Use `uxTaskGetStackHighWaterMark()` at runtime to check remaining stack. Set `configCHECK_FOR_STACK_OVERFLOW = 2` for best overflow detection.

## Heap Implementation Selection

| Heap | Behavior | wolfSSL Suitability |
|------|----------|---------------------|
| heap_1 | No free; static only | NOT suitable -- wolfSSL frees memory |
| heap_2 | Free, no coalescence | Fragmentation risk with TLS sessions |
| heap_3 | Wraps libc malloc/free | OK if libc malloc available |
| **heap_4** | **Coalescing, single block** | **Recommended** |
| heap_5 | Coalescing, multiple regions | Good for split-memory targets |

Monitor with `xPortGetFreeHeapSize()` / `xPortGetMinimumEverFreeHeapSize()`.

**Realloc gotcha**: heap_4 and heap_5 have no `pvPortRealloc`. If wolfSSL needs `XREALLOC`, implement a wrapper using `pvPortMalloc` + `memcpy` + `vPortFree`.

## Threading Layer

wolfSSL maps its mutex abstraction to FreeRTOS semaphores:

| wolfSSL | FreeRTOS |
|---------|----------|
| `wc_InitMutex()` | `xSemaphoreCreateMutex()` |
| `wc_LockMutex()` | `xSemaphoreTake(mutex, portMAX_DELAY)` |
| `wc_UnLockMutex()` | `xSemaphoreGive()` |
| `wc_FreeMutex()` | `vSemaphoreDelete()` |

Requires `configUSE_MUTEXES = 1` in `FreeRTOSConfig.h`. For recursive locking, also set `configUSE_RECURSIVE_MUTEXES = 1`.

**Critical rule**: never share a single `WOLFSSL*` object across multiple tasks -- one `WOLFSSL*` per task.

## Required FreeRTOSConfig.h Settings

```c
#define configUSE_MUTEXES                1   // mandatory for wolfSSL threading
#define configUSE_RECURSIVE_MUTEXES      1   // if callbacks re-enter locks
#define configTOTAL_HEAP_SIZE            ((size_t)(64 * 1024))  // tune per target
#define configCHECK_FOR_STACK_OVERFLOW   2   // best overflow detection
#define configTICK_RATE_HZ               ((TickType_t)1000)
```

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| Hard fault / stack overflow in TLS task | Task stack too small | Increase `usStackDepth` in `xTaskCreate()` |
| `wc_InitMutex` returns NULL | `configUSE_MUTEXES` not 1, or heap exhausted | Check `FreeRTOSConfig.h` and heap watermark |
| Deadlock during TLS handshake | Recursive lock with non-recursive mutex | Enable `configUSE_RECURSIVE_MUTEXES` |
| `pvPortMalloc` returns NULL mid-handshake | Heap fragmentation or undersized | Switch to heap_4/5; increase `configTOTAL_HEAP_SIZE` |
| `XREALLOC` linker error | heap_4/5 lack `pvPortRealloc` | Implement wrapper or disable features needing realloc |
| Priority inversion stalling TLS | Mutex held by low-priority task | FreeRTOS mutexes have priority inheritance when `configUSE_MUTEXES = 1`; verify no raw semaphore used instead |

## What This File Does NOT Cover

FreeRTOS installation, specific MCU/board setup, TCP/IP stack integration (FreeRTOS+TCP, lwIP). See `embedded-common.md` for time source, RNG, and I/O callback patterns.
