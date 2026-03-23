---
paths:
  - "**/micrium*"
  - "**/Micrium*"
  - "**/ucos*"
---

# Micrium uC/OS-III — wolfSSL Platform Guide

## 1. Overview

Micrium uC/OS-III (now part of Silicon Labs) is a preemptive real-time operating system for embedded systems. wolfSSL provides first-class support through the `MICRIUM` preprocessor define, which activates comprehensive platform adaptations across threading, networking, time, string handling, memory operations, and I/O.

When `MICRIUM` is defined, wolfSSL automatically maps mutex operations to OS_MUTEX, time to the uC-Clk module (`Clk_GetTS_Unix()`), string/memory functions to Micrium's `Str_*`/`Mem_*` APIs, I/O to uC/TCP-IP NetSock callbacks, and RNG to `Math_Rand`. It also detects endianness from `CPU_CFG_ENDIAN_TYPE` and enables side-channel protections (`TFM_TIMING_RESISTANT`, `ECC_TIMING_RESISTANT`, `WC_RSA_BLINDING`).

The reference platform is an Eclipse-based IDE project at `IDE/ECLIPSE/MICRIUM/` with `user_settings.h`, TLS client/server examples, and the `wolfsslRunTests.c` test runner.

**Supported versions:** Both legacy uC/OS-III (OS_VERSION < 50000) and Micrium OS 5.x (RTOS_MODULE_NET_AVAIL) with version-specific error handling.

---

## 2. Build Configuration

### Primary Define

```c
#define MICRIUM
```

This is listed in `wolfssl/wolfcrypt/settings.h` (line 76, commented out by default). The recommended approach is to define it in `user_settings.h` and compile with `WOLFSSL_USER_SETTINGS`.

### Reference user_settings.h

The tested configuration at `IDE/ECLIPSE/MICRIUM/user_settings.h`:

```c
#define MICRIUM
#define NO_FILESYSTEM
#define NO_MAIN_DRIVER
#define NO_TESTSUITE_MAIN_DRIVER
#define NO_WRITE_TEMP_FILES
#define SIZEOF_LONG_LONG 8
#define USE_CERT_BUFFERS_2048
#define BENCH_EMBEDDED
#define HAVE_AESGCM
#define WOLFSSL_SHA512
#define HAVE_ECC
#define HAVE_CURVE25519
#define CURVE25519_SMALL
#define HAVE_ED25519
#define ED25519_SMALL
#define XSNPRINTF snprintf
```

### Defines Auto-Enabled by MICRIUM

When `MICRIUM` is defined in `settings.h`, the following are set automatically (do not redefine):

- **Side-channel hardening:** `TFM_TIMING_RESISTANT`, `ECC_TIMING_RESISTANT`, `WC_RSA_BLINDING`, `HAVE_HASHDRBG`
- **ECC support:** `HAVE_ECC`, `ALT_ECC_SIZE`, `TFM_ECC192/224/256/384/521`
- **TLS features:** `HAVE_TLS_EXTENSIONS`, `HAVE_SUPPORTED_CURVES`, `HAVE_EXTENDED_MASTER`, `NO_RC4`
- **Platform adapters:** `NO_WOLFSSL_DIR`, `NO_WRITEV`, `STRING_USER`
- **RNG:** `CUSTOM_RAND_TYPE RAND_NBR`, `CUSTOM_RAND_GENERATE Math_Rand` (unless hardware RNG defined)

### Compiler Setup

1. Add `WOLFSSL_USER_SETTINGS` to your preprocessor defines
2. Add these include paths:
   - wolfSSL root directory
   - `wolfssl/wolfcrypt/` directory
   - `IDE/ECLIPSE/MICRIUM/` directory (for `user_settings.h`)
3. Exclude assembly files from the build: `aes_asm.asm`, `aes_gcm_asm.asm`, `aes_xts_asm.asm`, `aes_asm.s`

### Clock Configuration (Critical)

The uC-Clk module is **mandatory**. wolfSSL maps `XTIME()` to `micrium_time()`, which calls `Clk_GetTS_Unix()` from `<clk.h>`. Without it, certificate date validation fails. The clock must be initialized before any TLS operations:

```c
CLK_ERR err;
Clk_Init(&err);
Clk_SetTS_Unix(CURRENT_UNIX_TS);  /* seconds since Jan 1 1970 UTC */
```

The `CURRENT_UNIX_TS` value in `user_settings.h` must be a recent timestamp. An outdated value causes certificate validation failures (`notBefore`/`notAfter` checks).

---

## 3. Platform-Specific Features

### Threading and Mutex

wolfSSL maps `wolfSSL_Mutex` to `OS_MUTEX` using `OSMutexCreate`, `OSMutexPend` (blocking), `OSMutexPost`, and `OSMutexDel` (requires `OS_CFG_MUTEX_DEL_EN`). If `OS_CFG_MUTEX_EN == DEF_DISABLED`, wolfSSL automatically defines `SINGLE_THREADED`.

### Network I/O (uC/TCP-IP Integration)

wolfSSL provides built-in I/O callbacks for the Micrium uC/TCP-IP NetSock API, automatically registered when `MICRIUM` is defined (`USE_WOLFSSL_IO` is not set):

