---
paths:
  - "**/threadx*/**"
  - "**/ThreadX*/**"
---

# Eclipse ThreadX (Azure RTOS) — External Platform Summary

## Current State
ThreadX is a real-time operating system originally developed by Express Logic, acquired by Microsoft (Azure RTOS), and now maintained by Eclipse Foundation. It targets deeply embedded systems — medical devices, automotive, industrial controllers. ThreadX includes NetX Duo for TCP/IP networking and NetX Secure for TLS (which wolfSSL can replace).

## Architecture
- **Kernel**: `common/inc/tx_api.h` defines the ThreadX API — `tx_thread_create()`, `tx_mutex_get()`/`tx_mutex_put()`, `tx_semaphore_get()`, `tx_byte_allocate()`.
- **Ports**: `ports/` contains architecture-specific code (Cortex-M, Cortex-A, RISC-V, x86, etc.) for context switching and interrupt handling.
- **NetX Duo**: Separate component providing TCP/IP stack. wolfSSL integrates at the socket layer via NetX Duo BSD socket adapter or raw NetX API.
- **NetX Secure**: ThreadX's built-in TLS stack. wolfSSL replaces this entirely.

## wolfSSL Integration Notes
- Define `THREADX` in `user_settings.h` to enable ThreadX platform support in wolfSSL.
- Threading: wolfSSL maps its mutex operations to `tx_mutex_get()`/`tx_mutex_put()` when `THREADX` is defined.
- Memory allocation: wolfSSL uses `tx_byte_allocate()` from a ThreadX byte pool. Alternatively, use wolfSSL's static memory feature (`WOLFSSL_STATIC_MEMORY`) to avoid dynamic allocation entirely.
- NetX Duo integration: Implement wolfSSL I/O callbacks that call NetX Duo socket functions (`nx_tcp_socket_send()`/`nx_tcp_socket_receive()`). The `osp` repo may have example integration code.
- No filesystem typically: Use `wolfSSL_CTX_load_verify_buffer()` and `wolfSSL_CTX_use_certificate_buffer()` to load certs from C arrays compiled into flash.
- Stack sizing: ThreadX threads need sufficient stack for TLS handshake. 8-12KB minimum for the thread performing TLS on Cortex-M4. Use `WOLFSSL_SMALL_STACK` to reduce this.
- Hardware crypto: Many ThreadX targets have hardware accelerators. wolfSSL ports for STM32 HAL, NXP CAAM, Renesas SCE, etc. work alongside ThreadX.
- Time: wolfSSL needs a time source for certificate validation. Implement `XTIME()` or `XGMTIME()` using ThreadX timer services or an RTC.
- Common issue: ThreadX `tx_mutex_get()` with `TX_WAIT_FOREVER` can deadlock if wolfSSL is called from a callback context. Ensure TLS operations run in a proper thread context.

## Key Files (in ThreadX)
- `common/inc/tx_api.h` — ThreadX kernel API (threads, mutexes, memory)
- `ports/` — Architecture-specific context switch and timer code
- `common/src/tx_mutex_get.c` — Mutex implementation wolfSSL uses
- `common/src/tx_byte_allocate.c` — Memory allocator wolfSSL can use
