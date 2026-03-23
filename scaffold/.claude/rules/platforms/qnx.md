---
paths:
  - "**/qnx*"
  - "**/QNX*"
---

# QNX Neutrino — wolfSSL Platform Guide

## 1. Overview

QNX Neutrino is a real-time operating system (RTOS) commonly used in safety-critical and embedded applications, including automotive, medical, and industrial systems. wolfSSL provides support for QNX Neutrino, including integration with the Cryptographic Acceleration and Assurance Module (CAAM) hardware security block found on NXP i.MX processors running under QNX.

The primary define for this platform is `WOLFSSL_QNX_CAAM`, which enables wolfSSL's CAAM hardware acceleration driver when running on QNX Neutrino. This is closely related to the `WOLFSSL_IMX6_CAAM` define used for Linux-based i.MX6 targets — both share portions of the CAAM driver infrastructure within wolfSSL.

> **Note:** The source material available for this guide is limited. For comprehensive integration details, consult the [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/) and the wolfSSL QNX-specific documentation or contact wolfSSL support directly.

---

## 2. Build Configuration

### Key Defines

| Define | Purpose |
|---|---|
| `WOLFSSL_QNX_CAAM` | Enables QNX Neutrino CAAM hardware acceleration support |
| `WOLFSSL_CAAM` | Enables the core CAAM driver (optional, must be explicitly defined) |
| `WOLFSSL_CAAM_BLOB` | Enables CAAM blob encapsulation/decapsulation (optional, must be explicitly defined) |

### Important Notes on CAAM Defines

From the wolfSSL source (`settings.h`), the CAAM-specific defines are **not enabled by default** and must be explicitly uncommented or added to your build configuration:

```c
/* Only for WOLFSSL_IMX6_CAAM / WOLFSSL_QNX_CAAM */
/* #define WOLFSSL_CAAM      */
/* #define WOLFSSL_CAAM_BLOB */
```

These must be manually defined in your `user_settings.h` or passed as compiler flags if CAAM hardware acceleration is desired.

### Configure Flags

No specific `./configure` flags are documented in the available source material for QNX Neutrino. wolfSSL on QNX is typically built using a custom `user_settings.h` approach rather than the autoconf `./configure` system, as cross-compilation for RTOS targets generally requires manual build system integration.

### Build System Integration

- wolfSSL is typically integrated into QNX projects via the QNX Momentics IDE or QNX `make`-based build system.
- Define `WOLFSSL_USER_SETTINGS` in your compiler flags and provide a `user_settings.h` file to control the build configuration.
- No IDE project files are referenced in the available source material; check the `IDE/` directory in the wolfSSL source tree for any QNX-specific project files.

---

## 3. Platform-Specific Features

### Hardware Cryptography — CAAM

The CAAM (Cryptographic Acceleration and Assurance Module) is the primary hardware acceleration feature for this platform. When `WOLFSSL_QNX_CAAM` is defined alongside `WOLFSSL_CAAM`, wolfSSL will route supported cryptographic operations through the CAAM hardware block.

The optional `WOLFSSL_CAAM_BLOB` define adds support for CAAM blob operations, which allow cryptographic keys to be wrapped (encapsulated) and unwrapped (decapsulated) using hardware-bound keys — a useful feature for secure key storage on i.MX platforms.

### Additional Algorithm Support

The following defines are noted in the source material as relevant to this class of platform and may be enabled as needed:

| Define | Feature |
|---|---|
| `WOLFSSL_AES_SIV` | AES-SIV authenticated encryption |
| `WOLFSSL_CMAC` | CMAC message authentication |
| `WOLFSSL_CERT_PIV` | PIV certificate support |
| `WOLFSSL_AES_EAX` | AES-EAX authenticated encryption |
| `ECC_SHAMIR` | Shamir's trick for ECC (performance optimization) |
| `HAVE_X963_KDF` | X9.63 Key Derivation Function |

### Threading

