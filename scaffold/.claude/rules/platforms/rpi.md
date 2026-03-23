---
paths:
  - "**/rpi*"
  - "**/raspberry*"
---

# Raspberry Pi + Pico — wolfSSL Platform Guide

## 1. Overview

The Raspberry Pi Pico is a microcontroller board based on the RP2040 chip, a dual-core ARM Cortex-M0+ processor developed by Raspberry Pi Ltd. wolfSSL supports the RP2040 platform through the `WOLFSSL_RP2040` define, enabling TLS/SSL and cryptographic operations on this resource-constrained embedded target.

> **Note:** The source material available for this guide is limited. The sections below reflect known metadata about this platform integration. For comprehensive details, consult the [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/) and the wolfSSL GitHub repository, particularly the `IDE/` and `examples/` directories.

---

## 2. Build Configuration

### Key Defines

| Define | Purpose |
|---|---|
| `WOLFSSL_RP2040` | Identifies the target as an RP2040-based platform (e.g., Raspberry Pi Pico) |

### Configure Flags

No specific `./configure` flags are documented in the available source material for this platform. The RP2040 is typically built using the **Raspberry Pi Pico SDK** (CMake-based) rather than the autoconf/configure build system.

### CMake-Based Build (Pico SDK)

The Raspberry Pi Pico SDK uses CMake as its primary build system. A typical integration involves:

1. Adding wolfSSL as a subdirectory or library target in your `CMakeLists.txt`.
2. Passing `WOLFSSL_RP2040` as a compile definition.
3. Providing a `user_settings.h` file to configure wolfSSL features appropriate for the constrained environment.

Example `CMakeLists.txt` snippet:

```cmake
add_subdirectory(wolfssl)

target_compile_definitions(wolfssl PUBLIC
    WOLFSSL_USER_SETTINGS
)

target_include_directories(wolfssl PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include  # directory containing user_settings.h
)
```

### user_settings.h

wolfSSL on the RP2040 is typically configured via `user_settings.h` rather than `./configure`. Define `WOLFSSL_USER_SETTINGS` to enable this file.

---

## 3. Platform-Specific Features

### Hardware Cryptography

The RP2040 does **not** include a dedicated hardware cryptographic accelerator. All cryptographic operations run in software on the Cortex-M0+ cores. wolfSSL's software implementations are used by default.

- No hardware AES, SHA, or RNG acceleration is available on the base RP2040.
- The RP2040 includes a hardware ROSC (Ring Oscillator) that may be used as an entropy source for the RNG, but care should be taken regarding its suitability for cryptographic use.

### Threading

The RP2040 is a dual-core processor. If using FreeRTOS or the Pico SDK's multicore support:

- Define `WOLFSSL_PTHREADS` or the appropriate RTOS threading layer if multi-threaded TLS sessions are required.
- For single-threaded applications, define `SINGLE_THREADED` to avoid threading overhead.

### Networking

The base Raspberry Pi Pico does **not** include built-in networking hardware. Networking support depends on the variant or add-on used:

- **Raspberry Pi Pico W**: Includes a CYW43439 Wi-Fi/Bluetooth chip. Network connectivity is provided through the Pico W SDK networking layer.
- wolfSSL's TLS stack can be used over any socket-compatible networking layer provided by the SDK or an RTOS (e.g., lwIP).

### Memory Constraints

The RP2040 has:
- 264 KB of on-chip SRAM
- 2 MB of external flash (on the Pico board)

wolfSSL must be configured conservatively to fit within these constraints. See the Example Configuration section below.

---

## 4. Common Issues

### Stack Size

The RP2040's limited RAM requires careful stack sizing. TLS handshakes can require significant stack space. Known considerations:

- Increase the default stack size for tasks performing TLS operations.
- If using FreeRTOS, set the TLS task stack to at least **8–12 KB** as a starting point, and adjust based on profiling.
- Insufficient stack space typically manifests as hard faults or corrupted state during handshakes.

