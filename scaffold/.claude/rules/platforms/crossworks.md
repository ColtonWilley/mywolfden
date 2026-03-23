---
paths:
  - "**/CrossWorks*/**"
---

# Rowley CrossWorks for ARM — wolfSSL Platform Guide

## 1. Overview

Rowley CrossWorks is a commercial integrated development environment (IDE) from Rowley Associates for ARM, RISC-V, MSP430, and other embedded targets. wolfSSL includes a dedicated platform define `WOLFSSL_ROWLEY_ARM` in `wolfssl/wolfcrypt/settings.h` (line ~161) and ships with pre-built CrossWorks project files in the `IDE/ROWLEY-CROSSWORKS-ARM/` directory.

The CrossWorks toolchain is based on GCC but uses its own project format (`.hzp` solution files, `.hzs` session files), custom startup code, and proprietary linker scripts. wolfSSL's CrossWorks port is configured for single-threaded, no-filesystem embedded operation and includes example projects targeting NXP/Freescale Kinetis K64 Cortex-M4 hardware with optional MMCAU and LTC hardware crypto acceleration.

The `WOLFSSL_ROWLEY_ARM` define shares its settings block in `settings.h` with `WOLFSSL_IAR_ARM`, as both represent bare-metal ARM toolchain targets with similar constraints.

---

## 2. Build Configuration

### Primary Define

Enable CrossWorks ARM support in wolfSSL with:

```c
#define WOLFSSL_ROWLEY_ARM
```

This is listed in `wolfssl/wolfcrypt/settings.h` as a platform selector. It is commented out by default and must be explicitly enabled.

### What the Define Enables

When `WOLFSSL_ROWLEY_ARM` is defined (or `WOLFSSL_IAR_ARM`), `settings.h` applies the following defaults:

```c
#define NO_MAIN_DRIVER       /* No main() in wolfSSL test/benchmark */
#define SINGLE_THREADED      /* No threading support */
#define USE_CERT_BUFFERS_1024  /* Default cert buffers (unless 2048/4096 defined) */
#define BENCH_EMBEDDED       /* Reduced benchmark sizes */
#define NO_FILESYSTEM        /* No file I/O */
#define NO_WRITEV            /* No writev() support */
#define WOLFSSL_USER_IO      /* Custom I/O callbacks required */
```

These are minimal bare-metal defaults. The example `user_settings.h` in the IDE directory overrides and extends many of these.

### How to Enable

**Option A — Define in `user_settings.h` (recommended):**

```c
#define WOLFSSL_USER_SETTINGS
```

Then in your `user_settings.h`:

```c
#define WOLFSSL_ROWLEY_ARM
```

**Option B — Add to CrossWorks Preprocessor Definitions:**

In CrossWorks, go to Project Properties -> Preprocessor Definitions and add:

```
WOLFSSL_ROWLEY_ARM
WOLFSSL_USER_SETTINGS
```

**Option C — Pass via compiler flags:**

```
-DWOLFSSL_ROWLEY_ARM
```

### IDE / Project Files

wolfSSL ships with CrossWorks project files at:

```
IDE/ROWLEY-CROSSWORKS-ARM/
```

This directory contains:

| File | Purpose |
|------|---------|
| `wolfssl.hzp` | Main CrossWorks solution with libwolfssl, benchmark, and test projects |
| `wolfssl_ltc.hzp` | Solution variant with NXP LTC hardware crypto support |
| `user_settings.h` | Example wolfSSL configuration for Kinetis K64 |
| `arm_startup.c` | Startup code (reset handler, section init, heap init) |
| `kinetis_hw.c` | Hardware abstraction for Kinetis K64 (UART, RTC, RNG) |
| `hw.h` | Hardware API interface (must be implemented for other targets) |
| `benchmark_main.c` | Benchmark application entry point |
| `test_main.c` | wolfCrypt test suite entry point |

The solution contains three projects:
1. **libwolfssl** — Builds the wolfSSL static library (`libwolfssl_v7em_t_le_eabi.a`)
2. **benchmark** — Runs `benchmark_test` repeatedly until failure
3. **test** — Runs `wolfcrypt_test` repeatedly until failure

### Prerequisites

Install the following packages via CrossWorks Package Manager (Tools -> Package Manager):
- **Freescale Kinetis CPU Support Package**
- **ARM CPU Support Package**

