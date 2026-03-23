---
paths:
  - "**/IDE/apple*/**"
  - "**/IDE/Xcode*/**"
  - "**/*.xcodeproj/**"
---

# iOS / macOS (Apple Platforms) — wolfSSL Platform Guide

---

## 1. Overview

wolfSSL supports Apple platforms — including iOS and macOS (OS X) — through a combination of platform-specific preprocessor defines, Xcode project files, and optional integration with Apple's native certificate validation APIs. The library can be built as a static library (`libwolfssl_ios.a` or `libwolfssl_osx.a`) using the provided Xcode projects, or configured and built from the command line using autoconf.

Key capabilities on Apple platforms include:

- Full TLS/DTLS support via wolfSSL
- wolfCrypt cryptographic primitives, including optional ARMv8 hardware acceleration on supported devices (iPhone 8/8 Plus, iPhone X and later)
- Optional integration with Apple's native certificate manager via the `APPLE_NATIVE_CERTMAN` / `WOLFSSL_APPLE_NATIVE_CERT_VALIDATION` feature
- FIPS-capable builds via a separate Xcode project (requires FIPS sources; contact wolfSSL for availability)

---

## 2. Build Configuration

### 2.1 Preprocessor Defines

| Define | Purpose |
|---|---|
| `IPHONE` | Required for Xcode-based builds on iOS and macOS. Signals the wolfSSL build system that it is targeting an Apple platform. |
| `WOLFSSL_USER_SETTINGS` | Enables the `user_settings.h` file for macro configuration across multiple Xcode projects. Defined automatically by the Xcode projects. |
| `APPLE_NATIVE_CERTMAN` | Enables Apple native certificate manager integration. |
| `WOLFSSL_APPLE_NATIVE_CERT_VALIDATION` | Enables Apple native certificate validation. Used together with `APPLE_NATIVE_CERTMAN`. |

> **Note:** `IPHONE` is listed in `settings.h` as a commented-out option. It must be explicitly defined — either in `user_settings.h`, as a compiler preprocessor macro in Xcode build settings, or on the compiler command line.

### 2.2 Configure Flag (Command-Line Builds)

For autoconf/command-line builds, Apple native certificate manager support can be enabled with:

```sh
./configure --enable-apple-native-certman
```

Additional options (e.g., enabling ECC, SHA-3, ChaCha20-Poly1305) should be added as needed for your use case.

### 2.3 Xcode Project Files

The directory `IDE/XCODE/` contains the following files for building on Apple platforms:

| File | Description |
|---|---|
| `wolfssl.xcworkspace` | Workspace combining the library and testsuite client projects |
| `wolfssl.xcodeproj` | Builds wolfSSL and wolfCrypt libraries for macOS and iOS |
| `wolfssl_testsuite.xcodeproj` | Runs the wolfSSL test suite |
| `wolfssl-FIPS.xcodeproj` | Builds wolfSSL and wolfCrypt-FIPS (requires FIPS sources) |
| `user_settings.h` | Shared custom library settings used across all projects |

**Output libraries:**

- `libwolfssl_osx.a` — macOS static library
- `libwolfssl_ios.a` — iOS static library

Headers are copied into `Build/Products/Debug/include` or `Build/Products/Release/include`.

### 2.4 Configuring the Xcode Build Location

For the library and testsuite to link correctly, the build location must be set relative to the workspace:

1. **File → Workspace Settings** (or **Xcode → Preferences → Locations → Locations**)
2. **Derived Data → Advanced**
3. **Custom → Relative to Workspace**
4. **Products → Build/Products**

### 2.5 Modifying Xcode Preprocessor Macros

The Xcode projects define `WOLFSSL_USER_SETTINGS` by default. To add or modify preprocessor macros:

1. Click on the Project in **Project Navigator**
2. Click on the **Build Settings** tab
3. Scroll to **Apple LLVM - Preprocessing**
4. Open **Preprocessor Macros** and use **+** / **-** to modify
5. Repeat for both **Debug** and **Release** configurations

---

