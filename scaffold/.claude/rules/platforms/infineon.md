---
paths:
  - "**/infineon*"
  - "**/Infineon*"
  - "**/AURIX*"
  - "**/SLB96*"
---

# Infineon (AURIX, PSoC 6, TPM) — wolfSSL Platform Guide

## 1. Overview

Infineon produces several families of microcontrollers and security modules that wolfSSL integrates with. The primary targets covered in this guide are:

- **AURIX TC2xx/TC3xx** — Automotive-grade TriCore microcontrollers with a dedicated Hardware Security Module (HSM), a Cortex-M3 core running at 100 MHz that provides a trusted environment for secure operations. wolfSSL runs on the HSM core with optional hardware crypto acceleration.
- **PSoC 6** — Arm Cortex-M4/M0+ dual-core MCUs (formerly Cypress, now Infineon) with hardware crypto via the Peripheral Driver Library (PDL). wolfSSL provides a dedicated port layer under `wolfssl/wolfcrypt/port/cypress/psoc6_crypto.h`.
- **Infineon TPM (SLB9670/SLB9672)** — Discrete TPM 2.0 modules used with **wolfTPM**. wolfSSL has extensive examples and vendor documentation in the examples-private repository.

---

## 2. Build Configuration

### 2.1 AURIX TC3xx HSM

The AURIX HSM integration uses `user_settings.h` (no autoconf/configure). The HSM is a standalone Cortex-M3 core, so wolfSSL is cross-compiled with `arm-none-eabi-gcc`.

**Build command:**

```bash
# From the TC3xx HSM project directory
make TOOLCHAIN=/path/to/toolchain/arm-none-eabi-
```

Key `user_settings.h` options for the HSM core:

| Define | Purpose |
|---|---|
| `WOLFSSL_USER_SETTINGS` | Required — no autoconf on bare-metal HSM |
| `SP_WORD_SIZE 32` | 32-bit SP math for Cortex-M3 |
| `WOLFSSL_SP_ARM_CORTEX_M_ASM` | SP assembly optimizations for Cortex-M |
| `WOLFSSL_HAVE_SP_ECC` | SP math ECC support |
| `WOLFSSL_HAVE_SP_RSA` | SP math RSA support |
| `NO_FILESYSTEM` | Bare-metal — no filesystem |
| `NO_DEV_RANDOM` | No `/dev/random` — use HSM TRNG |
| `SINGLE_THREADED` | No RTOS on HSM core |

### 2.2 PSoC 6 (ModusToolbox / PDL)

| Define | Purpose |
|---|---|
| `WOLFSSL_PSOC6_CRYPTO` | Master enable for PSoC 6 hardware crypto acceleration |
| `WOLFSSL_USER_SETTINGS` | Required for ModusToolbox builds |

When `WOLFSSL_PSOC6_CRYPTO` is defined, the port header automatically enables hardware acceleration for the algorithms that are not disabled in your configuration:

- `PSOC6_HASH_SHA1` — enabled unless `NO_SHA` is defined
- `PSOC6_HASH_SHA2` — enabled unless `NO_SHA256` is defined (also covers SHA-224/384/512)
- `PSOC6_HASH_SHA3` — enabled when `WOLFSSL_SHA3` is defined
- `PSOC6_CRYPTO_AES` — enabled unless `NO_AES` is defined

The port includes `cy_pdl.h` from the Infineon PDL. This is the correct crypto path — the HAL layer does **not** have a crypto driver, so all crypto operations go through PDL directly.

### 2.3 TPM (SLB9670/SLB9672)

TPM integration uses **wolfTPM**, not wolfSSL directly. wolfTPM handles the TPM 2.0 command layer over SPI. See the wolfTPM documentation for build configuration.

For Raspberry Pi with SLB9670, the device tree overlay must be configured:

```
# In /boot/config.txt
dtoverlay=tpm-slb9670
```

SPI clock speed may need to be reduced to 12 MHz for reliable operation. See the device tree overlay modification instructions in the wolfSSL examples-private repository.

---

## 3. Platform-Specific Features

### 3.1 AURIX TC3xx HSM Crypto Acceleration

The TC3xx HSM hardware supports acceleration for:

- **AES-128** (CBC, ECB, GCM via software on HSM core)
- **TRNG** (True Random Number Generator)
- **PKC** — Public Key Cryptography engine supporting **ECC P-256**
- **SHA-1, SHA-224, SHA-256** (hardware hash)
- **MD5** (hardware hash, legacy)

The HSM communicates with the TriCore host via shared bridge memory. Commands are sent from the TriCore application core and responses are read back from shared memory.

**Memory layout:**

