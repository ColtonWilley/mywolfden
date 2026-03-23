---
paths:
  - "**/ATECC*"
  - "**/ATTPM*"
  - "**/TA100*"
  - "**/CryptoAuth*"
---

# Microchip Secure Elements and Crypto Devices -- wolfSSL Platform Guide

## 1. Overview

wolfSSL provides deep integration with Microchip (formerly Atmel) secure elements and crypto hardware. This covers three major device families and one MCU crypto engine:

- **ATECC508A / ATECC608A** -- CryptoAuthentication secure elements providing hardware ECC P-256 operations (key generation, ECDSA sign/verify, ECDH), hardware RNG, and secure key storage. Communicated over I2C. The ATECC608A is the newer variant with additional security features.
- **TA100 (Trust Anchor)** -- Microchip's next-generation secure element with expanded cryptographic capabilities. Available in 14-pin, 8-pin, and 24-pad VQFN packages.
- **ATTPM20P** -- Microchip's discrete TPM 2.0 module, supported via wolfTPM.
- **PIC32MZ** -- Microchip 32-bit MCU with a built-in hardware crypto engine supporting AES, DES3, MD5, SHA, and SHA-256 acceleration, plus a hardware RNG.

The ATECC integration depends on Microchip's **CryptoAuthLib** (open source, available at `github.com/MicrochipTech/cryptoauthlib`), which provides the low-level I2C transport and command interface. wolfSSL's port layer in `wolfcrypt/src/port/atmel/atmel.c` wraps CryptoAuthLib API calls into wolfSSL-compatible functions and PK callbacks.

The reference integration example targets a **SAMD21 Cortex-M0 + ATECC508A + WINC1500 WiFi** stack using Atmel Software Framework (ASF), demonstrating both TLS client and server with hardware-accelerated ECC.

---

## 2. Build Configuration

### ATECC508A / ATECC608A

wolfSSL supports two integration methods:

**Method 1: Native wolfCrypt API** -- Hardware ECC operations are transparently used through the standard `wc_ecc_*` API.

```c
/* user_settings.h */
#define WOLFSSL_ATECC508A    /* or WOLFSSL_ATECC608A */
```

Or via configure:
```bash
./configure CFLAGS="-DWOLFSSL_ATECC608A"
```

**Method 2: PK Callbacks for TLS** -- Uses wolfSSL's PK callback mechanism to route TLS ECC operations to the secure element.

```c
/* user_settings.h */
#define HAVE_PK_CALLBACKS
#define WOLFSSL_ATECC_PKCB     /* PK callbacks without full init */
```

Or via configure:
```bash
./configure --enable-pkcallbacks CFLAGS="-DWOLFSSL_ATECC_PKCB"
./configure --with-cryptoauthlib=/path/to/cryptoauthlib
```

The `--with-cryptoauthlib` option links against `-lcryptoauth` and defines `WOLFSSL_ATECC508A` automatically.

**All ATECC-related build defines:**