## 3. Platform-Specific Features

### 3.1 ARMv8 Hardware Cryptography Acceleration

On devices with ARMv8 hardware crypto support (iPhone 8/8 Plus, iPhone X and later), wolfSSL can use hardware-accelerated cryptographic instructions. This is conditionally enabled in `user_settings.h`:

```c
/* ARMv8 - iPhone 8/8Plus and iPhone X */
#ifdef __ARM_FEATURE_CRYPTO
    #define WOLFSSL_ARMASM
    #define WOLFSSL_SP_ARM64_ASM
#endif
```

When `WOLFSSL_ARMASM` is defined, Ed25519 is disabled in the example configuration (see the `#ifndef WOLFSSL_ARMASM` guard around `HAVE_ED25519`).

### 3.2 Single Precision (SP) Math

SP math is enabled in the example configuration for performance on Apple silicon and ARM devices:

```c
#define WOLFSSL_SP_MATH
#define WOLFSSL_HAVE_SP_RSA
#define WOLFSSL_HAVE_SP_DH
#define WOLFSSL_HAVE_SP_ECC
```

### 3.3 128-bit Integer Type

Apple platform toolchains support `__uint128_t`, which can be enabled for performance:

```c
#define HAVE___UINT128_T
```

### 3.4 Timing Resistance

The example configuration enables timing-resistant implementations by default:

```c
#define WC_RSA_BLINDING
#define TFM_TIMING_RESISTANT
#define ECC_TIMING_RESISTANT
```

### 3.5 Apple Native Certificate Validation

wolfSSL provides optional integration with Apple's native certificate validation system (Security framework). This is enabled via:

- Define: `APPLE_NATIVE_CERTMAN` and/or `WOLFSSL_APPLE_NATIVE_CERT_VALIDATION`
- Configure flag: `--enable-apple-native-certman`

This allows wolfSSL to delegate certificate chain validation to the Apple Security framework rather than using wolfSSL's built-in certificate manager. This can be useful for applications that need to respect the system trust store on macOS and iOS.

> **Note:** The source material confirms the existence of these defines and the configure flag, but detailed behavioral documentation is limited here. Consult the [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/) and the wolfSSL GitHub repository for full API and behavioral details.

### 3.6 DTLS Support

DTLS is enabled in the example Xcode `user_settings.h`:

```c
#define WOLFSSL_DTLS
```

### 3.7 FIPS Builds

A dedicated Xcode project (`wolfssl-FIPS.xcodeproj`) is provided for FIPS builds. FIPS sources are not included in the standard distribution. Contact [info@wolfssl.com](mailto:info@wolfssl.com) for wolfCrypt FIPS availability.

When `HAVE_FIPS` is defined, the example configuration applies a restricted set of options:

```c
#define NO_MD4
#define NO_DSA
#define NO_PWDBASED
```

---

## 4. Common Issues

### 4.1 Missing `IPHONE` Define

The `IPHONE` define is **not** set automatically. It must be explicitly defined in `user_settings.h`, as a preprocessor macro in Xcode build settings, or on the compiler command line. Omitting it may result in incorrect platform detection within wolfSSL.

### 4.2 `WOLFSSL_USER_SETTINGS` Must Be Defined

The Xcode projects define `WOLFSSL_USER_SETTINGS` automatically to enable `user_settings.h`. If you are integrating wolfSSL into your own Xcode project without using the provided project files, you must add `WOLFSSL_USER_SETTINGS` to your preprocessor macros manually, or wolfSSL will not pick up your `user_settings.h` configuration.

### 4.3 Build Location Must Be Set Correctly

If the build location is not set to **Relative to Workspace**, the library and testsuite projects may fail to link. Follow the workspace settings steps described in Section 2.4.

### 4.4 Ed25519 Disabled with ARMv8 Assembly

The example `user_settings.h` disables Ed25519 when `WOLFSSL_ARMASM` is active:

```c
#ifndef WOLFSSL_ARMASM
    #define HAVE_ED25519
#endif
```