- HSM boot code loads into PF0 sector S1 at `0xA0004000`
- HSM application starts at `0x80060000`
- Encryption keys are stored in DF1 EEPROM (128 KB) at `0xAFC00000`

**Binary size reference** (TC367DP, wolfcrypt-only, -Os):

```
   text     data      bss      dec      hex  filename
 103808      464    74144   178416    2b8f0  HSM_App.elf
```

### 3.2 PSoC 6 Hardware Crypto

The PSoC 6 crypto port (`psoc6_crypto.h`) provides hardware-accelerated:

- **AES** — ECB, CBC, CFB, GCM, and direct encrypt/decrypt modes
- **SHA-1** — via `wc_Psoc6_Sha1_Sha2_Init()` with `WC_PSOC6_SHA1` mode
- **SHA-2 family** — SHA-224, SHA-256, SHA-384, SHA-512, SHA-512/224, SHA-512/256
- **SHA-3** — Init, Update, Final, and SHAKE squeeze operations
- **ECC verification** — `psoc6_ecc_verify_hash_ex()` for hardware ECDSA verify

The hardware engine is accessed through `PSOC6_CRYPTO_BASE` mapped to `CRYPTO_BASE`.

Initialize with `psoc6_crypto_port_init()` before using any hardware-accelerated operations.

### 3.3 Infineon TPM 2.0 Modules

wolfSSL maintains examples for two Infineon TPM modules:

- **SLB9670** — TPM 2.0 discrete chip, commonly used on Raspberry Pi via SPI. Supports firmware versions 7.61 through 7.85. FIPS 140-2 and CC-EAL4 certified (firmware-version dependent).
- **SLB9672** — Newer TPM 2.0 module with firmware 15.xx series. Includes firmware update tools and additional application notes.

Both modules connect via SPI and are supported through wolfTPM's TIS (TPM Interface Specification) layer.

### 3.4 AURIX HSM Programming

Programming the HSM requires careful sequencing to avoid permanently locking the device:

1. Flash HSM boot code, HSM application, and TriCore application **first**
2. Then enable the HSM boot bit via `UCB_HSMCOTP0` using the UCB tool
3. Programming tools: Infineon MemTool + miniWiggler, AURIX Development Studio, or third-party debuggers (iSystem, UDE, Lauterbach)

**Critical warning:** Enabling HSM boot when no valid HSM code is present will **permanently lock** the device. During development, keep the UCB confirmation code in the `Unlocked` state (`0x4321 1234`).

---

## 4. Common Issues

### 4.1 HSM Flash Alignment

AURIX HSM flash must be 32-byte aligned with zero padding. Misaligned writes can corrupt the HSM code and potentially lock the device.

### 4.2 HSM Boot ROM Breakpoint

The boot ROM sets an on-chip breakpoint that prevents the HSM from starting. This must be cleared either via a debugger or from the TriCore application code:

```c
// TriCore core — clear HSM debug registers
MEM(0xF0041010) = 0xE0000000; // Set HSM DBGBASE
MEM(0xF0052008) = 0x00000000; // Delete boot ROM breakpoint
```

### 4.3 PSoC 6 HAL vs. PDL for Crypto

The Infineon HAL (Hardware Abstraction Layer) does **not** include a crypto driver. All crypto operations on PSoC 6 must go through the PDL (Peripheral Driver Library) directly. If your project is structured around HAL APIs, you still need PDL for crypto — include `cy_pdl.h` and ensure the PDL crypto sources are in your build.

### 4.4 PSoC 6 SHA-3 Availability

SHA-3 hardware acceleration on PSoC 6 requires both `WOLFSSL_SHA3` and `WOLFSSL_PSOC6_CRYPTO` to be defined. Not all PSoC 6 variants include SHA-3 hardware — verify your specific device's crypto block capabilities.

### 4.5 SLB9670 SPI Clock Speed

The SLB9670 TPM may exhibit communication errors at high SPI clock speeds. Reducing the SPI clock to 12 MHz (from the default 32 MHz on Raspberry Pi) resolves most reliability issues. This requires modifying the device tree overlay.

### 4.6 TPM Firmware Updates

Infineon TPM firmware updates are one-way and cannot be reversed. The SLB9670 supports a maximum of 64 firmware updates. Each update resets the TPM to factory defaults. Always verify the firmware image is valid for your specific TPM variant before applying.

### 4.7 AURIX TC2xx vs. TC3xx HSM Differences

The HSM implementation differs between TC2xx and TC3xx families. Infineon provides a dedicated application note (AP32489) covering the migration differences. Key changes include debug protection behavior and cache usage on TC3xx.

