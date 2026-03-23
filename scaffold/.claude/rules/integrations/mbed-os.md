---
paths:
  - "**/mbed*/**"
---

# Arm Mbed OS — External Platform Summary

## Current State
Mbed OS is Arm's open-source IoT operating system for Cortex-M microcontrollers. It includes mbedTLS as the default TLS stack under `connectivity/mbedtls/`. Mbed OS reached end of life in July 2026, but remains widely deployed on existing products. wolfSSL can replace mbedTLS for TLS operations.

## Architecture
- **Network stack**: `connectivity/netsocket/` provides `TLSSocket` and `TLSSocketWrapper` which abstract TLS over Mbed's socket API. These default to mbedTLS.
- **RTOS layer**: Mbed OS includes an RTOS kernel (based on CMSIS-RTOS) with `Thread`, `Mutex`, `Semaphore` primitives under `rtos/`.
- **Target BSPs**: `targets/` contains board support packages for hundreds of Cortex-M devices with hardware crypto drivers.
- **Build system**: Mbed CLI / CMake. Configuration via `mbed_app.json`.

## wolfSSL Integration Notes
- wolfSSL replaces mbedTLS by providing TLS operations through its own API or OpenSSL compat layer.
- Define `MBED` in `user_settings.h` to enable Mbed OS platform adaptations in wolfSSL.
- Threading: wolfSSL uses Mbed's `rtos::Mutex` when `MBED` is defined. Ensure `WOLFSSL_PTHREADS` is NOT set — Mbed uses its own threading API.
- Memory: Cortex-M devices are RAM-constrained (64KB–1MB typical). Use `--enable-smallstack` and tune `WOLFMEM_TRACK_MALLOC` for debugging. TLS handshake peak is ~8-12KB on Cortex-M4.
- Hardware crypto: Many Mbed-supported targets have hardware accelerators (STM32 HAL, NXP CAAM, etc.). wolfSSL's hardware crypto ports can be used alongside Mbed.
- Network socket: To use wolfSSL with Mbed's socket API, implement wolfSSL I/O callbacks (`wolfSSL_SetIOSend`/`wolfSSL_SetIORecv`) that call Mbed's `Socket::send()`/`Socket::recv()`.
- No configure/autotools: Mbed projects don't use autotools. All wolfSSL configuration is via `user_settings.h` with `WOLFSSL_USER_SETTINGS` defined.
- Common issue: Mbed's default heap allocator may fragment with wolfSSL's allocation pattern. Consider using wolfSSL's static memory feature (`--enable-staticmemory`) on very constrained targets.

## Key Files (in Mbed OS)
- `connectivity/mbedtls/` — Default TLS stack (what wolfSSL replaces)
- `connectivity/netsocket/include/netsocket/TLSSocket.h` — TLS socket abstraction
- `rtos/include/rtos/Mutex.h` — Threading primitives wolfSSL uses
- `targets/` — Board support packages with hardware crypto drivers
