---
paths:
  - "**/simplelink*"
  - "**/SimpleLink*"
  - "**/ti-*"
---

# Texas Instruments SimpleLink / TI-RTOS — wolfSSL Platform Guide

## 1. Overview

Texas Instruments produces the SimpleLink family of wireless MCUs (CC32xx, CC13xx, CC26xx) and the MSP432/TivaC series, all of which can run wolfSSL under TI-RTOS (now called TI-RTOS Kernel / SYS/BIOS). wolfSSL provides:

- **`WOLFSSL_TIRTOS`** define in `settings.h` that configures wolfSSL for the TI-RTOS environment
- **Hardware crypto port** under `wolfssl/wolfcrypt/port/ti/` with `ti-ccm.h` (CCM hardware driver mutex/init) and `ti-hash.h` (hardware hash type definitions)
- **Hardware crypto source** in `wolfcrypt/src/port/ti/` with `ti-aes.c`, `ti-des3.c`, `ti-hash.c`, and `ti-ccm.c` implementing AES, DES, hash, and CCM driver management via the TI DTHE (Data Transfer and Hash Engine)
- **CCS examples** in the wolfssl-examples repository under `tirtos_ccs_examples/` with TCP echo client/server, wolfCrypt tests, and benchmarks for the TivaC TM4C1294NCPDT

---

## 2. Build Configuration

### 2.1 Key Preprocessor Defines

| Define | Purpose |
|---|---|
| `WOLFSSL_TIRTOS` | Master enable for TI-RTOS platform support |
| `WOLFSSL_TI_HASH` | Enable TI hardware hash acceleration (MD5, SHA-1, SHA-224, SHA-256) |
| `WOLFSSL_TI_CRYPT` | Enable TI hardware symmetric cipher acceleration (AES, DES3) |

### 2.2 Defines Set Automatically by `WOLFSSL_TIRTOS`

When `WOLFSSL_TIRTOS` is defined in `settings.h`, the following are configured automatically:

| Auto-defined | Value/Effect |
|---|---|
| `SIZEOF_LONG_LONG` | 8 |
| `NO_WRITEV` | No writev support |
| `NO_WOLFSSL_DIR` | No directory operations |
| `SP_WORD_SIZE` | 32 (unless `USE_FAST_MATH` is defined) |
| `WOLFSSL_HAVE_SP_ECC` | SP math ECC enabled |
| `WOLFSSL_HAVE_SP_RSA` | SP math RSA enabled (unless `NO_RSA`) |
| `WOLFSSL_HAVE_SP_DH` | SP math DH enabled (unless `NO_DH`) |
| `TFM_TIMING_RESISTANT` | Timing-resistant math |
| `ECC_TIMING_RESISTANT` | Timing-resistant ECC |
| `WC_RSA_BLINDING` | RSA blinding enabled |
| `NO_DEV_RANDOM` | No `/dev/random` |
| `NO_FILESYSTEM` | No filesystem |
| `NO_MAIN_DRIVER` | No `main()` from wolfSSL |
| `HAVE_ECC` | ECC enabled |
| `HAVE_ALPN` | ALPN extension enabled |
| `USE_WOLF_STRTOK` | wolfSSL's own strtok (for ALPN) |
| `HAVE_TLS_EXTENSIONS` | TLS extensions enabled |
| `HAVE_SUPPORTED_CURVES` | Supported curves extension |
| `HAVE_AESGCM` | AES-GCM enabled |
| `USE_CERT_BUFFERS_2048` | Use 2048-bit cert buffers for tests (unless `NO_CRYPT_TEST`) |
| `NO_ERROR_STRINGS` | Disabled unless `DEBUG_WOLFSSL` is defined |

### 2.3 TI Time Handling

wolfSSL includes `<ti/sysbios/hal/Seconds.h>` for time support. When using the TI compiler (`__ti__`), `NO_TIME_SIGNEDNESS_CHECK` is defined because TI's internal `time()` offsets by 2208988800 (1900 to 1970 epoch), which overflows a signed 32-bit value.

### 2.4 Build System

wolfSSL for TI-RTOS is built using TI's XDC (eXpress DSP Components) make system:

```bash
# From wolfssl/tirtos/ directory
../../xdctools_X_XX_XX_XX_core/gmake.exe -f wolfssl.mak
```

The build requires a `products.mak` file that specifies paths to:

