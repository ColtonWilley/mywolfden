---
paths:
  - "**/vxworks*"
  - "**/VxWorks*"
---

# VxWorks — wolfSSL Platform Guide

## 1. Overview

VxWorks is a real-time operating system (RTOS) developed by Wind River Systems, widely used in embedded, aerospace, defense, and industrial applications. wolfSSL supports VxWorks through the `WOLFSSL_VXWORKS` define, which enables platform-specific adaptations within the wolfSSL source tree.

When `WOLFSSL_VXWORKS` is defined, wolfSSL adjusts its internal behavior to accommodate the VxWorks environment, including its threading model, networking stack, and system API differences compared to standard POSIX or desktop platforms.

> **Note:** The source material available for this guide is limited to the presence of the `WOLFSSL_VXWORKS` define in `settings.h`. For comprehensive integration details, consult the [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/) and the wolfSSL support team.

---

## 2. Build Configuration

### Primary Define

To build wolfSSL for VxWorks, define the following in your build system or `user_settings.h`:

```c
#define WOLFSSL_VXWORKS
```

This define is listed in `wolfssl/wolfcrypt/settings.h` as the canonical flag for VxWorks builds. It is commented out by default and must be explicitly enabled.

### Recommended Approach: `user_settings.h`

wolfSSL recommends using a `user_settings.h` file for embedded and RTOS targets rather than relying on configure-time flags. To activate this mechanism, define:

```c
#define WOLFSSL_USER_SETTINGS
```

This causes wolfSSL to include your `user_settings.h` before processing `settings.h`, giving you full control over the feature set.

### Configure Flags

No specific `./configure` flags are documented in the available source material for VxWorks. VxWorks projects are typically built using the Wind River Workbench IDE or a custom makefile rather than the autoconf/automake build system. If using a makefile-based build, pass defines directly via compiler flags:

```
-DWOLFSSL_VXWORKS -DWOLFSSL_USER_SETTINGS
```

### IDE / Workbench Projects

No pre-built Wind River Workbench project files are referenced in the available source material. Check the wolfSSL GitHub repository under the `IDE/` directory for any VxWorks-specific project files, or contact wolfSSL for integration assistance.

---

## 3. Platform-Specific Features

### Threading

VxWorks has its own threading and mutex APIs. When `WOLFSSL_VXWORKS` is defined, wolfSSL is expected to map its internal locking primitives to VxWorks equivalents. Verify that multi-threading support is correctly configured for your VxWorks version (e.g., VxWorks 6.x vs. VxWorks 7).

### Networking

VxWorks provides a BSD-compatible socket layer. wolfSSL's I/O callbacks should work with the VxWorks network stack, but you may need to verify socket API compatibility for your specific VxWorks version and network component configuration.

### VxWorks Version Differences