### Flash and RAM Usage

- Use `NO_*` defines to disable unused algorithms and features.
- Enable `WOLFSSL_SMALL_STACK` to move large stack buffers to the heap, which can help with stack overflow issues at the cost of heap allocation overhead.
- Use `WOLFSSL_SP_MATH` or `WOLFSSL_SP_MATH_ALL` with small SP (Single Precision) options to reduce code size for public key operations.

### Entropy / RNG

- The RP2040 does not have a dedicated hardware TRNG. Ensure a suitable entropy source is configured.
- If using the Pico SDK, the `pico_rand` library may be used as an entropy source.
- Define a custom `wc_GenerateSeed()` implementation appropriate for your platform if the default is not suitable.

### No Native `time()` Support

- The RP2040 does not have a real-time clock by default. Certificate time validation requires a valid time source.
- Define `NO_ASN_TIME` to disable time-based certificate validation if no RTC is available, or provide a custom `time()` implementation.

### Cortex-M0+ Limitations

- The Cortex-M0+ does not support hardware division or certain instructions available on M3/M4/M7 cores.
- wolfSSL's software math libraries handle this, but performance will be lower than on higher-end Cortex-M cores.

---

## 5. Example Configuration

The following is a minimal `user_settings.h` suitable as a starting point for the Raspberry Pi Pico (RP2040). Adjust based on your application's requirements.

```c
/* user_settings.h — wolfSSL configuration for Raspberry Pi Pico (RP2040) */

#ifndef WOLFSSL_USER_SETTINGS_H
#define WOLFSSL_USER_SETTINGS_H

/* Platform identification */
#define WOLFSSL_RP2040

/* Use user_settings.h instead of configure-generated options */
/* (This file itself — ensure WOLFSSL_USER_SETTINGS is defined in build system) */

/* Single-threaded operation (remove if using RTOS with multiple TLS tasks) */
#define SINGLE_THREADED

/* Small stack: move large buffers to heap */
#define WOLFSSL_SMALL_STACK

/* Disable features not needed on embedded targets */
#define NO_FILESYSTEM
#define NO_WRITEV
#define NO_MAIN_DRIVER

/* Disable unused cipher suites and algorithms to save space */
#define NO_DES3
#define NO_RC4
#define NO_MD4
#define NO_PSK
#define NO_DSA
#define NO_DH

/* Enable only required TLS version(s) */
#define WOLFSSL_TLS13
#define NO_OLD_TLS

/* Use Single Precision math for smaller code size */
#define WOLFSSL_SP_MATH
#define WOLFSSL_SP_SMALL
#define SP_WORD_SIZE 32

/* ECC support (commonly used with TLS 1.3) */
#define HAVE_ECC
#define ECC_TIMING_RESISTANT

/* AES support */
#define NO_AES_192   /* optional: reduce AES key size support */

/* SHA support */
#define HAVE_SHA256
#define NO_SHA512    /* optional: disable if not needed */

/* Disable time-based certificate validation if no RTC is present */
/* #define NO_ASN_TIME */  /* Uncomment if no time source is available */

/* Custom entropy source — implement wc_GenerateSeed() for your platform */
/* #define CUSTOM_RAND_GENERATE_SEED */

#endif /* WOLFSSL_USER_SETTINGS_H */
```

---

## Additional Resources

- [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/)
- [wolfSSL GitHub Repository](https://github.com/wolfSSL/wolfssl) — check `IDE/` and `examples/` for any RP2040-specific project files
- [Raspberry Pi Pico SDK Documentation](https://datasheets.raspberrypi.com/pico/raspberry-pi-pico-c-sdk.pdf)
- [wolfSSL Support](https://www.wolfssl.com/contact/) — for platform-specific questions not covered by available documentation

> **Disclaimer:** This guide was generated from limited metadata. Always verify configuration options against the current wolfSSL source and documentation for your specific wolfSSL version.
