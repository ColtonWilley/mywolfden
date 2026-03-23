---
paths:
  - "**/nucleus*"
  - "**/Nucleus*"
---

# Nucleus RTOS — wolfSSL Platform Guide

## 1. Overview

Nucleus RTOS is a real-time operating system developed by Mentor Graphics (now Siemens). wolfSSL provides support for Nucleus-based targets through dedicated platform defines that configure the library for the Nucleus environment.

Two distinct Nucleus variants are recognized in the wolfSSL source:

| Variant | Define |
|---|---|
| Nucleus 1.2 | `WOLFSSL_NUCLEUS_1_2` |
| Nucleus Plus 2.3 | `NUCLEUS_PLUS_2_3` |

The general `WOLFSSL_NUCLEUS` define is also referenced as the umbrella identifier for Nucleus platform builds. These defines allow wolfSSL's `settings.h` to apply appropriate platform-specific adaptations for the Nucleus environment.

> **Note:** The wolfSSL source material available for this guide is limited to the platform detection layer in `settings.h`. For full integration details, consult the [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/) and the wolfSSL support team.

---

## 2. Build Configuration

### Platform Defines

Select the define that matches your Nucleus version. These are commented out by default in `settings.h` and must be explicitly enabled.

| Define | Purpose |
|---|---|
| `WOLFSSL_NUCLEUS` | General Nucleus RTOS platform identifier |
| `WOLFSSL_NUCLEUS_1_2` | Targets Nucleus RTOS version 1.2 |
| `NUCLEUS_PLUS_2_3` | Targets Nucleus Plus version 2.3 |

### Enabling the Define

**Option A — Define in your project/IDE build settings (recommended):**

Add the appropriate define as a compiler preprocessor flag, for example:

```
-DWOLFSSL_NUCLEUS_1_2
```

or

```
-DNUCLEUS_PLUS_2_3
```

**Option B — Uncomment in `settings.h`:**

```c
/* For Nucleus 1.2 */
#define WOLFSSL_NUCLEUS_1_2

/* OR for Nucleus Plus 2.3 */
#define NUCLEUS_PLUS_2_3
```

**Option C — Define in a `user_settings.h` file (recommended for maintainability):**

Create a `user_settings.h` and define `WOLFSSL_USER_SETTINGS` in your build system, then place your platform and feature configuration in that file (see Section 5).

### Configure Flags

No specific `./configure` flags are documented in the available source material for Nucleus. Nucleus builds are typically performed without the autoconf/configure system, using an IDE or custom makefile instead. Check the wolfSSL manual for any configure-based options that may apply.

### IDE / Project Files

The wolfSSL repository may include IDE project files for embedded targets under the `IDE/` directory. Check for a Nucleus-specific subdirectory:

```
wolfssl/IDE/
```

If no Nucleus-specific project is present, you will need to create a custom project that:
- Adds all required wolfSSL source files (`wolfcrypt/src/*.c`, `src/*.c`)
- Adds the wolfSSL root and `wolfssl/` directories to the include path
- Defines `WOLFSSL_USER_SETTINGS` and provides a `user_settings.h`

---

## 3. Platform-Specific Features

### Threading

Nucleus RTOS provides its own threading and synchronization primitives. wolfSSL's mutex and threading abstraction layer will need to map to Nucleus APIs when multi-threaded use is required. The specific integration details are not fully documented in the available source material.

- If building single-threaded, define `SINGLE_THREADED` to disable wolfSSL's threading layer.
- If multi-threaded operation is needed, verify that the appropriate Nucleus mutex/semaphore wrappers are in place within wolfSSL's `wc_port.c` / `wolfio.c`.

### Networking (I/O)

wolfSSL's I/O layer must be connected to the Nucleus networking stack. This typically involves:

- Implementing custom `Send` and `Receive` callbacks via `wolfSSL_SetIOSend()` and `wolfSSL_SetIORecv()`
- Or ensuring the default BSD-socket-style I/O layer maps correctly to Nucleus TCP/IP socket calls

If Nucleus uses a non-standard socket API, define `WOLFSSL_USER_IO` and provide your own I/O callbacks.

### Hardware Cryptography

