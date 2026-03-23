---
paths:
  - "**/silabs*"
  - "**/SiLabs*"
  - "**/EFM32*"
  - "**/EFR32*"
---

# Silicon Labs EFR32 / Gecko SDK — wolfSSL Platform Guide

## 1. Overview

wolfSSL provides hardware-accelerated cryptography support for Silicon Labs EFR32 Series 2 devices through the SE (Secure Element) Manager interface. The port is gated by the `WOLFSSL_SILABS_SE_ACCEL` preprocessor define and leverages the Gecko SDK's `sl_se_manager` API to offload cryptographic operations to the on-chip Secure Element.

The port files are located at:
- **Headers:** `wolfssl/wolfcrypt/port/silabs/silabs_aes.h`, `silabs_ecc.h`, `silabs_hash.h`, `silabs_random.h`
- **Sources:** `wolfcrypt/src/port/silabs/silabs_aes.c`, `silabs_ecc.c`, `silabs_hash.c`, `silabs_random.c`
- **IDE Project:** `IDE/SimplicityStudio/` (user_settings.h, test_wolf.c, README)

The integration covers EFR32 Mighty Gecko, Blue Gecko, and Flex Gecko families. Devices with the Secure Vault feature (`_SILICON_LABS_SECURITY_FEATURE_VAULT`) gain additional capabilities including SHA-384/512 hardware acceleration and vault-based ECC key storage.

**Important:** Silicon Labs recommends using higher-level APIs (like the SE Manager or mbedTLS shim) over raw `em_crypto.h` for the CRYPTO peripheral. The wolfSSL port follows this guidance by integrating through `sl_se_manager` rather than the low-level HAL directly.

---

## 2. Build Configuration

### Primary Define

```c
#define WOLFSSL_SILABS_SE_ACCEL
```

This is the only required define to enable hardware acceleration. It gates all Silicon Labs port code.

### IDE Setup (Simplicity Studio)

wolfSSL ships a ready-made project under `IDE/SimplicityStudio/`. The recommended integration steps:

1. Create a new project in Simplicity Studio based on `cli_kernel_freertos`.
2. Copy wolfSSL source into the project. Use `./scripts/makedistsmall.sh` to produce a reduced bundle.
3. Exclude all `.S` and `asm.c` files (not needed when using SE hardware acceleration).
4. Copy `IDE/SimplicityStudio/user_settings.h` to `wolfssl/user_settings.h` in the project.
5. Add `WOLFSSL_USER_SETTINGS` as a C preprocessor define.
6. Add `wolfssl` to the C include path.
7. Install the **SE Manager** component in the Simplicity Studio project configurator.

### Gecko SDK Version Compatibility

The port supports both Gecko SDK v3 and v4+:

- **Gecko SDK v3:** Uses the "streaming" hash interface (`sl_se_hash_streaming_context_t`). Auto-detected when `SL_SE_PRF_HMAC_SHA1` is not defined. Can be forced with `WOLFSSL_SILABS_SE_ACCEL_3`.
- **Gecko SDK v4+:** Uses the "multipart" hash interface (`sl_se_sha*_multipart_context_t`). This is the default path when SDK v3 is not detected.

Detection happens automatically in `silabs_hash.h`:
```c
#if !defined(WOLFSSL_SILABS_SE_ACCEL_3) && !defined(SL_SE_PRF_HMAC_SHA1)
    #define WOLFSSL_SILABS_SE_ACCEL_3
#endif
```

### Stack and Heap Requirements

The reference `user_settings.h` specifies 12 KB for both FreeRTOS heap and CLI task stack. The SE Manager itself requires heap for command context structures. Recommended minimums:

- FreeRTOS heap: 12 KB (`configTOTAL_HEAP_SIZE`)
- Task stack for wolfCrypt operations: 12 KB
- `WOLFSSL_SMALL_STACK` is recommended to reduce stack pressure by moving large variables to heap allocation

### Reference user_settings.h Defines

The `IDE/SimplicityStudio/user_settings.h` provides a complete reference. Key platform-related defines:

```c
#define WOLFSSL_SILABS_SE_ACCEL       /* Enable SE hardware acceleration */
#define WOLFSSL_GENERAL_ALIGNMENT 4   /* ARM Cortex-M alignment */
#define SIZEOF_LONG_LONG 8
#define FREERTOS                      /* Or SINGLE_THREADED for bare-metal */
#define WOLFSSL_SMALL_STACK
#define WOLFSSL_USER_IO               /* Custom I/O callbacks, no BSD sockets */
#define WOLFSSL_SP_ASM
#define WOLFSSL_SP_ARM_CORTEX_M_ASM   /* SP math with Cortex-M assembly */
#define WOLFSSL_SP_MATH_ALL
#define NO_FILESYSTEM
#define NO_WRITEV
#define NO_DEV_RANDOM                 /* SE TRNG provides entropy */
```

