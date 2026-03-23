---
paths:
  - "**/android*/**"
  - "**/Android*"
---

# Android NDK + JNI — wolfSSL Platform Guide

## 1. Overview

Android NDK (Native Development Kit) allows developers to implement parts of an Android application in C or C++. wolfSSL supports Android as a first-class platform, with dedicated build files and configuration templates located in the `IDE/Android/` directory of the wolfSSL source tree.

The primary tested use case is Android v8.1 with **WPA Supplicant** and **KeyStore** integration, replacing BoringSSL as the underlying TLS/crypto provider. wolfSSL can be built as a shared library (`libwolfssl`) and consumed by native Android components via the Android build system (AOSP) or via JNI from Java/Kotlin application code.

The key platform detection macro is `__ANDROID__`, and the key build macro required for custom configuration is `WOLFSSL_USER_SETTINGS`.

---

## 2. Build Configuration

### 2.1 AOSP / Android.bp Integration

wolfSSL ships a template `Android.bp` build file for integration into the Android Open Source Project (AOSP) build system. The recommended installation procedure is:

1. Place the wolfSSL source tree into `./external/wolfssl` within your AOSP tree.
2. Copy `IDE/Android/Android.bp` into `./external/wolfssl/`.
3. Copy `IDE/Android/user_settings.h` into `./external/wolfssl/`.
4. Add the following line to your device `.mk` file:

```makefile
PRODUCT_PACKAGES += libwolfssl
```

### 2.2 Building with AOSP

```sh
source build/envsetup.sh
lunch [num]
mm -j8
```

### 2.3 Consuming libwolfssl in an Application Module

In your application's `Android.mk` file, add:

```makefile
# Crypto Provider - wolfSSL
LOCAL_CFLAGS += -DWOLFSSL_USER_SETTINGS \
                -Iexternal/wolfssl \
                -Iexternal/wolfssl/wolfssl
LOCAL_SHARED_LIBRARIES += libwolfssl
```

The `-DWOLFSSL_USER_SETTINGS` flag instructs wolfSSL to read all compile-time configuration from `user_settings.h` rather than from `config.h` or autoconf-generated headers.

### 2.4 Key Compiler Defines

| Define | Purpose |
|---|---|
| `WOLFSSL_USER_SETTINGS` | Use `user_settings.h` for all build configuration |
| `__ANDROID__` | Platform detection (set automatically by NDK toolchain) |
| `__aarch64__` | Detected automatically; enables ARM64 assembly paths |
| `WOLFSSL_ARMASM` | Enables ARM hardware assembly optimizations (AArch64) |
| `WOLFSSL_SP_ARM64_ASM` | Enables SP (Single Precision) ARM64 assembly speedups |

### 2.5 Configure Flags

No specific `./configure` flags are documented for this platform in the source material. The Android build relies entirely on the `Android.bp` build system file and `user_settings.h`. Consult the [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/) for configure-based build options if building outside of AOSP.

---

## 3. Platform-Specific Features

### 3.1 Hardware / Assembly Crypto Acceleration

On **AArch64** (ARM64) devices, wolfSSL automatically enables ARM assembly optimizations with a version guard for Clang compatibility:

```c
#ifdef __aarch64__
    #if !defined(__clang__) || \
        (defined(__clang__) && defined(__clang_major__) && __clang_major__ >= 5)
        #define WOLFSSL_ARMASM
    #endif
#endif
```

> **Note:** Clang v4 has a known issue with inline assembly constraints. `WOLFSSL_ARMASM` is intentionally suppressed for that version.

When `WOLFSSL_ARMASM` is active, SP ARM64 assembly is also enabled:

```c
#ifdef WOLFSSL_ARMASM
    #define WOLFSSL_SP_ARM64_ASM
#endif
```

### 3.2 SP (Single Precision) Math Speedups

The template configuration enables SP math acceleration for RSA, DH, and ECC:

```c
#define WOLFSSL_SP
#define WOLFSSL_SP_SMALL        /* smaller code footprint variant */
#define WOLFSSL_HAVE_SP_RSA
#define WOLFSSL_HAVE_SP_DH
#define WOLFSSL_HAVE_SP_ECC
```

### 3.3 Threading

Thread-local storage is enabled for Android:

```c
#define HAVE_THREAD_LS
```

This supports per-thread error state, which is required for correct multi-threaded operation.

### 3.4 KeyStore / PK Callbacks

To support Android KeyStore integration (delegating private key operations to the system keystore rather than performing them in-process), the following are enabled:

```c
#define HAVE_PK_CALLBACKS       /* signing operations delegated to KeyStore */
#define WOLF_CRYPTO_CB          /* crypto callback support (non-FIPS builds) */
```

> **Note:** `WOLF_CRYPTO_CB` is explicitly excluded when `HAVE_FIPS` is defined, as it is not present in the FIPS 3389 boundary.

### 3.5 WPA Supplicant Support

The configuration includes WPA Supplicant compatibility:

```c
#define WOLFSSL_WPAS_SMALL
#define OPENSSL_ALL             /* broad OpenSSL API compatibility layer */
```

### 3.6 TLS Configuration

- TLS 1.3 is enabled (`WOLFSSL_TLS13`)
- Old TLS versions (TLS 1.0, TLS 1.1) are disabled (`NO_OLD_TLS`)
- Session tickets, TLS extensions, supported curves, extended master secret, and encrypt-then-MAC are all enabled

### 3.7 Certificate and Key Operations

The following certificate and key generation features are enabled for Android KeyStore and WPA Supplicant use cases:

```c
#define WOLFSSL_CERT_GEN
#define WOLFSSL_CERT_EXT
#define WOLFSSL_CERT_REQ
#define WOLFSSL_KEY_GEN
#define KEEP_OUR_CERT
#define KEEP_PEER_CERT
```