| Define | Purpose |
|--------|---------|
| `WOLFSSL_ATECC508A` | Enable ATECC508A support (init, slot management, crypto ops) |
| `WOLFSSL_ATECC608A` | Enable ATECC608A support (same API, different device type) |
| `WOLFSSL_ATECC_PKCB` | Enable PK callback wrappers without full device init |
| `WOLFSSL_ATECC508A_TLS` | Enable TLS-specific device configuration |
| `WOLFSSL_ATECC_RNG` | Enable ATECC hardware RNG |
| `WOLFSSL_ATECC_SHA256` | Enable ATECC hardware SHA-256 |
| `WOLFSSL_ATECC_ECDH_ENC` | Use `atcab_ecdh_enc()` for encrypted ECDH (I2C bus protection) |
| `WOLFSSL_ATECC_ECDH_IOENC` | Use `atcab_ecdh_ioenc()` for I/O-encrypted ECDH |
| `WOLFSSL_ATECC_TNGTLS` | Enable Microchip Trust&GO (TNGTLS) module configuration |
| `WOLFSSL_ATECC_TFLXTLS` | Enable Microchip TrustFLEX with custom PKI configuration |
| `WOLFSSL_ATECC_DEBUG` | Enable debug printf messages for ATECC operations |
| `WOLFSSL_ATMEL` | Enable ASF hooks (random seeding via `atmel_get_random_number`) |
| `WOLFSSL_ATMEL_TIME` | Enable built-in ASF RTC time function |
| `ATECC_GET_ENC_KEY` | Macro to override the default encryption key retrieval function |
| `ATECC_SLOT_I2C_ENC` | Slot number for the I2C encryption key (default 4, or 6 for TNGTLS) |
| `ATECC_SLOT_AUTH_PRIV` | Slot number for device authentication private key (default 0) |
| `ATECC_SLOT_ECDHE_PRIV` | Slot number for ephemeral ECDHE private key (default 2) |
| `ATECC_MAX_SLOT` | Maximum number of dynamic slots (default 8, slots 0-7) |
| `WOLFSSL_ATECC508A_NOSOFTECC` | Disable software ECC fallback for non-P256 curves |
| `ATECC_I2C_ADDR` | I2C address (default 0xC0, or 0x6A for TNGTLS) |
| `ATECC_I2C_BUS` | I2C bus number (default 1) |

### PIC32MZ Crypto Engine

```c
/* user_settings.h */
#define MICROCHIP_PIC32
#define WOLFSSL_MICROCHIP_PIC32MZ
```

This automatically enables:
- `WOLFSSL_PIC32MZ_CRYPT` -- Hardware AES/DES3 acceleration (disable with `NO_PIC32MZ_CRYPT`)
- `WOLFSSL_PIC32MZ_RNG` -- Hardware RNG (disable with `NO_PIC32MZ_RNG`)
- `WOLFSSL_PIC32MZ_HASH` -- Hardware MD5/SHA/SHA-256 hashing (disable with `NO_PIC32MZ_HASH`)

The PIC32 base define also sets:
```c
#define SIZEOF_LONG_LONG 8
#define SINGLE_THREADED
#define WOLFSSL_USER_IO    /* unless MICROCHIP_TCPIP_BSD_API is defined */
#define NO_WRITEV
#define NO_DEV_RANDOM
#define NO_FILESYSTEM
#define TFM_TIMING_RESISTANT
```

**Microchip TCP/IP stack integration:**
- `MICROCHIP_TCPIP_V5` -- Legacy Microchip TCP/IP stack v5
- `MICROCHIP_TCPIP` -- Current Microchip TCP/IP stack
- `MICROCHIP_TCPIP_BSD_API` -- Use BSD socket API (no custom I/O needed)
- `MICROCHIP_MPLAB_HARMONY` -- MPLAB Harmony framework integration
- `MICROCHIP_MPLAB_HARMONY_3` -- MPLAB Harmony 3 framework (auto-configures ATECC608A via `atecc608_0_init_data`)

---

## 3. Platform-Specific Features

### Slot Management (ATECC508A/608A)

The ATECC devices have 8 key slots (0-7) managed by wolfSSL's slot allocator in `atmel.c`. Default slot assignments:

| Slot | Purpose | Define |
|------|---------|--------|
| 0 | Device authentication private key (signing) | `ATECC_SLOT_AUTH_PRIV` |
| 2 | Ephemeral ECDHE private key | `ATECC_SLOT_ECDHE_PRIV` |
| 4 (or 6 for TNGTLS) | I2C transport encryption key | `ATECC_SLOT_I2C_ENC` |
| 7 (or 6 for TNGTLS) | Parent encryption key | `ATECC_SLOT_ENC_PARENT` |

wolfSSL provides a custom slot allocator API:
```c
int atmel_set_slot_allocator(atmel_slot_alloc_cb alloc, atmel_slot_dealloc_cb dealloc);
```

This allows applications to override the default slot allocation strategy. Slots 0 and 4 (or their TNGTLS equivalents) are permanently reserved and not returned to the free pool.

### PK Callbacks for TLS

The reference PK callbacks in `atmel.c` handle TLS ECC operations:

