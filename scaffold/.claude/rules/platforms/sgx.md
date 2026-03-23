---
paths:
  - "**/sgx*"
  - "**/SGX*"
  - "**/enclave*"
---

# Intel SGX — wolfSSL Platform Guide

## 1. Overview

Intel Software Guard Extensions (SGX) provides hardware-based trusted execution environments (enclaves) that isolate code and data from the operating system and other applications. wolfSSL supports building as a static library for linking into SGX enclaves on both Linux and Windows platforms.

The primary define for this platform is `WOLFSSL_SGX`, which triggers a block of automatic configuration in `wolfssl/wolfcrypt/settings.h`. This define removes filesystem access, enforces single-threaded operation, enables timing-resistant math, and sets up certificate buffers — all adaptations required by the constrained enclave environment.

wolfSSL provides two IDE project directories for SGX:
- **`IDE/LINUX-SGX/`** — Makefile-based build producing `libwolfssl.sgx.static.lib.a`
- **`IDE/WIN-SGX/`** — Visual Studio project producing `wolfssl.lib` (requires Intel C++ Compiler)

Both produce static libraries intended to be linked into enclave binaries. Example enclaves demonstrating wolfSSL integration are available in the [wolfssl-examples](https://github.com/wolfSSL/wolfssl-examples) repository on GitHub.

---

## 2. Build Configuration

### The `WOLFSSL_SGX` Auto-Configuration Block

When `WOLFSSL_SGX` is defined, `settings.h` automatically sets the following defines. These apply to **both** Linux and Windows SGX builds:

| Define | Purpose |
|---|---|
| `NO_FILESYSTEM` | Enclaves have no filesystem access; certificates must use buffers |
| `ECC_TIMING_RESISTANT` | Side-channel protection for ECC operations |
| `TFM_TIMING_RESISTANT` | Side-channel protection for bignum math |
| `SINGLE_THREADED` | Multi-threaded operation has not been tested in enclaves |
| `NO_ASN_TIME` | System time headers (e.g., `windows.h`) are unavailable inside enclaves |
| `HAVE_AESGCM` | AES-GCM authenticated encryption enabled |
| `USE_CERT_BUFFERS_2048` | Built-in 2048-bit test certificate buffers (for testing without filesystem) |
| `WC_RSA_BLINDING` | RSA blinding for side-channel protection (when not FIPS and RSA is enabled) |

### Linux-Only Auto-Defines (non-MSVC)

| Define | Purpose |
|---|---|
| `HAVE_ECC` | ECC algorithm support enabled |
| `NO_WRITEV` | `writev()` is not available inside enclaves |
| `NO_MAIN_DRIVER` | No `main()` entry point in enclave library |
| `USER_TICKS` | User-provided tick function (no system clock) |
| `WOLFSSL_LOG_PRINTF` | Route logging through `printf` (requires OCALL) |
| `WOLFSSL_DH_CONST` | Use constant-time DH operations |

### Windows-Only Auto-Defines (MSVC)

| Define | Purpose |
|---|---|
| `NO_RC4` | RC4 disabled |
| `WOLFCRYPT_ONLY` | Crypto-only build, no TLS layer (non-FIPS only) |
| `NO_DES3` | Triple-DES disabled (non-FIPS only) |
| `NO_SHA` | SHA-1 disabled (non-FIPS only) |
| `NO_MD5` | MD5 disabled (non-FIPS only) |

For Windows FIPS builds, the Windows path instead defines `TFM_TIMING_RESISTANT`, `NO_WOLFSSL_DIR`, `NO_WRITEV`, `NO_MAIN_DRIVER`, `WOLFSSL_LOG_PRINTF`, and `WOLFSSL_DH_CONST`.

### Linux SGX Build Commands

The Linux build uses a dedicated makefile that sets `-DWOLFSSL_SGX -DWOLFSSL_CUSTOM_CONFIG`:

```bash
# Basic static library build (simulation mode)
make -f sgx_t_static.mk all

# Full build with SP math, debug, benchmarks, and tests
make -f sgx_t_static.mk \
    CFLAGS=-DDEBUG_WOLFSSL \
    HAVE_WOLFSSL_BENCHMARK=1 \
    HAVE_WOLFSSL_TEST=1 \
    HAVE_WOLFSSL_SP=1

# Build with AES-NI and x86_64 assembly acceleration
make -f sgx_t_static.mk \
    HAVE_WOLFSSL_ASSEMBLY=1 \
    HAVE_WOLFSSL_SP=1

# Hardware mode (requires SGX hardware + driver)
make -f sgx_t_static.mk SGX_MODE=HW

# Clean
./clean.sh
```

The output is `libwolfssl.sgx.static.lib.a` in the `IDE/LINUX-SGX/` directory.

### Windows SGX Build

Open `IDE/WIN-SGX/wolfSSL_SGX.sln` in Visual Studio. The default Platform Toolset is **Intel C++ Compiler 16.0** — adjust this to match your installed Intel compiler version. Select the target architecture (Win32 or x64) and the build configuration (Debug or PreSales). The output is `wolfssl.lib` placed in `IDE/WIN-SGX/<Configuration>/<Platform>/`.

> **Note:** The library architecture (Win32 vs x64) must match the enclave/application it links against. Release mode builds require additional steps per Intel's SGX documentation for signing and attestation.

### SP Math (Recommended)

Single Precision (SP) math is strongly recommended for SGX builds to mitigate side-channel attacks. On Linux, pass `HAVE_WOLFSSL_SP=1` to the makefile. This enables:
- `WOLFSSL_HAVE_SP_RSA` — SP RSA acceleration
- `WOLFSSL_HAVE_SP_DH` — SP DH acceleration
- `WOLFSSL_HAVE_SP_ECC` — SP ECC acceleration
- `WOLFSSL_SP_MATH_ALL` — Full SP math library

When combined with `HAVE_WOLFSSL_ASSEMBLY=1`, the build additionally links x86_64 assembly implementations for SP math and AES, providing both security hardening and significant performance improvement.

---

## 3. Platform-Specific Features

### Enclave Static Library Pattern

wolfSSL is built as a static library that is linked into an enclave binary at compile time. The enclave binary is then signed and loaded by the SGX runtime. This is the only supported integration pattern — dynamic linking is not supported within SGX enclaves.

The Enclave Definition Language (EDL) file (`wolfSSL_SGX.edl`) defines the boundary between trusted (enclave) and untrusted (application) code. The default EDL shipped with wolfSSL is minimal — applications must add their own ECALLs (calls into the enclave) and OCALLs (calls out of the enclave) as needed.

### Side-Channel Protections

SGX enclaves are a high-value target for side-channel attacks because the OS is explicitly untrusted. wolfSSL's SGX configuration enables multiple protections by default:

- **`ECC_TIMING_RESISTANT`** — Constant-time ECC scalar multiplication
- **`TFM_TIMING_RESISTANT`** — Constant-time bignum exponentiation
- **`WC_RSA_BLINDING`** — Random blinding on RSA private key operations

For maximum protection, enable SP math (`HAVE_WOLFSSL_SP=1`) which provides constant-time implementations specifically designed to resist cache-timing and branch-prediction attacks.

### No-Filesystem Constraints

Enclaves cannot access the host filesystem. This has several practical consequences:
- **Certificate loading** must use buffer-based APIs (`wolfSSL_CTX_use_certificate_buffer()`, `wolfSSL_CTX_use_PrivateKey_buffer()`) rather than file-based ones
- **`USE_CERT_BUFFERS_2048`** is auto-defined for testing convenience, providing built-in test certificates
- **CRL loading** from files is unavailable; use `wolfSSL_CRL_SetIOCb()` for custom CRL retrieval if needed
- **Entropy** is provided by the SGX SDK's `sgx_read_rand()` — wolfSSL's default `/dev/urandom` path is not available

### Simulation vs Hardware Mode

The Linux makefile defaults to `SGX_MODE=SIM` (simulation mode), which does not require SGX hardware and is suitable for development and testing. Set `SGX_MODE=HW` for production builds that use actual SGX hardware isolation. Hardware mode requires:
- SGX-capable CPU with SGX enabled in BIOS
- Intel SGX Platform Software (PSW) installed
- Intel SGX SDK installed (default path: `/opt/intel/sgxsdk`)

---

## 4. Common Issues

### Missing `wolfssl/options.h`

When building from a GitHub clone (rather than a release bundle), `wolfssl/options.h` does not exist. The build will fail without it. Create it using one of:

```bash
# Full autoconf approach
cd wolfssl && ./autogen.sh && ./configure && ./config.status

# Quick workaround (empty file is sufficient for SGX makefile builds)
touch wolfssl/options.h
```

### AES-NI Not Enabled by Default

AES-NI hardware acceleration within SGX requires explicitly passing `HAVE_WOLFSSL_ASSEMBLY=1` to the makefile. Without this flag, AES operations use pure C implementations. Note that older versions of the SGX port did not support AES-NI at all.

### Windows Build Is Crypto-Only (Non-FIPS)

The Windows SGX build with `WOLFCRYPT_ONLY` defined (the non-FIPS default) excludes the TLS layer entirely. Only wolfCrypt APIs (hashing, encryption, signatures, key generation) are available. If full TLS support is needed inside a Windows SGX enclave, a FIPS build is required or the define must be manually overridden.

### Single-Threaded Limitation

All SGX builds enforce `SINGLE_THREADED`. Multi-threaded wolfSSL usage inside enclaves has not been tested. If your enclave creates multiple threads that each need wolfSSL, you must either serialize access or maintain separate wolfSSL contexts per thread without relying on wolfSSL's internal mutex support.

### No System Time

`NO_ASN_TIME` is auto-defined because enclaves cannot access system time. This means certificate validity period checks are skipped. If time-based validation is required, use `wolfSSL_SetTimeCb()` to provide a custom time source (e.g., an OCALL to the untrusted application).

### Intel Compiler Requirement (Windows)

The Windows SGX project requires the Intel C++ Compiler (default: version 16.0). If a different version is installed, update the Platform Toolset in the Visual Studio project properties. Standard MSVC cannot compile SGX enclave code.

### Linking Architecture Mismatch

On Windows, the wolfSSL static library architecture (Win32 or x64) must exactly match the enclave project architecture. A mismatch produces linker errors that can be confusing — always verify both projects target the same platform.

---

## 5. Example Configuration

### Linux SGX — Production Build Script

```bash
#!/bin/bash
# Build wolfSSL for SGX with recommended security settings
# Run from wolfssl/IDE/LINUX-SGX/

# Ensure options.h exists (required for GitHub clones)
touch ../../wolfssl/options.h

# Build with SP math, assembly acceleration, hardware mode
make -f sgx_t_static.mk \
    SGX_MODE=HW \
    HAVE_WOLFSSL_SP=1 \
    HAVE_WOLFSSL_ASSEMBLY=1

# Output: libwolfssl.sgx.static.lib.a
```

### Custom `user_settings.h` for SGX Enclave

If building wolfSSL outside the provided IDE projects (e.g., integrating into a custom enclave build system), use a `user_settings.h` like the following:

```c
/* user_settings.h — wolfSSL for Intel SGX enclave */

#ifndef WOLFSSL_USER_SETTINGS_H
#define WOLFSSL_USER_SETTINGS_H

/* ---- Platform: Intel SGX ---- */
#define WOLFSSL_SGX
/* settings.h auto-defines: NO_FILESYSTEM, SINGLE_THREADED,
   ECC_TIMING_RESISTANT, TFM_TIMING_RESISTANT, WC_RSA_BLINDING,
   NO_ASN_TIME, HAVE_AESGCM, USE_CERT_BUFFERS_2048 */

/* ---- SP Math (recommended for side-channel resistance) ---- */
#define WOLFSSL_HAVE_SP_RSA
#define WOLFSSL_HAVE_SP_DH
#define WOLFSSL_HAVE_SP_ECC
#define WOLFSSL_SP_MATH_ALL

/* ---- TLS Configuration (omit for crypto-only) ---- */
#define HAVE_TLS_EXTENSIONS
#define HAVE_SUPPORTED_CURVES
#define HAVE_SNI

/* ---- Algorithm Selection ---- */
#define HAVE_ECC
#define HAVE_AESGCM
#define HAVE_CHACHA
#define HAVE_POLY1305
#define HAVE_HKDF

/* ---- Disable Unused Features ---- */
#define NO_RC4
#define NO_DES3
#define NO_MD4
#define NO_PSK
#define NO_OLD_TLS

/* ---- Debug (disable for production) ---- */
/* #define DEBUG_WOLFSSL */

#endif /* WOLFSSL_USER_SETTINGS_H */
```

### Certificate Loading in an Enclave

Since `NO_FILESYSTEM` is enforced, certificates must be loaded from memory buffers:

```c
#include <wolfssl/ssl.h>
#include <wolfssl/certs_test.h>  /* provides test cert buffers */

/* Load CA certificate from buffer */
int ret = wolfSSL_CTX_load_verify_buffer(ctx,
    ca_cert_der_2048, sizeof_ca_cert_der_2048,
    SSL_FILETYPE_ASN1);

/* Load server certificate from buffer */
ret = wolfSSL_CTX_use_certificate_buffer(ctx,
    server_cert_der_2048, sizeof_server_cert_der_2048,
    SSL_FILETYPE_ASN1);

/* Load server private key from buffer */
ret = wolfSSL_CTX_use_PrivateKey_buffer(ctx,
    server_key_der_2048, sizeof_server_key_der_2048,
    SSL_FILETYPE_ASN1);
```

For production, replace the test buffers with your own certificate and key data, compiled into the enclave binary or passed in via ECALLs.

---

> **Source files:** `IDE/LINUX-SGX/README.md`, `IDE/LINUX-SGX/sgx_t_static.mk`, `IDE/WIN-SGX/ReadMe.txt`, `wolfssl/wolfcrypt/settings.h` (the `WOLFSSL_SGX` ifdef block at line 2851).