---

## 5. Example Configuration

### 5.1 Minimal `user_settings.h` — AURIX TC3xx HSM

```c
/* user_settings.h — AURIX TC3xx HSM (Cortex-M3) */

#define WOLFSSL_USER_SETTINGS

/* Bare-metal HSM core */
#define NO_FILESYSTEM
#define NO_DEV_RANDOM
#define SINGLE_THREADED
#define NO_WRITEV
#define NO_MAIN_DRIVER

/* Math: SP with Cortex-M assembly */
#define WOLFSSL_SP_MATH_ALL
#define SP_WORD_SIZE 32
#define WOLFSSL_SP_ARM_CORTEX_M_ASM
#define WOLFSSL_HAVE_SP_ECC
#define WOLFSSL_HAVE_SP_RSA
#define WOLFSSL_HAVE_SP_DH

/* Algorithms */
#define HAVE_ECC
#define HAVE_AES_CBC
#define HAVE_AESGCM
#define WOLFSSL_AES_128
#define WOLFSSL_SHA384

/* Timing resistance */
#define TFM_TIMING_RESISTANT
#define ECC_TIMING_RESISTANT
#define WC_RSA_BLINDING

/* Size optimization */
#ifndef DEBUG_WOLFSSL
    #define NO_ERROR_STRINGS
#endif
```

### 5.2 Minimal `user_settings.h` — PSoC 6 with Hardware Crypto

```c
/* user_settings.h — PSoC 6 with PDL crypto */

#define WOLFSSL_USER_SETTINGS
#define WOLFSSL_PSOC6_CRYPTO

/* Algorithms (hardware-accelerated via PDL) */
#define HAVE_ECC
#define HAVE_AES_CBC
#define HAVE_AESGCM
#define WOLFSSL_AES_DIRECT
#define WOLFSSL_SHA384
#define WOLFSSL_SHA512

/* TLS features */
#define HAVE_TLS_EXTENSIONS
#define HAVE_SUPPORTED_CURVES
#define HAVE_ALPN

/* Threading (if using RTOS) */
/* #define SINGLE_THREADED */

/* Math */
#define WOLFSSL_SP_MATH_ALL
#define SP_WORD_SIZE 32
#define WOLFSSL_HAVE_SP_ECC
#define WOLFSSL_HAVE_SP_RSA
```

---

## 6. Additional Resources

### Vendor Documentation (Public)

**AURIX TC3xx:**
- AURIX TC3xx User Manual (Architecture vol. 2): free download with myInfineon registration at infineon.com
- AURIX HSM Training PDF: "Infineon-AURIX_Hardware_Security_Module-Training-v01_01-EN.pdf" — direct download from Infineon
- Getting Started with AURIX Development Studio: "Infineon-AURIX_Getting_Started_with_AURIX_Development_Studio-GettingStarted-v01_11-EN.pdf"
- HSM application notes available from Infineon: AP32349 (HSM Startup), AP32373 (HSM Demo Examples), AP32391 (Secure Boot), AP32399 (Debug Protection), AP32489 (TC2xx vs TC3xx HSM changes), AP32543 (HSM hardware security use-cases), AP32574 (HSM Performance Figures)

**PSoC 6 / ModusToolbox:**
- PDL Crypto API Reference: infineon.github.io/psoc6pdl/ (public, no login)
- PDL source on GitHub: github.com/Infineon/mtb-pdl-cat1 — crypto headers at `drivers/include/cy_crypto_core.h`
- Hardware-accelerated mbedTLS (reference for crypto block capabilities): github.com/Infineon/cy-mbedtls-acceleration
- ModusToolbox main site: infineon.com/modustoolbox

**Infineon TPM (Public):**
- SLB9670 datasheet: "Infineon-TPM SLB 9670 2.0-DS-v11_15-EN.pdf"
- TPM 2.0 User Guidance: "IFX_TPM_2.0_AN_User_Guidance" (multiple revisions available)
- SLB9672 datasheet and firmware update documentation available from Infineon
- Raspberry Pi TPM setup guide: letstrust.de (LetsTrust TPM overlay for Pi)

**Internal wolfSSL Integration Code:**
- AURIX TC3xx HSM integration: examples-private/infineon/tc3xx/ — includes HSM boot, application code, benchmarks, and TriCore host examples
- SLB9670 TPM examples: examples-private/infineon/slb9670_tpm/ — wiring diagrams, firmware update procedures, Raspberry Pi kernel build notes
- SLB9672 TPM examples: examples-private/infineon/slb9672_tpm/ — datasheets, firmware update tools (IFXTPMUpdate, TPMFactoryUpd), application notes