- **`MicriumSend()`** / **`MicriumReceive()`** — TCP via `NetSock_TxData()` / `NetSock_RxData()`
- **`MicriumSendTo()`** / **`MicriumReceiveFrom()`** — UDP/DTLS support
- **`MicriumGenerateCookie()`** — DTLS cookie generation using peer address hash

DTLS timeout handling uses `NetSock_CfgTimeoutRxQ_Set()`. **Not yet supported:** `WOLFSSL_SESSION_EXPORT`, `HAVE_CRL`, `HAVE_OCSP` (each needs custom callback implementation).

### String, Memory, and Filesystem

All standard C string/memory functions are remapped to Micrium's `Str_*` and `Mem_*` libraries (e.g., `XSTRLEN` -> `Str_Len`, `XMEMCPY` -> `Mem_Copy`). `XMEMCMP` uses `Mem_Cmp` with a version-specific workaround for OS 5.x (see Common Issues).

When the Micrium FS module is available, wolfSSL maps file operations to the `fs_*` API. Most embedded projects define `NO_FILESYSTEM` and use certificate buffers instead.

Defining `MICRIUM_MALLOC` enables Micrium-specific memory allocation, bypassing the default wolfSSL memory system. For constrained environments, consider `WOLFSSL_STATIC_MEMORY`.

---

## 4. Common Issues

### Certificate Validation Failures ("ASN date error")

**Cause:** `CURRENT_UNIX_TS` in `user_settings.h` is stale, or `Clk_Init()` was not called before wolfSSL operations.
**Fix:** Update `CURRENT_UNIX_TS` to a current Unix timestamp and ensure `Clk_Init()` + `Clk_SetTS_Unix()` are called at startup before any wolfSSL API calls.

### XMEMCMP Behavior Change in Micrium OS 5.x

**Cause:** Micrium OS 5.8 changed `Mem_Cmp` to return `DEF_NO` for zero-size comparisons, breaking cryptographic verifications.
**Fix:** Use a current wolfSSL version that includes the `OS_VERSION >= 50000` workaround in the `XMEMCMP` macro in `settings.h`.

### Mutex BAD_MUTEX_E Errors

**Cause:** `OS_CFG_MUTEX_EN` is disabled in uC/OS-III config but wolfSSL expects multi-threaded mode.
**Fix:** Enable `OS_CFG_MUTEX_EN` in `os_cfg.h`, or define `SINGLE_THREADED` in `user_settings.h`.

### Linker Errors for Clk_Init / Clk_GetTS_Unix

**Cause:** The uC-Clk module was not added to the IDE project (it is separate from the uC/OS-III kernel).
**Fix:** Add the Micrium uC-Clk source files to your project.

### Stack/Heap Overflow

**Fix:** The reference uses 16 KB stack and 20 KB heap. RSA-2048 needs at least 16 KB stack. Use `WOLFSSL_SMALL_STACK` to move large buffers to the heap.

---

## 5. Example Configuration

### Verified Reference Platform

Tested at `IDE/ECLIPSE/MICRIUM/` on NXP Kinetis K70 (TWR-K70F120M), uC/OS-III + uC/TCP-IP + uC-Clk, IAR EWARM 8.32.1, 1 MB flash / 128 KB SRAM (16 KB stack, 20 KB heap).

### Benchmark Results (NXP K70, ARM Cortex-M4, 120 MHz)

Software-only, `BENCH_EMBEDDED` (1 KB blocks):

| Algorithm | Performance |
|---|---|
| AES-128-CBC enc/dec | ~226 / ~224 KB/s |
| AES-256-CBC enc | ~194 KB/s |
| AES-128-GCM enc | ~102 KB/s |
| SHA-256 / SHA-512 | ~554 / ~199 KB/s |
| RSA-2048 pub / priv | 128 ms / 2486 ms per op |
| ECC-256 keygen | 395 ms/op |
| ECDSA-256 sign / verify | 403 ms / 793 ms per op |
| Curve25519 keygen | 631 ms/op |

Hardware crypto acceleration (if available on the target SoC) will substantially improve these numbers.

### Startup Integration

```c
#include <wolfssl/ssl.h>

static void App_TaskStart(void *p_arg)
{
    OS_ERR os_err;
    CLK_ERR clk_err;

    /* Initialize the Micrium clock module (required by wolfSSL) */
    Clk_Init(&clk_err);
    Clk_SetTS_Unix(CURRENT_UNIX_TS);

    /* Initialize wolfSSL */
    wolfSSL_Init();

    /* Application TLS code here... */

    while (DEF_TRUE) {
        OSTimeDlyHMSM(0u, 5u, 0u, 0u, OS_OPT_TIME_HMSM_STRICT, &os_err);
    }
}
```

### Test Selection Defines

The reference `wolfsslRunTests.c` supports four test modes via defines in `user_settings.h`: `WOLFSSL_WOLFCRYPT_TEST`, `WOLFSSL_BENCHMARK_TEST`, `WOLFSSL_CLIENT_TEST`, `WOLFSSL_SERVER_TEST`. For TLS client tests, set `TCP_SERVER_IP_ADDR` and `TCP_SERVER_PORT` in `client_wolfssl.c`. For TLS server tests, set `TLS_SERVER_PORT` in `server_wolfssl.c`. The default cipher suite is `TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256` on TLS 1.2.