```c
wolfSSL_CTX_SetEccKeyGenCb(ctx, atcatls_create_key_cb);
wolfSSL_CTX_SetEccVerifyCb(ctx, atcatls_verify_signature_cb);
wolfSSL_CTX_SetEccSignCb(ctx, atcatls_sign_certificate_cb);
wolfSSL_CTX_SetEccSharedSecretCb(ctx, atcatls_create_pms_cb);
```

The key generation callback supports software fallback for non-P256 curves (unless `WOLFSSL_ATECC508A_NOSOFTECC` is defined). P-256 operations are always routed to the hardware.

### Trust&GO and TrustFLEX Certificate Handling

When `WOLFSSL_ATECC_TNGTLS` is enabled, wolfSSL reads the device and signer certificates directly from the ATECC device using CryptoAuthLib's TNG API:
- `tng_atcacert_max_signer_cert_size()` -- Get signer certificate buffer size
- `tng_atcacert_read_signer_cert()` -- Read the signer (intermediate CA) certificate
- `tng_atcacert_read_device_cert()` -- Read the device certificate

When `WOLFSSL_ATECC_TFLXTLS` is enabled, the TrustFLEX custom PKI path reads certificates using the `cust_def_device` and `cust_def_signer` structures from CryptoAuthLib.

### Hardware RNG

The ATECC provides a true random number generator accessible via:
```c
int atmel_get_random_number(uint32_t count, uint8_t* rand_out);
int atmel_get_random_block(unsigned char* output, unsigned int sz);
```

For direct HW RNG use without the DRBG:
```c
#define CUSTOM_RAND_GENERATE_BLOCK  atmel_get_random_block
```

### I2C Bus Encryption

ATECC devices support encrypted I2C communication to prevent bus snooping. wolfSSL supports two modes:
- `WOLFSSL_ATECC_ECDH_ENC` -- Uses `atcab_ecdh_enc()` with a slot-based encryption key
- `WOLFSSL_ATECC_ECDH_IOENC` -- Uses `atcab_ecdh_ioenc()` with an I/O protection key

The encryption key is initialized during `atmel_init()` and can be customized by defining `ATECC_GET_ENC_KEY(enckey, keysize)`.

### PIC32MZ Crypto Engine

The PIC32MZ hardware crypto engine accelerates:
- **AES**: ECB, CBC, CFB, OFB, CTR, GCM modes
- **DES/3DES**: ECB, CBC, CFB, OFB modes
- **Hashing**: MD5, SHA-1, SHA-256 (including HMAC)
- **Large hash support**: Enabled by `WOLFSSL_PIC32MZ_LARGE_HASH` (requires exclusive crypto hardware access at the application layer)

The engine uses DMA-based buffer descriptors and security association structures defined in `pic32mz-crypt.h`.

---

## 4. Common Issues

### CryptoAuthLib Not Found

**Issue:** Build fails with `cryptoauthlib isn't found` when using `--with-cryptoauthlib`.
**Resolution:** Ensure CryptoAuthLib is installed and specify the correct path. The library must provide `cryptoauthlib.h` and `libcryptoauth.so`/`.a`. Install from source at `github.com/MicrochipTech/cryptoauthlib` or via your package manager.

### I2C Communication Failures

**Issue:** `atcab_init()` fails or crypto operations return errors.
**Resolution:** Verify:
1. Correct I2C bus number (`ATECC_I2C_BUS`, default 1; Raspberry Pi uses `/dev/i2c-1`)
2. Correct I2C address (`ATECC_I2C_ADDR`, default 0xC0; TNGTLS uses 0x6A)
3. I2C bus permissions (on Linux, the user must have access to `/dev/i2c-N`)
4. Wake delay and retry settings are appropriate for your bus speed

### Only P-256 Supported

**Issue:** Non-P256 ECC operations fail or fall back to software.
**Resolution:** The ATECC508A/608A hardware only supports ECC SECP256R1 (NIST P-256). For other curves, wolfSSL uses software fallback unless `WOLFSSL_ATECC508A_NOSOFTECC` is defined. If your application requires P-384 or P-521 in hardware, the ATECC family is not suitable.

### Slot Exhaustion