---

## 3. Platform-Specific Features

### Hardware-Accelerated Algorithms

The SE Manager port accelerates:

- **AES:** CBC encrypt/decrypt, GCM encrypt/decrypt, CCM encrypt/decrypt (via `silabs_aes.c`). Also supports `WOLFSSL_AES_DIRECT` for raw block encrypt/decrypt.
- **Hashing:** SHA-1, SHA-224, SHA-256 on all SE-equipped devices. SHA-384 and SHA-512 on Secure Vault devices only.
- **ECC:** Key generation, ECDSA sign/verify, ECDHE shared secret (via `silabs_ecc.c`). Uses `sl_se_manager_key_derivation.h` and `sl_se_manager_signature.h`.
- **Random:** Hardware TRNG seeding via `silabs_random.c`. By default, the TRNG seeds the wolfSSL DRBG. Define `WOLFSSL_SILABS_TRNG` to use the hardware TRNG for all random data generation.

### Secure Vault Features

Devices with `_SILICON_LABS_SECURITY_FEATURE_VAULT` gain:

- **SHA-384 and SHA-512** hardware acceleration (enabled via `WOLFSSL_SILABS_SHA384` / `WOLFSSL_SILABS_SHA512`, auto-defined when `WOLFSSL_SHA384` / `WOLFSSL_SHA512` are set)
- **Vault key storage** for ECC keys via `silabs_ecc_load_vault()` — allows loading ECC private keys from the device's secure key storage

### Multi-Threading

The SE Manager natively supports multi-threading for FreeRTOS and Micrium. If using a different RTOS, additional mutex protection around SE Manager calls may be necessary. The wolfSSL reference configuration uses FreeRTOS by default.

### SE Firmware

The SE firmware version matters for correctness and stability. wolfSSL testing was performed with SE firmware version `1.2.6`. SE firmware updates are applied through Simplicity Commander:
```
commander flash s2c1_se_fw_upgrade_app_1v2p6.hex
```

---

## 4. Common Issues

### AES-GCM Tag Length Restriction

**Issue:** AES-GCM operations fail or produce incorrect results with authentication tag lengths less than 16 bytes.
**Resolution:** The SE Manager requires GCM tag lengths >= 16 bytes. If your application uses shorter tags, you cannot use hardware acceleration for those operations. This is a hardware limitation, not a wolfSSL bug.

### TRNG Over-Request Causing System Reset

**Issue:** When `WOLFSSL_SILABS_TRNG` is defined, requesting too much random data or requesting it too rapidly may trigger a system reset with `SESYSREQ` error.
**Resolution:** This affects early SE firmware versions. Update the SE firmware to the latest version. If the issue persists, remove `WOLFSSL_SILABS_TRNG` and use the default mode where the hardware TRNG only seeds the software DRBG.

### Gecko SDK Version Mismatch

**Issue:** Build errors referencing `sl_se_hash_streaming_context_t` or `sl_se_sha*_multipart_context_t` not found.
**Resolution:** Check which Gecko SDK version is installed. If using SDK v3, verify that `WOLFSSL_SILABS_SE_ACCEL_3` is being auto-detected (check for `SL_SE_PRF_HMAC_SHA1` in SDK headers). If auto-detection fails, manually define `WOLFSSL_SILABS_SE_ACCEL_3` in `user_settings.h`.

### SE Manager Component Not Installed

**Issue:** Build errors for missing `sl_se_manager.h` or related headers.
**Resolution:** In Simplicity Studio, open the project's Software Components and install the **SE Manager** component. This adds the necessary SDK source and headers.

### Insufficient Stack or Heap

**Issue:** Hard faults or FreeRTOS stack overflow during wolfCrypt operations.
**Resolution:** Increase both the FreeRTOS heap (`configTOTAL_HEAP_SIZE`) and task stack to at least 12 KB. Enable `WOLFSSL_SMALL_STACK` to move large temporary buffers to heap allocation.

### SHA-384/512 Not Available

**Issue:** SHA-384 or SHA-512 operations fall back to software or fail on EFR32 devices.
**Resolution:** SHA-384 and SHA-512 hardware acceleration is only available on Secure Vault devices (`_SILICON_LABS_SECURITY_FEATURE_VAULT`). On non-Vault devices, these algorithms use the software implementation. This is expected behavior.

---

## 5. Example Configuration

The following is a minimal `user_settings.h` for an EFR32 Series 2 device with SE acceleration and FreeRTOS. For a complete reference, see `IDE/SimplicityStudio/user_settings.h`.

