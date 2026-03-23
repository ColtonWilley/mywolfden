---
paths:
  - "**/FreeRTOS*/**"
---

# FreeRTOS Kernel — External Platform Summary

## Current State

- **Latest stable release:** FreeRTOS Kernel V11.1.0, part of FreeRTOS 202406.00 LTS
- **Latest development version:** V11.3.0 (released March 2026), available on `main` branch
- **Repository:** https://github.com/FreeRTOS/FreeRTOS-Kernel
- **License:** MIT
- **CI:** CMock unit tests with codecov coverage tracking on `main`
- The kernel itself is used as a submodule within the broader [FreeRTOS/FreeRTOS](https://github.com/FreeRTOS/FreeRTOS) repository, which contains demo projects

---

## Architecture

### Core Kernel Files
The kernel is contained in three portable files at the repository root:
- `tasks.c` — task scheduler, context switching, priority management
- `queue.c` — queues, mutexes, semaphores (underlying mechanism for `xSemaphoreCreateMutex`)
- `list.c` — linked list primitives used internally
- `croutine.c` — optional co-routine support (rarely used; avoid in TLS contexts due to limited stack)

### Portability Layer (`portable/`)
- Compiler/architecture-specific `port.c` and assembly files live under `portable/<COMPILER>/<ARCH>/`
- Supported toolchains: GCC, IAR, Keil/RVDS, ARMClang, CCS, CodeWarrior, MSVC/MinGW, and others
- Memory management implementations are in `portable/MemMang/` (heap_1 through heap_5)

### Memory Management
Selected via `FREERTOS_HEAP` CMake variable (or by including the appropriate `heap_N.c`):
| Heap | Behavior | wolfSSL suitability |
|------|----------|---------------------|
| heap_1 | No free; static allocation only | Not suitable — wolfSSL frees memory |
| heap_2 | Free allowed, no coalescence | Fragmentation risk with TLS sessions |
| heap_3 | Wraps system `malloc`/`free` | Suitable if libc malloc is available |
| heap_4 | Coalescing allocator, single block | **Recommended** for wolfSSL |
| heap_5 | Coalescing, multiple memory regions | Suitable for split-memory targets |

### Synchronization Primitives Relevant to wolfSSL
- `xSemaphoreCreateMutex()` — creates a non-recursive mutex (binary semaphore backed by queue)
- `xSemaphoreCreateRecursiveMutex()` — recursive mutex; required if wolfSSL callbacks re-enter the same lock
- `xSemaphoreTake()` / `xSemaphoreGive()` — acquire/release
- All semaphore APIs are defined in `include/semphr.h` as macros over queue primitives in `queue.c`
- Mutexes support priority inheritance; relevant when wolfSSL tasks run at mixed priorities

### Task Model
- Each FreeRTOS task has its own stack; wolfSSL TLS operations require substantial stack depth (typically 8–20 KB depending on cipher suite and key size)
- No shared heap by default — `pvPortMalloc`/`vPortFree` must be thread-safe; heap_4 and heap_5 use a critical section internally for thread safety

---

## wolfSSL Integration Notes

### Build System

**CMake (recommended):**
```cmake
# Pull in FreeRTOS kernel
FetchContent_Declare(freertos_kernel
  GIT_REPOSITORY https://github.com/FreeRTOS/FreeRTOS-Kernel.git
  GIT_TAG        V11.1.0
)
set(FREERTOS_HEAP "4" CACHE STRING "" FORCE)
set(FREERTOS_PORT "GCC_ARM_CM33_NTZ_NONSECURE" CACHE STRING "" FORCE)
FetchContent_MakeAvailable(freertos_kernel)

# wolfSSL must link against freertos_kernel and freertos_kernel_include
target_link_libraries(wolfssl PRIVATE freertos_kernel freertos_kernel_include)
```

**Manual/Makefile builds:**
- Include `tasks.c`, `queue.c`, `list.c`, the selected `heap_N.c`, and the port-specific `port.c`
- Add `include/` and the port directory to include paths
- `FreeRTOSConfig.h` must be on the include path before any FreeRTOS header is included

### Required `FreeRTOSConfig.h` Settings for wolfSSL

```c
/* Mutex support — mandatory for wolfSSL threading layer */
#define configUSE_MUTEXES                    1
#define configUSE_RECURSIVE_MUTEXES          1  /* if using recursive mutex variant */

/* Sufficient heap for TLS sessions */
#define configTOTAL_HEAP_SIZE                ((size_t)(64 * 1024))  /* tune per target */

/* Stack overflow detection — helps diagnose wolfSSL stack exhaustion */
#define configCHECK_FOR_STACK_OVERFLOW       2

/* Tick rate affects xSemaphoreTake timeout calculations */
#define configTICK_RATE_HZ                   ((TickType_t)1000)
```

### wolfSSL Threading Layer (`WOLFSSL_FREERTOS`)

wolfSSL's FreeRTOS threading wrappers (`wolfssl/wolfcrypt/wc_port.h`, `wolfcrypt/src/wc_port.c`) map to:
| wolfSSL abstraction | FreeRTOS API |
|---------------------|--------------|
| `wolfSSL_Mutex` | `SemaphoreHandle_t` |
| `wc_InitMutex()` | `xSemaphoreCreateMutex()` |
| `wc_LockMutex()` | `xSemaphoreTake(mutex, portMAX_DELAY)` |
| `wc_UnLockMutex()` | `xSemaphoreGive()` |
| `wc_FreeMutex()` | `vSemaphoreDelete()` |

Enable with: `#define WOLFSSL_FREERTOS` in `user_settings.h` or as a compiler define.

### Memory Allocation Hooks

wolfSSL uses `XMALLOC`/`XFREE`/`XREALLOC`. On FreeRTOS these must map to `pvPortMalloc`/`vPortFree`:

```c
/* In user_settings.h */
#define XMALLOC(s, h, t)     pvPortMalloc((s))
#define XFREE(p, h, t)       vPortFree((p))
#define XREALLOC(p, n, h, t) wolfssl_pvPortRealloc((p), (n))  /* heap_4/5 have no realloc; implement manually */
```

**Note:** `heap_4` and `heap_5` do not provide `pvPortRealloc`. If wolfSSL is built with features requiring `XREALLOC` (e.g., dynamic buffer resizing), a wrapper must be implemented using `pvPortMalloc` + `memcpy` + `vPortFree`.

### TCP/IP Stack Hooks

wolfSSL's I/O callbacks (`EmbedSend`/`EmbedReceive`) expect a BSD-socket-like interface. On FreeRTOS this is typically provided by:
- **FreeRTOS+TCP** — provides `FreeRTOS_send()`, `FreeRTOS_recv()`, `FreeRTOS_socket()` with BSD-compatible signatures; wolfSSL's default callbacks work with minor adaptation
- **lwIP** — requires `WOLFSSL_LWIP` define; uses lwIP's `lwip/sockets.h` API

For FreeRTOS+TCP specifically:
```c
/* In user_settings.h */
#define FREERTOS_TCP
/* wolfSSL will use FreeRTOS_send/recv via its EmbedSend/EmbedReceive callbacks */
```

Custom I/O callbacks can be registered per-session with `wolfSSL_SetIOSend()` / `wolfSSL_SetIORecv()` if the TCP stack does not provide a socket abstraction.

### Common Integration Issues

| Symptom | Likely Cause | Resolution |
|---------|-------------|------------|
| Hard fault / stack overflow in TLS task | wolfSSL task stack too small | Increase `usStackDepth` in `xTaskCreate`; minimum ~8 KB for RSA-2048, more for larger keys |
| `wc_InitMutex` returns error / NULL handle | `configUSE_MUTEXES` not set to 1, or heap exhausted before mutex creation | Verify `FreeRTOSConfig.h`; check heap watermark with `xPortGetFreeHeapSize()` |
| Deadlock during TLS handshake | Recursive lock attempt with non-recursive mutex | Set `configUSE_RECURSIVE_MUTEXES 1` and use `xSemaphoreCreateRecursiveMutex()` |
| `pvPortMalloc` returns NULL mid-handshake | Heap fragmentation or insufficient `configTOTAL_HEAP_SIZE` | Switch to heap_4 or heap_5; increase heap size; use `xPortGetMinimumEverFreeHeapSize()` to profile |
| `XREALLOC` linker error or crash | heap_4/5 lack `pvPortRealloc` | Implement a wrapper or disable features requiring realloc |
| I/O callback returns `WOLFSSL_CBIO_ERR_WANT_READ` loop | Non-blocking socket with no yield | Add `taskYIELD()` or a short `vTaskDelay(1)` in the I/O callback on `WANT_READ` |
| Priority inversion stalling TLS task | Mutex held by low-priority task, high-priority TLS task blocked | FreeRTOS mutexes support priority inheritance by default when `configUSE_MUTEXES 1`; verify no semaphore (non-mutex) is used instead |

---

## Key Files

| File/Path | Purpose |
|-----------|---------|
| `include/FreeRTOS.h` | Master include; pulls in `FreeRTOSConfig.h` and port headers; must be included before all other FreeRTOS headers |
| `include/semphr.h` | Semaphore/mutex API macros — `xSemaphoreCreateMutex`, `xSemaphoreTake`, `xSemaphoreGive`, `vSemaphoreDelete` |
| `include/queue.h` | Underlying queue implementation backing all semaphore/mutex operations |
| `include/task.h` | Task creation (`xTaskCreate`), stack size parameter, `vTaskDelay`, `taskYIELD` |
| `include/portable.h` | Declares `pvPortMalloc` / `vPortFree`; included transitively via `FreeRTOS.h` |
| `portable/MemMang/heap_4.c` | Recommended heap implementation for wolfSSL; thread-safe via critical section |
| `portable/MemMang/heap_5.c` | Multi-region heap; use on targets with non-contiguous RAM |
| `portable/<COMPILER>/<ARCH>/port.c` | Architecture port; defines `portENTER_CRITICAL` / `portEXIT_CRITICAL` used by heap allocators |
| `template_configuration/FreeRTOSConfig.h` | Reference configuration template; starting point for new projects |
| `tasks.c` | Implements priority inheritance for mutexes; relevant to wolfSSL multi-task scenarios |