**Issue:** `atmel_ecc_alloc()` returns `ATECC_INVALID_SLOT` (0xFF).
**Resolution:** The ATECC has only 8 slots (0-7) with several reserved. Ensure slots are freed after use with `atmel_ecc_free()`. For concurrent TLS sessions, a custom slot allocator may be needed. Consider the total number of simultaneous ECC operations your application requires.

### Harmony 3 Integration

**Issue:** ATECC608A not initialized correctly under MPLAB Harmony 3.
**Resolution:** When `MICROCHIP_MPLAB_HARMONY_3` is defined, wolfSSL expects an externally defined `atecc608_0_init_data` (type `ATCAIfaceCfg`) generated by the Harmony 3 configurator. Ensure your Harmony 3 project has the CryptoAuthLib component properly configured and that this symbol is exported.

### PIC32MZ Cache Coherency

**Issue:** Crypto operations produce incorrect results on PIC32MZ.
**Resolution:** The PIC32MZ crypto engine uses DMA and requires cache-coherent memory. The port code uses `KVA_TO_PA()` for physical address translation and checks RAM boundaries with `PIC32MZ_IF_RAM()`. Ensure buffers passed to crypto functions are in cacheable RAM and that cache is properly managed. Some EF-series parts do not support output byte swapping (`PIC32_NO_OUT_SWAP`).

### ATECC Default Encryption Key

**Issue:** I2C bus encryption uses a default all-0xFF key, which is insecure.
**Resolution:** The default `atmel_get_enc_key_default()` fills the key with 0xFF. For production deployments, define `ATECC_GET_ENC_KEY(enckey, keysize)` to provide your own encryption key retrieval function that reads from secure storage.

---

## 5. Example Configuration

### ATECC508A with SAMD21 (Bare Metal, ASF)

Based on the reference `user_settings.h` from the CryptoAuth example:

```c
/* user_settings.h -- wolfSSL for SAMD21 + ATECC508A + WINC1500 */
#ifndef WOLFSSL_USER_SETTINGS_H
#define WOLFSSL_USER_SETTINGS_H

/* ---- Platform ---- */
#define WOLFSSL_ATMEL
#define WOLFSSL_GENERAL_ALIGNMENT   4
#define SINGLE_THREADED
#define WOLFSSL_SMALL_STACK

/* ---- Secure Element ---- */
#define WOLFSSL_ATECC508A           /* or WOLFSSL_ATECC608A */
#define WOLFSSL_ATECC508A_TLS       /* TLS device configuration */
#define ATECC_I2C_BUS  2            /* SAMD21 SERCOM2 I2C */

/* ---- Time ---- */
#define WOLFSSL_USER_CURRTIME
#define WOLFSSL_GMTIME
#define USER_TICKS
#define WOLFSSL_ATMEL_TIME          /* ASF RTC time support */

/* ---- Network ---- */
#define WOLFSSL_USER_IO             /* Custom I/O for WINC1500 */

/* ---- Math ---- */
#define USE_FAST_MATH
#define TFM_TIMING_RESISTANT

/* ---- TLS Features ---- */
#define KEEP_PEER_CERT
#define HAVE_PK_CALLBACKS           /* Route ECC to ATECC508A */

/* ---- Crypto ---- */
#define HAVE_ECC
#define ECC_USER_CURVES             /* P-256 only */
#define ECC_TIMING_RESISTANT
#define ALT_ECC_SIZE
#define HAVE_AESGCM
#define GCM_SMALL                   /* Low-memory GCM */

/* ---- RNG: Use ATECC508A hardware RNG directly ---- */
#define CUSTOM_RAND_GENERATE_BLOCK  atmel_get_random_block

/* ---- Disable Unused Features ---- */
#define NO_RSA
#define NO_DSA
#define NO_DH
#define NO_DES3
#define NO_RC4
#define NO_OLD_TLS
#define NO_HC128
#define NO_RABBIT
#define NO_PSK
#define NO_MD4
#define NO_MD5
#define NO_PWDBASED
#define NO_FILESYSTEM
#define NO_WRITEV
#define NO_MAIN_DRIVER
#define NO_WOLFSSL_MEMORY
#define BENCH_EMBEDDED
#define USE_CERT_BUFFERS_2048
#define USE_CERT_BUFFERS_256

#endif /* WOLFSSL_USER_SETTINGS_H */
```