- XDCtools installation
- SYS/BIOS (TI-RTOS Kernel)
- NDK (Network Developer's Kit)
- TivaWare C Series drivers
- TI ARM compiler (ti-cgt-arm)

### 2.5 Port Header Locations

```
wolfssl/wolfcrypt/port/ti/
    ti-ccm.h        # CCM hardware driver init and mutex (lock/unlock)
    ti-hash.h       # wolfssl_TI_Hash type, hash algorithm typedefs

wolfcrypt/src/port/ti/
    ti-aes.c        # AES hardware acceleration via DTHE
    ti-ccm.c        # CCM hardware driver initialization and locking
    ti-des3.c       # DES/3DES hardware acceleration via DTHE
    ti-hash.c       # MD5, SHA-1, SHA-224, SHA-256 hardware acceleration
```

---

## 3. Platform-Specific Features

### 3.1 Hardware Crypto via DTHE Engine

The TI SimpleLink CC32xx family includes a DTHE (Data Transfer and Hash Engine) that provides hardware acceleration for:

- **AES** — ECB, CBC, CCM, GCM modes
- **DES/3DES** — ECB, CBC modes
- **SHA** — MD5, SHA-1, SHA-224, SHA-256
- **HMAC** — Hardware HMAC for MD5, SHA-1, SHA-224, SHA-256

Enable with `WOLFSSL_TI_CRYPT` (symmetric ciphers) and `WOLFSSL_TI_HASH` (hash algorithms).

### 3.2 Hardware Hash Type Replacement

When `WOLFSSL_TI_HASH` is defined, wolfSSL replaces its software hash structures with the `wolfssl_TI_Hash` structure:

```c
typedef struct {
    byte   *msg;
    word32 used;
    word32 len;
    byte hash[WOLFSSL_MAX_HASH_SIZE];
} wolfssl_TI_Hash;
```

This structure is typedef'd to `wc_Md5`, `wc_Sha`, `wc_Sha256`, and `wc_Sha224` when `WOLFSSL_TI_HASH` is defined. The initial buffer size is `WOLFSSL_TI_INITBUFF` (default 64 bytes), and max hash output is `WOLFSSL_MAX_HASH_SIZE` (default 64 bytes).

`WOLFSSL_NO_HASH_RAW` is automatically defined when using TI hardware hashing.

### 3.3 CCM Driver Mutex

The TI crypto hardware requires exclusive access. The CCM driver provides initialization and locking:

- `wolfSSL_TI_CCMInit()` — Initialize the hardware crypto module
- `wolfSSL_TI_lockCCM()` / `wolfSSL_TI_unlockCCM()` — Mutex for multi-threaded access

In `SINGLE_THREADED` mode, the lock/unlock macros are no-ops.

### 3.4 SP Math Configuration

Under `WOLFSSL_TIRTOS`, SP math is configured for 32-bit word size with ECC, RSA, and DH support. If `SP_INT_MAX_BITS >= 4096`, 4096-bit RSA/DH is also enabled (`WOLFSSL_SP_4096`).

Fast math (`USE_FAST_MATH`) can be used as an alternative — when defined, the SP math auto-configuration is skipped.

---

## 4. Common Issues

### 4.1 Products.mak Version Strings

The `products.mak` file requires exact version strings for XDCtools, SYS/BIOS, NDK, TivaWare, and the TI compiler. Version mismatches are the most common build failure. Browse `C:\ti\` (or your install directory) and update all `X_XX_XX_XX` placeholders to match the installed versions exactly. Note that `XDC_INSTALL_DIR` may require a `_core` suffix depending on your XDCtools version.

### 4.2 TI Compiler Time Overflow

The TI compiler's `time()` function uses a 1900-based epoch, adding 2208988800 seconds to convert to the 1970 epoch. This overflows a signed 32-bit integer. wolfSSL handles this automatically when `WOLFSSL_TIRTOS` is defined by setting `NO_TIME_SIGNEDNESS_CHECK`, but custom time implementations should be aware of this.

### 4.3 No SHA-384/SHA-512 in Hardware

The TI DTHE engine on CC32xx supports MD5, SHA-1, SHA-224, and SHA-256 only. SHA-384 and SHA-512 are computed in software. If your application requires SHA-384/SHA-512, ensure the software implementations are enabled (they are by default).

### 4.4 Random Number Generation

`WOLFSSL_TIRTOS` sets `NO_DEV_RANDOM`. You must provide a hardware RNG source. On CC32xx, use the TI driverlib TRNG. For the DTHE-equipped devices, the hardware RNG is typically available through the SimpleLink SDK.

### 4.5 CCS Project Include Paths

When importing wolfSSL into a Code Composer Studio project, two paths must be manually configured:

- **ARM Compiler Include Options**: Add the wolfSSL root directory (e.g., `"C:/ti/wolfssl"`)
- **ARM Linker File Search Path**: Add the wolfSSL library path (`wolfssl/tirtos/packages/ti/net/wolfssl/lib/`) and the library file (`wolfssl.aem4f`)

Missing these paths results in header-not-found or linker errors.

### 4.6 IAR Compiler Warning Suppression

When using IAR under TI-RTOS, wolfSSL automatically suppresses warning Pa089 (related to pointer casting). For non-GCC/non-IAR compilers (typically the TI compiler), diagnostic 11 is suppressed instead.

---

## 5. Example Configuration

### 5.1 Minimal `user_settings.h` — CC32xx with Hardware Crypto

```c
/* user_settings.h — TI CC32xx SimpleLink with DTHE hardware crypto */

#define WOLFSSL_TIRTOS

/* Enable TI hardware crypto acceleration */
#define WOLFSSL_TI_CRYPT   /* AES, DES via DTHE */
#define WOLFSSL_TI_HASH    /* MD5, SHA-1, SHA-224, SHA-256 via DTHE */

/* TLS 1.2 with common cipher suites */
#define HAVE_AES_CBC
#define HAVE_AESGCM
#define HAVE_ECC

/* Optional: enable TLS 1.3 */
/* #define WOLFSSL_TLS13 */
/* #define HAVE_HKDF */
/* #define WC_RSA_PSS */
```

### 5.2 Minimal `user_settings.h` — TivaC Software-Only

```c
/* user_settings.h — TivaC TM4C1294 without hardware crypto */

#define WOLFSSL_TIRTOS

/* SP math with 32-bit word size (auto-configured by TIRTOS) */
/* Override max bits if needed */
/* #define SP_INT_MAX_BITS 4096 */

/* TLS features */
#define HAVE_AES_CBC
#define HAVE_AESGCM
#define HAVE_ECC

/* Debug (uncomment to enable error strings) */
/* #define DEBUG_WOLFSSL */
```

### 5.3 CCS Example Project Setup

The wolfssl-examples repository provides a complete TCP Echo with TLS example for the TivaC EK-TM4C1294XL evaluation kit:

1. Install CCS and TI-RTOS for TivaC from the CCS App Center
2. Clone wolfSSL to `C:\ti\wolfssl`
3. Configure `wolfssl/tirtos/products.mak` with your installed component versions
4. Build the wolfSSL library: `gmake.exe -f wolfssl.mak` from `wolfssl/tirtos/`
5. Import the TCP Echo with TLS example from TI Resource Explorer
6. Add wolfSSL include and linker paths to the project properties
7. Build, flash to the EK-TM4C1294XL, and test with `./examples/client/client -h <board_ip> -p 1000`

---

## 6. Additional Resources

### Vendor Documentation (Public)

**TI SimpleLink SDK:**
- CryptoCC32XX Doxygen API Reference: software-dl.ti.com/simplelink/cc32xx — public, no login required
- SimpleLink SDK overview and documentation: software-dl.ti.com — public portal for all TI SDK docs
- TI-RTOS Kernel (SYS/BIOS) User Guide: available through CCS Resource Explorer

**Driver Source (Public):**
- Full driver source available via Zephyr hal_ti mirror on GitHub: github.com/zephyrproject-rtos/hal_ti
- CryptoCC32XX driver headers define the AES, DES, SHA, and HMAC interfaces used by the wolfSSL port

**TI Wiki:**
- wolfSSL with TI-RTOS integration guide: processors.wiki.ti.com/index.php/Using_wolfSSL_with_TI-RTOS (may be archived)

**wolfSSL Resources:**
- TI-RTOS CCS examples: wolfssl-examples repository under `tirtos_ccs_examples/`
- Examples include TCP echo client/server (TivaC TM4C1294NCPDT), wolfCrypt test suite, and benchmarks
- wolfSSL TI-RTOS build system: `wolfssl/tirtos/` directory with XDC makefiles