If you require Ed25519 on ARMv8 devices, review this guard and test carefully for compatibility.

### 4.5 No Temporary File Writes

The example configuration defines `NO_WRITE_TEMP_FILES`, which is appropriate for iOS where the application sandbox restricts arbitrary file system writes. Ensure your application does not rely on wolfSSL writing temporary files.

### 4.6 Stack Sizing

The source material does not specify explicit stack size requirements for iOS/macOS. However, iOS imposes strict stack size limits on secondary threads (512 KB by default). If wolfSSL operations are performed on background threads, ensure sufficient stack space is allocated. Consult the [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/) for general stack usage guidance.

### 4.7 RC4, MD4, DSA, PSK, and PWDBASED Disabled by Default

The example configuration explicitly disables several older or less-used algorithms:

```c
#define NO_RC4
#define NO_MD4
#define NO_DSA
#define NO_PSK
#define NO_PWDBASED
```

If your application requires any of these, remove the corresponding `NO_*` define from your `user_settings.h`.

---

## 5. Example Configuration

### 5.1 Minimal `user_settings.h` for iOS / macOS (Xcode)

This is based directly on the `IDE/XCODE/user_settings.h` provided in the wolfSSL source tree:

```c
/* user_settings.h — wolfSSL for iOS / macOS (Xcode) */

/* Required for Xcode / Apple platform builds */
#define IPHONE

/* RNG */
#define HAVE_HASHDRBG

/* Symmetric */
#define HAVE_AESGCM

/* Hash */
#define WOLFSSL_SHA512
#define WOLFSSL_SHA384
#define WOLFSSL_SHA3

/* Disable main() entry point */
#define NO_MAIN_DRIVER

/* 128-bit integer support */
#define HAVE___UINT128_T

/* SP Math */
#define WOLFSSL_SP_MATH
#define WOLFSSL_HAVE_SP_RSA
#define WOLFSSL_HAVE_SP_DH
#define WOLFSSL_HAVE_SP_ECC

/* ECC */
#define HAVE_ECC
#define ECC_SHAMIR
#define TFM_ECC256

/* Timing resistance */
#define WC_RSA_BLINDING
#define TFM_TIMING_RESISTANT
#define ECC_TIMING_RESISTANT

/* ARMv8 hardware crypto (iPhone 8/8Plus, iPhone X and later) */
#ifdef __ARM_FEATURE_CRYPTO
    #define WOLFSSL_ARMASM
    #define WOLFSSL_SP_ARM64_ASM
#endif

/* Authenticated encryption */
#define HAVE_POLY1305
#define HAVE_CHACHA

/* Curve/Ed */
#define HAVE_CURVE25519
#ifndef WOLFSSL_ARMASM
    #define HAVE_ED25519
#endif

/* TLS extensions */
#define HAVE_ONE_TIME_AUTH
#define HAVE_TLS_EXTENSIONS
#define HAVE_SUPPORTED_CURVES
#define HAVE_EXTENDED_MASTER

/* DTLS */
#define WOLFSSL_DTLS

/* Disable legacy/weak algorithms */
#define NO_RC4
#define NO_MD4
#define NO_DSA
#define NO_PSK
#define NO_PWDBASED

/* No temporary file writes (required for iOS sandbox) */
#define NO_WRITE_TEMP_FILES

/* Test certificate buffers (remove for production) */
#define USE_CERT_BUFFERS_2048
#define USE_CERT_BUFFERS_256

/* Optional: Apple native certificate validation */
/* #define WOLFSSL_APPLE_NATIVE_CERT_VALIDATION */
```

### 5.2 Command-Line Configure with Apple Native Certificate Manager

```sh
./configure --enable-apple-native-certman
make
sudo make install
```

---

## Further Reference

- [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/)
- wolfSSL Xcode project files: `IDE/XCODE/` in the wolfSSL source tree
- wolfSSL GitHub: [https://github.com/wolfSSL/wolfssl](https://github.com/wolfSSL/wolfssl)
- FIPS inquiries: [info@wolfssl.com](mailto:info@wolfssl.com)
