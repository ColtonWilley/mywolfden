---
paths:
  - "**/threadx*"
  - "**/ThreadX*"
---

# ThreadX / Azure RTOS — wolfSSL Platform Guide

## 1. Overview

ThreadX (now marketed as Azure RTOS ThreadX by Microsoft) is a real-time operating system (RTOS) designed for embedded and IoT applications. wolfSSL supports ThreadX through the `THREADX` preprocessor define, which enables platform-specific adaptations within the wolfSSL source tree.

When `THREADX` is defined, wolfSSL adjusts its internal behavior to be compatible with the ThreadX environment, including threading primitives, memory management, and I/O abstractions appropriate for the RTOS context.

> **Note:** The source material available for this guide is limited to the presence of the `THREADX` define in `settings.h`. For full integration details, consult the [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/) and the wolfSSL embedded systems support resources.

---

## 2. Build Configuration

### Primary Define

The single required define to enable ThreadX support is:

```c
#define THREADX
```

This is listed in `wolfssl/wolfcrypt/settings.h` as a platform selector. It is commented out by default and must be explicitly enabled.

### How to Enable

**Option A — Define in `user_settings.h` (recommended for embedded targets):**

```c
#define WOLFSSL_USER_SETTINGS
```

Then in your `user_settings.h`:

```c
#define THREADX
```

**Option B — Define directly in `settings.h`:**

Uncomment the relevant line in `wolfssl/wolfcrypt/settings.h`:

```c
#define THREADX   /* was: */ /* #define THREADX */
```

**Option C — Pass via compiler flags:**

```
-DTHREADX
```

### Configure Flags

No specific `./configure` flags are documented in the available source material for ThreadX. ThreadX builds are typically performed without the autoconf/configure system, using an IDE or a custom makefile instead.

### IDE / Project Files

The wolfSSL source tree includes an `IDE/` directory that may contain project files for embedded toolchains commonly used with ThreadX (such as IAR EWARM or Rowley CrossWorks). Check the following defines, which may be relevant depending on your toolchain:

```c
/* For IAR EWARM */
#define WOLFSSL_IAR_ARM

/* For Rowley CrossWorks ARM */
#define WOLFSSL_ROWLEY_ARM
```

Consult the `IDE/` directory in the wolfSSL source distribution for any pre-built project files applicable to your hardware and toolchain combination.

---

## 3. Platform-Specific Features

### Threading

When `THREADX` is defined, wolfSSL is expected to use ThreadX threading primitives (mutexes, semaphores) in place of POSIX equivalents. The exact mapping is handled internally by wolfSSL's abstraction layer when the define is active.

### Networking

ThreadX is commonly paired with NetX or NetX Duo for TCP/IP networking. The available source material does not document a specific wolfSSL define for NetX/NetX Duo integration. You may need to implement a custom I/O callback layer (using `wolfSSL_SetIORecv` / `wolfSSL_SetIOSend`) to interface wolfSSL with the NetX stack.

### Hardware Cryptography

No hardware crypto acceleration specific to ThreadX is referenced in the available source material. If your ThreadX-based hardware platform includes a crypto accelerator (for example, on STM32 or NXP devices), additional platform-specific defines may be required alongside `THREADX`. Examples from `settings.h` that may be relevant depending on your hardware:

```c
#define WOLFSSL_STM32F2
#define WOLFSSL_STM32F4
#define WOLFSSL_STM32F7
```

Consult the wolfSSL manual for hardware acceleration options applicable to your specific SoC.

---

## 4. Common Issues

### Stack Size
Embedded RTOS environments including ThreadX require careful stack sizing for any thread that calls wolfSSL functions. TLS handshake operations in particular can require significant stack depth. It is recommended to:
- Allocate at least **8–16 KB** of stack for threads performing TLS operations (more may be required depending on cipher suites and key sizes).
- Test with stack overflow detection enabled in ThreadX during development.

### No `configure` System
ThreadX builds typically do not use the autoconf `./configure` system. All configuration must be done via `user_settings.h` or compiler defines. Ensure `WOLFSSL_USER_SETTINGS` is defined globally so that wolfSSL picks up your `user_settings.h` file.

### File System / Entropy
ThreadX environments may not have a standard file system or `/dev/random`-equivalent entropy source. You may need to provide a custom entropy/seed callback:
- Implement `wc_GenerateSeed()` for your hardware RNG, or
- Define `CUSTOM_RAND_GENERATE_BLOCK` and provide your own implementation.

### Limited Source Material
The wolfSSL source material available for this guide confirms only that `THREADX` is a recognized platform define. Detailed integration notes, example projects, and known bug workarounds beyond what is documented here should be verified against:
- The [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/)
- wolfSSL support: support@wolfssl.com
- The wolfSSL GitHub repository: https://github.com/wolfSSL/wolfssl

---

## 5. Example Configuration

The following is a minimal `user_settings.h` for a ThreadX target. Adjust feature flags based on your application requirements and available resources.

```c
/* user_settings.h — Minimal wolfSSL configuration for ThreadX / Azure RTOS */

#ifndef WOLFSSL_USER_SETTINGS_H
#define WOLFSSL_USER_SETTINGS_H

/* ---- Platform ---- */
#define THREADX

/* ---- Core TLS options ---- */
#define WOLFSSL_TLS13               /* Enable TLS 1.3 */
#define NO_OLD_TLS                  /* Disable TLS 1.0 / 1.1 */
#define WOLFSSL_NO_TLS12            /* Optional: disable TLS 1.2 if TLS 1.3 only */

/* ---- Memory ---- */
#define WOLFSSL_SMALL_STACK         /* Reduce stack usage */
/* #define WOLFSSL_STATIC_MEMORY */ /* Optional: use static memory pools */

/* ---- Cipher suite tuning ---- */
#define NO_DES3
#define NO_RC4
#define NO_MD4

/* ---- Entropy / RNG ---- */
/* Provide a custom seed function if no OS entropy source is available */
/* #define CUSTOM_RAND_GENERATE_BLOCK my_rng_function */

/* ---- Networking ---- */
/* Implement custom I/O callbacks for NetX / NetX Duo */
#define WOLFSSL_USER_IO

/* ---- Toolchain ---- */
/* Uncomment if using IAR EWARM */
/* #define WOLFSSL_IAR_ARM */

/* Uncomment if using Rowley CrossWorks */
/* #define WOLFSSL_ROWLEY_ARM */

#endif /* WOLFSSL_USER_SETTINGS_H */
```

Ensure that `WOLFSSL_USER_SETTINGS` is defined as a global compiler flag (e.g., `-DWOLFSSL_USER_SETTINGS`) so that wolfSSL loads this file during the build.