```c
/* user_settings.h — wolfSSL for Silicon Labs EFR32 with SE Accel */

#ifndef WOLFSSL_USER_SETTINGS_H
#define WOLFSSL_USER_SETTINGS_H

/* ---- Silicon Labs SE Hardware Acceleration ---- */
#define WOLFSSL_SILABS_SE_ACCEL

/* ---- Platform ---- */
#define WOLFSSL_GENERAL_ALIGNMENT 4
#define SIZEOF_LONG_LONG 8
#define HAVE_STRINGS_H
#define FREERTOS                       /* Use SINGLE_THREADED for bare-metal */
#define WOLFSSL_SMALL_STACK
#define WOLFSSL_USER_IO                /* Custom I/O callbacks */
#define NO_FILESYSTEM
#define NO_WRITEV
#define NO_DEV_RANDOM                  /* SE TRNG provides entropy */

/* ---- Math (SP with Cortex-M assembly) ---- */
#define WOLFSSL_HAVE_SP_RSA
#define WOLFSSL_HAVE_SP_DH
#define WOLFSSL_HAVE_SP_ECC
#define WOLFSSL_SP_MATH_ALL
#define WOLFSSL_SP_SMALL
#define WOLFSSL_SP_ASM
#define WOLFSSL_SP_ARM_CORTEX_M_ASM

/* ---- Cryptography ---- */
#define HAVE_ECC
#define ECC_USER_CURVES
#define ECC_TIMING_RESISTANT
#define HAVE_AES_CBC
#define HAVE_AESGCM
#define GCM_SMALL
#define HAVE_CHACHA
#define HAVE_POLY1305
#define HAVE_ONE_TIME_AUTH
#define WC_RSA_BLINDING
#define WC_RSA_PSS

/* ---- Hashing ---- */
/* SHA-1 and SHA-256 are HW accelerated on all SE devices */
/* Uncomment for Secure Vault devices: */
/* #define WOLFSSL_SHA384 */
/* #define WOLFSSL_SHA512 */

/* ---- TLS ---- */
#define WOLFSSL_TLS13
#define HAVE_TLS_EXTENSIONS
#define HAVE_SUPPORTED_CURVES
#define HAVE_HKDF

/* ---- Reduce footprint ---- */
#define NO_OLD_TLS
#define NO_PSK
#define NO_DSA
#define NO_RC4
#define NO_MD4
#define NO_MD5
#define NO_DES3

/* ---- Testing ---- */
#define BENCH_EMBEDDED
#define USE_CERT_BUFFERS_256
#define USE_CERT_BUFFERS_2048
#define WOLFSSL_IGNORE_FILE_WARN

#endif /* WOLFSSL_USER_SETTINGS_H */
```

---

## 6. Additional Resources

- wolfSSL Silicon Labs port README: `wolfcrypt/src/port/silabs/README.md`
- Simplicity Studio integration guide: `IDE/SimplicityStudio/README.md`
- wolfSSL benchmarks: [https://www.wolfssl.com/docs/benchmarks/](https://www.wolfssl.com/docs/benchmarks/)
- wolfSSL documentation: [https://www.wolfssl.com/documentation/](https://www.wolfssl.com/documentation/)

**Silicon Labs Documentation (Public)**:
- SE Manager API reference: [https://docs.silabs.com/gecko-platform/latest/service/api/group-sl-se-manager](https://docs.silabs.com/gecko-platform/latest/service/api/group-sl-se-manager)
- EFR32 SE documentation: [https://docs.silabs.com/mcu/latest/efr32mg21/group-SE](https://docs.silabs.com/mcu/latest/efr32mg21/group-SE)
- Gecko SDK Crypto Doxygen: [https://siliconlabs.github.io/Gecko_SDK_Doc/](https://siliconlabs.github.io/Gecko_SDK_Doc/) (covers EFR32 Mighty Gecko, Blue Gecko, Flex Gecko)
- Gecko SDK source: [https://github.com/SiliconLabs/gecko_sdk](https://github.com/SiliconLabs/gecko_sdk)
- Gecko SDK documentation source: [https://github.com/SiliconLabs/Gecko_SDK_Doc](https://github.com/SiliconLabs/Gecko_SDK_Doc)

**Tested Hardware:**
- EFR32xG21 Starter Kit (Cortex-M33 at 80 MHz), Gecko SDK v3.2.2 and v4.2.3

**Benchmark Reference (EFR32xG21, SE Accel, Gecko SDK v3.2.2, -Os):**
- AES-256-GCM-enc: ~4.65 MiB/s
- SHA-256: ~8.03 MiB/s
- ECC P-256 key gen: ~171 ops/sec
- ECDSA P-256 sign: ~173 ops/sec
- ECDSA P-256 verify: ~160 ops/sec

> **Note:** Silicon Labs recommends using mbedTLS APIs or the SE Manager over raw `em_crypto.h` HAL calls for richer API coverage with hardware acceleration. The wolfSSL port follows this practice by interfacing through `sl_se_manager` exclusively, which provides the CRYPTO peripheral access (AES, SHA, ECC) through a managed abstraction layer.