---

## 4. Common Issues

### 4.1 Clang v4 Inline Assembly
Older Android toolchains shipping Clang v4 have a known incompatibility with wolfSSL's inline assembly constraints. The `user_settings.h` template guards against this by checking `__clang_major__ >= 5` before enabling `WOLFSSL_ARMASM`. If you observe build errors related to assembly constraints, verify your Clang version.

### 4.2 FIPS and Crypto Callbacks
`WOLF_CRYPTO_CB` is incompatible with the FIPS 3389 module boundary. The template wraps this define in `#ifndef HAVE_FIPS`. If you are building a FIPS-validated configuration, do not enable `WOLF_CRYPTO_CB`.

### 4.3 WOLFSSL_USER_SETTINGS Must Be Defined Globally
The `-DWOLFSSL_USER_SETTINGS` flag must be passed as a compiler flag (not just defined inside a source file) so that it is visible to all wolfSSL translation units before any wolfSSL header is included.

### 4.4 Include Path Order
Both `-Iexternal/wolfssl` and `-Iexternal/wolfssl/wolfssl` must be present in `LOCAL_CFLAGS`. Missing the nested `wolfssl/` include path is a common cause of missing header errors.

### 4.5 BoringSSL Replacement
When replacing BoringSSL in an AOSP tree, API compatibility is provided through `OPENSSL_ALL` and `WOLFSSL_WPAS_SMALL`. Not all BoringSSL-specific extensions are covered; review any BoringSSL-specific API calls in your codebase against wolfSSL's OpenSSL compatibility layer.

### 4.6 Stack Size
No specific stack size guidance is provided in the available source material. Android's default thread stack sizes may be insufficient for some wolfSSL operations (particularly with large key sizes and `USE_FAST_MATH` with `FP_MAX_BITS (4096*2)`). Consult the [wolfSSL Manual — Porting Guide](https://www.wolfssl.com/documentation/manuals/wolfssl/) for stack sizing recommendations.

---

## 5. Example Configuration

The following is the `IDE/Android/user_settings.h` template (condensed to key sections). Copy this file to your wolfSSL source root and adjust as needed.

```c
/* user_settings.h — wolfSSL Android configuration template */
#ifndef _WOLF_USER_SETTINGS_H_
#define _WOLF_USER_SETTINGS_H_

/* ---- Optional: FIPS mode (disabled by default) ---- */
#if 0
    #define HAVE_FIPS_VERSION 2
    #define HAVE_FIPS
#endif

/* ---- ARM64 hardware assembly (AArch64 only) ---- */
#ifdef __aarch64__
    #if !defined(__clang__) || \
        (defined(__clang__) && defined(__clang_major__) && __clang_major__ >= 5)
        #define WOLFSSL_ARMASM
    #endif
#endif

/* ---- SP Math Speedups ---- */
#define WOLFSSL_SP
#define WOLFSSL_SP_SMALL
#define WOLFSSL_HAVE_SP_RSA
#define WOLFSSL_HAVE_SP_DH
#define WOLFSSL_HAVE_SP_ECC
#ifdef WOLFSSL_ARMASM
    #define WOLFSSL_SP_ARM64_ASM
#endif

/* ---- WPA Supplicant / OpenSSL compatibility ---- */
#define WOLFSSL_WPAS_SMALL
#define OPENSSL_ALL
#define HAVE_THREAD_LS

/* ---- Math library ---- */
#define USE_FAST_MATH
#define FP_MAX_BITS (4096 * 2)
#define TFM_TIMING_RESISTANT
#define ECC_TIMING_RESISTANT
#define WC_RSA_BLINDING

/* ---- RNG ---- */
#define HAVE_HASHDRBG

/* ---- TLS ---- */
#define WOLFSSL_TLS13
#define WC_RSA_PSS
#define HAVE_SESSION_TICKET
#define HAVE_TLS_EXTENSIONS
#define HAVE_SUPPORTED_CURVES
#define HAVE_EXTENDED_MASTER
#define HAVE_ENCRYPT_THEN_MAC
#define WOLFSSL_ENCRYPTED_KEYS
#define HAVE_KEYING_MATERIAL
#define NO_OLD_TLS
#define NO_CHECK_PRIVATE_KEY

/* ---- KeyStore / Callback support ---- */
#define HAVE_PK_CALLBACKS
#ifndef HAVE_FIPS
    #define WOLF_CRYPTO_CB
#endif

/* ---- Certificate handling ---- */
#define KEEP_OUR_CERT
#define KEEP_PEER_CERT
#define WOLFSSL_ALWAYS_VERIFY_CB
#define WOLFSSL_ALWAYS_KEEP_SNI
#define HAVE_EX_DATA
#define HAVE_EXT_CACHE
#define WOLFSSL_EITHER_SIDE
#define WOLFSSL_PUBLIC_MP
#define WOLFSSL_DER_LOAD
#define WOLFSSL_CERT_GEN
#define WOLFSSL_CERT_EXT
#define WOLFSSL_CERT_REQ
#define WOLFSSL_KEY_GEN
#define WC_RSA_NO_PADDING

/* ---- DH ---- */
#define WOLFSSL_DH_CONST
#define HAVE_FFDHE_2048
#define HAVE_FFDHE_3072
#define HAVE_FFDH

#endif /* _WOLF_USER_SETTINGS_H_ */
```

---

## Additional Resources

- wolfSSL source: `IDE/Android/README.md`, `IDE/Android/user_settings.h`, `IDE/Android/Android.bp`
- For questions or support: support@wolfssl.com
- [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/) — for configure options, porting guidance, and stack sizing details not covered by the Android-specific source material