- **VxWorks 6.x** documentation (kernel programmer's guides for versions 6.6 through 6.9) is the most accessible publicly, available as uploaded PDFs. While these cover older versions, VxWorks kernel concepts (task management, semaphores, network stack, BSP structure) carry forward to VxWorks 7.
- **VxWorks 7** introduced a new SDK-based development model with enhanced POSIX compliance. Wind River's VxWorks 7 SDK Application Developer Guide is publicly accessible.
- The kernel programmer guide for VxWorks 7 requires a Wind River license, but the concepts from VxWorks 6.x guides largely apply to VxWorks 7 kernel development.
- **Crypto driver API documentation** for VxWorks is not publicly available. If a customer asks about VxWorks-native crypto driver integration, this must be sourced from Wind River under license.

### Hardware Cryptography

No VxWorks-specific hardware crypto acceleration is referenced in the available source material. If your VxWorks target hardware includes a crypto accelerator (e.g., from a supported vendor such as Xilinx, Renesas, or ARM TrustZone), additional defines may be required alongside `WOLFSSL_VXWORKS`. Consult the wolfSSL hardware acceleration documentation for the relevant platform.

### File System

If your VxWorks configuration does not include a file system, you may need to disable wolfSSL features that depend on file I/O (e.g., certificate loading from files). Use `NO_FILESYSTEM` if applicable:

```c
#define NO_FILESYSTEM
```

---

## 4. Common Issues

### Stack Size
Embedded RTOS environments including VxWorks often have limited default task stack sizes. wolfSSL's TLS handshake and cryptographic operations can require significant stack space. Ensure that any task running wolfSSL has an adequately sized stack. wolfSSL recommends a minimum of several kilobytes; the exact requirement depends on the cipher suites and features enabled. Test with stack overflow detection enabled during development.

### API Compatibility
Different versions of VxWorks (5.x, 6.x, 7) may have varying levels of POSIX compatibility. If wolfSSL uses POSIX APIs not available on your target, you may need to provide stub implementations or enable alternative code paths via defines.

### Time Functions
wolfSSL requires access to a time source for certificate validation and TLS session management. Verify that `time()` or an equivalent is available and correctly returns the current time on your VxWorks target. If not, you may need to implement a custom time callback.

### Entropy / RNG
wolfSSL requires a source of entropy for its random number generator. On VxWorks, ensure that a suitable entropy source is available. If the default entropy source is not supported, you may need to implement a custom `wc_GenerateSeed()` function.

### Compiler Warnings and Compatibility
VxWorks toolchains (e.g., Wind River Diab, GNU for VxWorks) may produce warnings or errors on wolfSSL source files. Review compiler output and apply any necessary flags to suppress benign warnings or address compatibility issues.

---

## 5. Example Configuration

The following is a minimal `user_settings.h` for a VxWorks target. Adjust feature flags based on your application requirements and available resources.

```c
/* user_settings.h — wolfSSL minimal configuration for VxWorks */

#ifndef WOLFSSL_USER_SETTINGS_H
#define WOLFSSL_USER_SETTINGS_H

/* Platform */
#define WOLFSSL_VXWORKS

/* Use TLS 1.2 and 1.3 */
#define WOLFSSL_TLS13
#define NO_OLD_TLS

/* Disable features not needed in embedded context */
#define NO_FILESYSTEM        /* Remove if file system is available */
#define NO_INLINE            /* Optional: disable inlining for debugging */

/* Reduce memory footprint if needed */
#define WOLFSSL_SMALL_STACK

/* Cipher suite selection — customize as needed */
#define NO_DES3
#define NO_RC4
#define NO_MD4

/* Enable only required key types */
#define HAVE_ECC
#define HAVE_AESGCM
#define HAVE_SHA256

/* Threading — enable if using multi-threaded tasks */
/* #define SINGLE_THREADED */  /* Uncomment if single-threaded only */

/* Entropy source — implement wc_GenerateSeed() if needed */

#endif /* WOLFSSL_USER_SETTINGS_H */
```

To use this file, ensure `WOLFSSL_USER_SETTINGS` is defined in your compiler flags or at the top of your build configuration:

```
-DWOLFSSL_USER_SETTINGS
```

---

## Additional Resources

- [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/)
- [wolfSSL GitHub Repository](https://github.com/wolfSSL/wolfssl) — check `IDE/` and `wolfssl/wolfcrypt/settings.h`
- [wolfSSL Support](https://www.wolfssl.com/contact/) — for VxWorks-specific integration assistance

**VxWorks Documentation (Public)**:
- VxWorks 6.x Kernel Programmer's Guides (6.6 through 6.9) are publicly available as uploaded PDFs. While these cover older versions, VxWorks kernel concepts (task management, semaphores, network stack, BSP structure) carry forward to VxWorks 7.
- Wind River's VxWorks 7 SDK Application Developer Guide is publicly accessible
- VxWorks 5.5 Programmer's Guide is hosted at JLab (Jefferson Lab)