No QNX-specific threading configuration is documented in the available source material. QNX Neutrino supports POSIX threads (pthreads). If your application uses multithreading, ensure wolfSSL is built with thread safety enabled. Consult the wolfSSL Manual for mutex/threading callback configuration.

### Networking

No QNX-specific networking layer configuration is documented in the available source material. QNX Neutrino supports standard POSIX socket APIs, which wolfSSL uses by default. Custom I/O callbacks can be registered if a non-standard networking stack is in use.

---

## 4. Common Issues

### CAAM Defines Must Be Explicitly Enabled

`WOLFSSL_CAAM` and `WOLFSSL_CAAM_BLOB` are commented out in `settings.h` by default. Forgetting to define these when CAAM hardware acceleration is intended will result in a software-only build without any error or warning. Always verify your build configuration explicitly enables the desired hardware paths.

### Relationship Between `WOLFSSL_QNX_CAAM` and `WOLFSSL_IMX6_CAAM`

These two defines share CAAM driver code within wolfSSL. If referencing wolfSSL documentation or examples written for `WOLFSSL_IMX6_CAAM` (Linux/i.MX6), much of the CAAM-related guidance will apply to `WOLFSSL_QNX_CAAM` as well, but OS-level driver interfaces will differ.

### Cross-Compilation

QNX Neutrino targets are cross-compiled using the QNX toolchain. Ensure the wolfSSL build system is pointed at the correct QNX cross-compiler and sysroot. The autoconf `./configure` system may require a custom `--host` triplet and toolchain prefix.

### Stack Size

wolfSSL cryptographic operations, particularly asymmetric algorithms (RSA, ECC) and post-quantum algorithms, can require significant stack space. On resource-constrained QNX deployments, verify that thread stack sizes are sufficient. As a general reference, operations like ML-KEM (Kyber) may require 10 KB or more of stack. Consult the wolfSSL Manual for algorithm-specific stack requirements.

### Limited Source Material

The wolfSSL source material available for this guide is limited in QNX-specific detail. For authoritative guidance, refer to:
- The [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/)
- wolfSSL support at support@wolfssl.com
- The `wolfssl/wolfcrypt/port/caam/` directory in the wolfSSL source tree for CAAM driver implementation details

---

## 5. Example Configuration

The following is a minimal `user_settings.h` for a QNX Neutrino target with CAAM hardware acceleration enabled. Adjust based on your specific application requirements.

```c
/* user_settings.h — wolfSSL for QNX Neutrino with CAAM */

#ifndef WOLFSSL_USER_SETTINGS_H
#define WOLFSSL_USER_SETTINGS_H

/* ---- Platform: QNX Neutrino with CAAM ---- */
#define WOLFSSL_QNX_CAAM

/* Enable CAAM hardware acceleration driver */
#define WOLFSSL_CAAM

/* Optional: Enable CAAM blob key encapsulation/decapsulation */
/* #define WOLFSSL_CAAM_BLOB */

/* ---- Algorithm Configuration ---- */
#define WOLFSSL_AES_SIV
#define WOLFSSL_CMAC
#define WOLFSSL_AES_EAX
#define HAVE_X963_KDF
#define ECC_SHAMIR

/* ---- Security Hardening ---- */
#define TFM_TIMING_RESISTANT
#define ECC_TIMING_RESISTANT
#define WC_RSA_BLINDING

/* ---- Optional: PIV Certificate Support ---- */
/* #define WOLFSSL_CERT_PIV */

/* ---- Optional: CAAM Blob Support ---- */
/* #define WOLFSSL_CAAM_BLOB */

#endif /* WOLFSSL_USER_SETTINGS_H */
```

To use this file, define `WOLFSSL_USER_SETTINGS` in your compiler flags:

```
-DWOLFSSL_USER_SETTINGS
```

And ensure `user_settings.h` is on the compiler include path.

---

> **Disclaimer:** The source material available for this guide covers only the `WOLFSSL_QNX_CAAM` define and adjacent settings. For full QNX Neutrino integration details — including CAAM driver setup, QNX resource manager interface, and complete build system instructions — consult the wolfSSL Manual and wolfSSL support resources.