### Configure System

CrossWorks builds do not use the autoconf `./configure` system. All configuration is done via `user_settings.h` and CrossWorks project properties. Ensure `WOLFSSL_USER_SETTINGS` is defined globally.

---

## 3. Platform-Specific Features

### Threading

The default configuration is `SINGLE_THREADED`. CrossWorks targets are typically bare-metal or run on an RTOS. If using an RTOS alongside CrossWorks:

- For FreeRTOS: add `#define FREERTOS` in `user_settings.h`
- For SafeRTOS: add `#define WOLFSSL_SAFERTOS`
- For ThreadX: add `#define THREADX`

Remove `#define SINGLE_THREADED` when using an RTOS.

### Networking

The default configuration defines `WOLFSSL_USER_IO`, meaning no built-in socket layer. You must implement custom I/O callbacks:

```c
wolfSSL_CTX_SetIORecv(ctx, my_recv_cb);
wolfSSL_CTX_SetIOSend(ctx, my_send_cb);
```

Alternatively, define `WOLFSSL_NO_SOCK` (as the example `user_settings.h` does) to explicitly disable socket support.

### Hardware Cryptography

The CrossWorks port includes support for NXP/Freescale hardware crypto:

| Feature | Define | Notes |
|---------|--------|-------|
| NXP MMCAU | `USE_NXP_MMCAU` -> `FREESCALE_USE_MMCAU` | Software-triggered crypto accelerator |
| NXP LTC | `USE_NXP_LTC` -> `FREESCALE_USE_LTC` | Low-power crypto accelerator with ECC support (up to 384-bit) |

**To enable MMCAU:**
1. Download the MMCAU library from NXP
2. Copy `lib_mmcau.a` and `cau_api.h` into the project
3. Define `USE_NXP_MMCAU` in `user_settings.h`
4. Add `lib_mmcau.a` to Source Files in the application project
5. Open `wolfssl_ltc.hzp` and build

**To enable LTC:**
1. Download NXP KSDK 2.0
2. Copy required driver and CMSIS folders into `IDE/ROWLEY-CROSSWORKS-ARM/`
3. Define `USE_NXP_LTC` in `user_settings.h`
4. Open `wolfssl_ltc.hzp` and build

When using LTC for ECC, `ECC_SHAMIR` is automatically disabled (Shamir trick is not compatible with hardware ECC), and `LTC_MAX_ECC_BITS` defaults to 384.

### Math Configuration

The example configuration uses fast math with ARM-specific optimizations:

```c
#define USE_FAST_MATH
#define TFM_TIMING_RESISTANT
#define TFM_ARM              /* ARM-specific assembly optimizations */
```

Single Precision (SP) math is also supported as an alternative:

```c
#define WOLFSSL_SP
#define WOLFSSL_SP_SMALL
#define WOLFSSL_SP_ARM_CORTEX_M_ASM  /* Cortex-M assembly optimizations */
```

### Required Application Functions

When writing a custom application (not using the provided benchmark/test mains), you must implement:

- `double current_time(int reset)` — Returns time as seconds.milliseconds
- `int custom_rand_generate(void)` — Returns a 32-bit random number from hardware RNG

---

## 4. Common Issues

### Porting to Non-Kinetis Hardware

The shipped project files target NXP/Freescale Kinetis K64 (`MK64FN1M0xxx12`). For other ARM targets:

1. Implement the functions declared in `hw.h` (UART, RTC, RNG)
2. Configure ARM Architecture and ARM Core Type in Solution Properties -> ARM
3. Set the Target Processor in each project's Project Properties
4. Provide appropriate startup code (replace `arm_startup.c` and `kinetis_hw.c`)

### Stack Size

Cortex-M targets have limited stack. With the default `user_settings.h`:
- RSA uses `FP_MAX_BITS = 4096` (supports RSA-2048)
- Fast math (`USE_FAST_MATH`) uses stack-allocated buffers
- Enable `WOLFSSL_SMALL_STACK` if stack overflows occur — this moves large buffers to heap

Recommended minimum stack: **8-12 KB** for TLS operations.

### No Filesystem

The default configuration defines `NO_FILESYSTEM`. Load certificates and keys from C arrays:

```c
#define USE_CERT_BUFFERS_2048    /* or USE_CERT_BUFFERS_256 for ECC */

wolfSSL_CTX_load_verify_buffer(ctx, ca_cert, sizeof(ca_cert), SSL_FILETYPE_ASN1);
wolfSSL_CTX_use_certificate_buffer(ctx, dev_cert, sizeof(dev_cert), SSL_FILETYPE_ASN1);
wolfSSL_CTX_use_PrivateKey_buffer(ctx, dev_key, sizeof(dev_key), SSL_FILETYPE_ASN1);
```

### Entropy / Random Number Generation

The example configuration requires a custom RNG implementation:

```c
#define CUSTOM_RAND_TYPE      unsigned int
#define CUSTOM_RAND_GENERATE  custom_rand_generate
#define NO_DEV_RANDOM
```

If your hardware has a true RNG peripheral, use it. The Kinetis K64 has an RNGA peripheral which the example `kinetis_hw.c` wraps.

### Debug Output

The example `user_settings.h` redefines `fprintf` to `printf` when `DEBUG_WOLFSSL` is enabled, since CrossWorks debug output typically goes through semihosting or a UART-backed `printf`:

```c
#ifdef DEBUG_WOLFSSL
    #define fprintf(file, format, ...)   printf(format, ##__VA_ARGS__)
#endif
```

---

## 5. Example Configuration

The following is a minimal `user_settings.h` for CrossWorks ARM. For a full-featured example, see `IDE/ROWLEY-CROSSWORKS-ARM/user_settings.h`.

```c
/* user_settings.h — Minimal wolfSSL for Rowley CrossWorks ARM */

#ifndef WOLFSSL_USER_SETTINGS_H
#define WOLFSSL_USER_SETTINGS_H

/* ---- Platform ---- */
#define WOLFSSL_ROWLEY_ARM
#define WOLFSSL_GENERAL_ALIGNMENT   4
#define SINGLE_THREADED
#define WOLFSSL_NO_SOCK

/* ---- Core TLS ---- */
#define WOLFSSL_TLS13
#define NO_OLD_TLS

/* ---- Math ---- */
#define USE_FAST_MATH
#define TFM_TIMING_RESISTANT
#define TFM_ARM                  /* ARM assembly optimizations */

/* ---- Filesystem ---- */
#define NO_FILESYSTEM
#define NO_WRITEV
#define NO_MAIN_DRIVER
#define NO_DEV_RANDOM

/* ---- Cipher suite tuning ---- */
#define HAVE_ECC
#define ECC_TIMING_RESISTANT
#define HAVE_AESGCM
#define HAVE_CHACHA
#define HAVE_POLY1305
#define NO_DES3
#define NO_RC4
#define NO_MD4
#define NO_DSA

/* ---- Security hardening ---- */
#define WC_RSA_BLINDING

/* ---- Networking ---- */
#define WOLFSSL_USER_IO

/* ---- Entropy ---- */
#define CUSTOM_RAND_TYPE      unsigned int
extern unsigned int custom_rand_generate(void);
#define CUSTOM_RAND_GENERATE  custom_rand_generate

/* ---- Time ---- */
#define WOLFSSL_USER_CURRTIME
#define USER_TICKS
extern unsigned long ksdk_time(unsigned long* timer);
#define XTIME ksdk_time

/* ---- Benchmark / Test ---- */
#define BENCH_EMBEDDED
#define USE_CERT_BUFFERS_2048
#define USE_CERT_BUFFERS_256

#endif /* WOLFSSL_USER_SETTINGS_H */
```

Build with `WOLFSSL_USER_SETTINGS` defined as a global compiler flag in CrossWorks Preprocessor Definitions or via:
```
-DWOLFSSL_USER_SETTINGS
```

---

## 6. Related Resources

- **CrossWorks Reference Manual PDF (v5.3.0):** https://cdn.rowleydownload.co.uk/arm/documentation/arm_crossworks_reference_manual.pdf
- **CrossWorks HTML Documentation Index:** https://rowleydownload.co.uk/arm/documentation/index.htm
- **Rowley Official Documentation Page:** https://rowley.co.uk/crossworks/Documentation.htm
- **wolfSSL CrossWorks IDE project files:** `IDE/ROWLEY-CROSSWORKS-ARM/` in the wolfSSL source tree
- **wolfSSL Manual:** https://www.wolfssl.com/documentation/manuals/wolfssl/
- **Rowley Associates:** https://www.rowley.co.uk/