### ATECC608A with MPLAB Harmony 3

```c
/* user_settings.h -- wolfSSL for PIC32 + ATECC608A + Harmony 3 */
#ifndef WOLFSSL_USER_SETTINGS_H
#define WOLFSSL_USER_SETTINGS_H

#define WOLFSSL_ATECC608A
#define MICROCHIP_MPLAB_HARMONY_3   /* Uses atecc608_0_init_data from Harmony */
#define HAVE_PK_CALLBACKS
#define HAVE_ECC
#define ECC_USER_CURVES
#define SINGLE_THREADED
#define WOLFSSL_SMALL_STACK
#define NO_FILESYSTEM
#define NO_WRITEV

/* Harmony 3 provides its own time and network I/O */

#endif /* WOLFSSL_USER_SETTINGS_H */
```

### PIC32MZ with Hardware Crypto

```c
/* user_settings.h -- wolfSSL for PIC32MZ with crypto engine */
#ifndef WOLFSSL_USER_SETTINGS_H
#define WOLFSSL_USER_SETTINGS_H

#define MICROCHIP_PIC32
#define WOLFSSL_MICROCHIP_PIC32MZ

/* Hardware crypto engine features (enabled by default with PIC32MZ): */
/* WOLFSSL_PIC32MZ_CRYPT -- AES/DES3 acceleration */
/* WOLFSSL_PIC32MZ_RNG   -- Hardware RNG */
/* WOLFSSL_PIC32MZ_HASH  -- MD5/SHA/SHA-256 acceleration */

/* To selectively disable: */
/* #define NO_PIC32MZ_CRYPT */
/* #define NO_PIC32MZ_RNG */
/* #define NO_PIC32MZ_HASH */

/* Microchip TCP/IP stack */
#define MICROCHIP_TCPIP
#define MICROCHIP_MPLAB_HARMONY
/* #define MICROCHIP_TCPIP_BSD_API */  /* Uncomment for BSD sockets */

#define HAVE_ECC
#define HAVE_AESGCM
#define HAVE_TLS_EXTENSIONS
#define HAVE_SUPPORTED_CURVES

#endif /* WOLFSSL_USER_SETTINGS_H */
```

---

## 6. Additional Resources

**Source Code:**
- wolfSSL ATECC port: `wolfcrypt/src/port/atmel/atmel.c`
- ATECC header: `wolfssl/wolfcrypt/port/atmel/atmel.h`
- ATECC port README: `wolfcrypt/src/port/atmel/README.md`
- PIC32MZ crypto port: `wolfcrypt/src/port/pic32/pic32mz-crypt.c`
- PIC32MZ header: `wolfssl/wolfcrypt/port/pic32/pic32mz-crypt.h`

**Example Projects:**
- CryptoAuth TLS demo (SAMD21 + ATECC508A + WINC1500): `examples-private/microchip/cryptoauth/`
- ATECC datasheets and application notes: `examples-private/microchip/atecc/`
- TA100 lab materials and datasheets: `examples-private/microchip/ta100/`

**External:**
- CryptoAuthLib (open source): `github.com/MicrochipTech/cryptoauthlib`
- wolfSSL ATECC page: `wolfssl.com/wolfSSL/wolfssl-atmel.html`
- wolfSSL Manual: `wolfssl.com/documentation/`

**Benchmarks (SAMD21 48MHz Cortex-M0, ECC P-256):**

| Operation | Software (ms) | ATECC508A HW (ms) | Speedup |
|-----------|--------------|-------------------|---------|
| Key Generation | 3123 | 144 | 21.7x |
| ECDH Agreement | 3117 | 134 | 23.3x |
| ECDSA Sign | 1997 | 293 | 6.8x |
| ECDSA Verify | 5057 | 208 | 24.3x |
| TLS Handshake | 13422 | 2342 | 5.7x |
