---
paths:
  - "**/mbed*"
---

# Arm Mbed OS — wolfSSL Platform Guide

## 1. Overview

Arm Mbed OS is an open-source embedded operating system designed for Arm Cortex-M microcontrollers. It provides an RTOS, networking stack, hardware abstraction layer, and a C++ application framework targeted at IoT devices.

wolfSSL supports Mbed OS through the `MBED` preprocessor define, which activates platform-specific adaptations within the wolfSSL source tree. This define is listed alongside other embedded RTOS and platform targets in `wolfssl/wolfcrypt/settings.h`, confirming first-class recognition of the platform.

> **Note:** The source material available for this guide is limited to the platform detection entry in `settings.h`. For full integration details, consult the [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/) and the wolfSSL GitHub repository, particularly any files under `IDE/` or `mbed/` directories.

---

## 2. Build Configuration

### Required Define

To build wolfSSL for Mbed OS, define `MBED` before or during compilation:

```c
#define MBED
```

This is the single platform identifier recognized by `wolfssl/wolfcrypt/settings.h`. When defined, wolfSSL will apply any Mbed-specific conditional compilation blocks present in the source.

### Recommended Approach: `user_settings.h`

wolfSSL's preferred method for embedded targets is a custom `user_settings.h` file combined with the `WOLFSSL_USER_SETTINGS` define. This gives full control over which features are compiled in and avoids reliance on autoconf.

**Steps:**

1. Create a `user_settings.h` file in your project (see Section 5 for a minimal example).
2. Pass `WOLFSSL_USER_SETTINGS` as a global compiler define in your Mbed build system (e.g., `mbed_app.json` or `CMakeLists.txt`).
3. Define `MBED` within `user_settings.h` or as a global compiler flag.

### Configure Flags

No specific `./configure` flags are documented in the available source material for Mbed OS. The `./configure`-based build system is primarily used on POSIX hosts; for Mbed OS, the `user_settings.h` approach is strongly preferred.

### Build System Integration

Mbed OS uses either its own build system (Mbed CLI 1 / Mbed CLI 2 with CMake) or can be integrated via CMake directly. wolfSSL can be added as a library source directory. Ensure:

- All `.c` files under `wolfssl/src/` and `wolfssl/wolfcrypt/src/` are included in the build.
- The wolfSSL root directory is on the include path.
- `WOLFSSL_USER_SETTINGS` and `MBED` are defined globally.

---

## 3. Platform-Specific Features

### Threading

Mbed OS includes an RTOS (based on CMSIS-RTOS / RTX). wolfSSL's thread-safety features may be enabled if the Mbed threading layer is configured. The source material does not detail a dedicated Mbed threading abstraction within wolfSSL; check `wolfssl/wolfcrypt/wc_port.h` and `wolfssl/wolfcrypt/wc_port.c` for any `MBED`-gated threading code.

If thread safety is required, you may need to implement the mutex callbacks manually or verify that wolfSSL's CMSIS or generic RTOS mutex support covers your Mbed version.

### Networking

Mbed OS provides its own socket API (Mbed TLS-compatible BSD-like sockets). wolfSSL's I/O layer can be adapted using custom I/O callbacks (`wolfSSL_SetIORecv` / `wolfSSL_SetIOSend`) to interface with the Mbed networking stack. The source material does not indicate a built-in Mbed network layer within wolfSSL, so custom I/O callbacks are the recommended integration path.

### Hardware Cryptography

Mbed OS targets a wide range of Arm Cortex-M devices, many of which include hardware cryptographic accelerators (e.g., STM32 crypto peripherals, NXP LTC, Arm CryptoCell). wolfSSL supports several of these independently via their own defines (e.g., `WOLFSSL_STM32F4`, `WOLFSSL_CRYPTOCELL`). These are separate from the `MBED` define and may be combined with it if your target hardware supports acceleration.

The source material does not document a unified Mbed hardware crypto abstraction within wolfSSL. Hardware acceleration should be enabled through the appropriate device-specific define in addition to `MBED`.

---

## 4. Common Issues

### Stack Size

Embedded TLS operations (especially RSA and ECC key generation/operations) require significant stack space. Mbed OS default thread stack sizes may be insufficient. Recommended mitigations:

- Increase the main thread or application thread stack size in `mbed_app.json`.
- Use wolfSSL's `SMALL_STACK` option (`#define WOLFSSL_SMALL_STACK`) to move large buffers to the heap instead of the stack.
- Monitor stack usage during development with Mbed OS stack statistics APIs.

### Heap Size

TLS handshakes allocate heap memory for certificates, keys, and session state. Ensure your target's heap is sized appropriately. On constrained devices, enable options such as:

- `NO_SESSION_CACHE` — disables the TLS session cache
- `WOLFSSL_SMALL_STACK` — reduces per-operation stack/heap peaks
- Disabling unused algorithms (e.g., `NO_DES3`, `NO_RC4`, `NO_MD4`)

### C++ Compatibility

Mbed OS applications are typically C++. wolfSSL is a C library. Ensure wolfSSL headers are included with `extern "C"` guards where needed, or include them as:

```cpp
extern "C" {
    #include <wolfssl/ssl.h>
}
```

wolfSSL headers include these guards internally, but verify this if you encounter linker or symbol errors.

### Time and Entropy

wolfSSL requires:

- A working `time()` function or a custom `XTIME` implementation.
- A source of entropy for the RNG (`wc_GenerateSeed`).

Mbed OS provides both, but you may need to wire them into wolfSSL's port layer if the default POSIX implementations are not available. Check `wolfssl/wolfcrypt/wc_port.c` for `MBED`-specific implementations, and provide custom versions if needed.

### File System / Certificate Loading

Many Mbed OS targets do not have a file system. Use wolfSSL's buffer-based certificate and key loading APIs (`wolfSSL_CTX_load_verify_buffer`, `wolfSSL_CTX_use_certificate_buffer`, etc.) rather than file-based APIs.

---

## 5. Example Configuration

The following is a minimal `user_settings.h` for an Mbed OS target. Adjust feature flags based on your application requirements and available memory.

```c
/* user_settings.h — wolfSSL minimal configuration for Mbed OS */

#ifndef WOLFSSL_USER_SETTINGS_H
#define WOLFSSL_USER_SETTINGS_H

/* ---- Platform ---- */
#define MBED

/* ---- Core build options ---- */
#define WOLFSSL_SMALL_STACK          /* Move large buffers to heap */
#define SINGLE_THREADED              /* Remove if using RTOS threads */

/* ---- Reduce code size ---- */
#define NO_FILESYSTEM                /* No file system; use buffer APIs */
#define NO_SESSION_CACHE             /* Disable TLS session cache */
#define NO_INLINE                    /* Optional: reduce code size */

/* ---- Disable unused algorithms ---- */
#define NO_DES3
#define NO_RC4
#define NO_MD4
#define NO_PSK
#define NO_DSA
#define NO_OLD_TLS                   /* Disable SSLv3, TLS 1.0, TLS 1.1 */

/* ---- Enable TLS 1.2 / 1.3 ---- */
#define WOLFSSL_TLS13
#define HAVE_TLS_EXTENSIONS
#define HAVE_SUPPORTED_CURVES

/* ---- ECC support ---- */
#define HAVE_ECC
#define ECC_SHAMIR                   /* Faster ECC; uses more RAM */

/* ---- SHA-256 (required for TLS 1.3) ---- */
/* Enabled by default; no define needed */

/* ---- RNG ---- */
/* Ensure wc_GenerateSeed is implemented for your target */

#endif /* WOLFSSL_USER_SETTINGS_H */
```

To activate this file, define `WOLFSSL_USER_SETTINGS` globally in your build system. For Mbed CLI 2 / CMake, add to `mbed_app.json`:

```json
{
    "target_overrides": {
        "*": {
            "target.macros_add": ["WOLFSSL_USER_SETTINGS", "MBED"]
        }
    }
}
```

---

## Further Resources

- [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/)
- [wolfSSL GitHub Repository](https://github.com/wolfSSL/wolfssl) — check `IDE/` and any `mbed` subdirectories for example projects
- [wolfSSL Support](https://www.wolfssl.com/contact/) — for platform-specific integration assistance