No hardware crypto acceleration specific to Nucleus is identified in the available source material. If your Nucleus-based hardware platform includes a crypto accelerator (e.g., from a supported silicon vendor), consult the wolfSSL manual for the relevant hardware acceleration define for that device.

---

## 4. Common Issues

### Selecting the Correct Variant Define

Using the wrong variant define (`WOLFSSL_NUCLEUS_1_2` vs. `NUCLEUS_PLUS_2_3`) may result in incorrect platform behavior. Confirm your exact Nucleus RTOS version before selecting a define.

### Stack Size

Embedded RTOS environments frequently have constrained stack sizes. wolfSSL cryptographic operations (particularly RSA and TLS handshakes) can require significant stack space. Recommendations:

- Allocate at least **8–16 KB** of stack for any task performing TLS operations (more may be needed for larger key sizes).
- Consider enabling `WOLFSSL_SMALL_STACK` to reduce per-function stack usage by moving large buffers to the heap.

### Heap Memory

wolfSSL uses dynamic memory allocation by default. Ensure your Nucleus heap is sized appropriately, or implement a custom allocator using `wolfSSL_SetAllocators()` if the default `malloc`/`free` are not available or suitable.

### File System / No Filesystem

If Nucleus does not provide a filesystem, define:

```c
#define NO_FILESYSTEM
```

This disables certificate and key loading from files; use the in-memory buffer APIs (`wolfSSL_CTX_load_verify_buffer()`, etc.) instead.

### Time / RNG

wolfSSL requires a source of time and entropy:

- If `time()` is unavailable, provide a custom time function or define `USER_TIME`.
- Ensure a hardware or software entropy source is available for the RNG. If the platform lacks `/dev/random` or equivalent, you may need to seed the RNG manually using `wc_RNG_DRBG_Reseed()` or a custom entropy callback.

---

## 5. Example Configuration

The following is a minimal `user_settings.h` for a Nucleus RTOS target. Adjust feature flags to match your application requirements.

```c
/* user_settings.h — wolfSSL configuration for Nucleus RTOS */

#ifndef WOLFSSL_USER_SETTINGS_H
#define WOLFSSL_USER_SETTINGS_H

/* ---- Select your Nucleus variant ---- */
/* Uncomment ONE of the following: */
#define WOLFSSL_NUCLEUS_1_2
/* #define NUCLEUS_PLUS_2_3 */

/* ---- Core platform settings ---- */
#define NO_FILESYSTEM          /* No file system available          */
#define SINGLE_THREADED        /* Remove if using RTOS threads      */
#define WOLFSSL_SMALL_STACK    /* Reduce stack usage                */

/* ---- Disable unused features to reduce code size ---- */
#define NO_OLD_TLS             /* Disable SSLv3, TLS 1.0, TLS 1.1  */
#define NO_DSA
#define NO_DH                  /* Remove if DH cipher suites needed */
#define NO_RC4
#define NO_MD4
#define NO_PSK                 /* Remove if PSK is needed           */

/* ---- Enable TLS 1.2 / 1.3 ---- */
#define WOLFSSL_TLS13
#define HAVE_TLS_EXTENSIONS
#define HAVE_SUPPORTED_CURVES
#define HAVE_EXTENDED_MASTER

/* ---- ECC support (optional) ---- */
#define HAVE_ECC
#define ECC_SHAMIR

/* ---- AES-GCM (optional) ---- */
#define HAVE_AESGCM

/* ---- Custom I/O (if Nucleus sockets differ from BSD) ---- */
/* #define WOLFSSL_USER_IO */

#endif /* WOLFSSL_USER_SETTINGS_H */
```

To use this file, define `WOLFSSL_USER_SETTINGS` in your compiler flags:

```
-DWOLFSSL_USER_SETTINGS
```

And ensure `user_settings.h` is on the compiler include path.

---

## Additional Resources

- [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/)
- [wolfSSL GitHub Repository](https://github.com/wolfSSL/wolfssl) — check `IDE/` and `wolfcrypt/src/port/` for any Nucleus-specific port files
- wolfSSL Support: [support@wolfssl.com](mailto:support@wolfssl.com)

> **Disclaimer:** The wolfSSL source material available for this guide covers only the platform detection defines in `settings.h`. Full Nucleus integration details — including threading wrappers, I/O port code, and any hardware acceleration — should be verified against the wolfSSL source tree and official documentation.
