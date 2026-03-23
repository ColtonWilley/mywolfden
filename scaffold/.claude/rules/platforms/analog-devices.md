---
paths:
  - "**/analog*devices*"
  - "**/ADUCM*"
  - "**/ADuCM*"
---

# Analog Devices Blackfin / SHARC DSP — wolfSSL Platform Guide

## 1. Overview

Analog Devices produces the Blackfin and SHARC families of digital signal processors (DSPs), commonly used in audio, industrial control, and defense applications. wolfSSL has direct Blackfin port support through an IDE project located at `IDE/VisualDSP/`, which provides a `user_settings.h` and task integration code for the Fusion RTOS (FCL) environment. This port was developed for FIPS 140-2 validation on the Blackfin platform.

There is no dedicated `settings.h` platform define (such as `WOLFSSL_BLACKFIN`) in the wolfSSL source — instead, the Blackfin build is configured entirely through `user_settings.h` with the `BLACKFIN_BUILD` define and Fusion RTOS (`FUSION_RTOS`) integration. There is no dedicated port directory under `wolfssl/wolfcrypt/port/` for Analog Devices hardware.

wolfSSL also provides a separate DSP offload capability (`WOLFSSL_DSP`) for Qualcomm Hexagon DSPs (`IDE/HEXAGON/`), which is architecturally distinct from the Analog Devices Blackfin/SHARC port. The Hexagon DSP support offloads ECC-256 verify operations to the aDSP via remote procedure calls — this is not applicable to Analog Devices DSPs.

For SHARC processors, no dedicated wolfSSL port exists. Integration would follow the same generic embedded path as Blackfin: a custom `user_settings.h` with appropriate defines for the target's memory model, alignment, and toolchain.

---

## 2. Build Configuration

### Key Defines

The Blackfin `user_settings.h` at `IDE/VisualDSP/user_settings.h` uses the following platform defines:

| Define | Purpose |
|---|---|
| `BLACKFIN_BUILD` | Master platform flag; gates Blackfin-specific code blocks |
| `WOLFSSL_GENERAL_ALIGNMENT 4` | 4-byte alignment for data structures (critical on DSP architectures) |
| `SINGLE_THREADED` | Disables multi-threading (Fusion RTOS tasks are managed externally) |
| `NO_WRITEV` | Disables `writev()` (not available on bare-metal/RTOS) |
| `NO_MAIN_DRIVER` | Disables standard `main()` test driver |
| `NO_ATTRIBUTE_CONSTRUCTOR` | **Required on ADSP Blackfin** — memory is zeroed after `__attribute__((constructor))` runs but before `main()`, breaking FIPS self-test initialization |
| `WOLFSSL_HAVE_MIN` / `WOLFSSL_HAVE_MAX` | Prevents wolfSSL from defining `min`/`max` macros (conflict with `<builtins.h>`) |
| `BENCH_EMBEDDED` | Uses reduced benchmark/test sizes suitable for constrained memory |
| `USE_FAST_MATH` | Enables fast math library with timing-resistant operations |
| `TFM_TIMING_RESISTANT` | Enables timing-resistant TFM operations (required for FIPS) |

### FIPS Configuration

The VisualDSP project was configured for FIPS 140-2 Level 2 validation:

- `HAVE_FIPS` with `HAVE_FIPS_VERSION 2`
- `NO_THREAD_LS` is set when `SINGLE_THREADED` is active (no thread-local storage)
- `NO_ATTRIBUTE_CONSTRUCTOR` is mandatory — the Blackfin runtime zeroes BSS after constructors run, which would corrupt the FIPS in-core integrity hash

### Memory Overrides

The Blackfin port uses Fusion RTOS (FCL) memory and string functions:

```c
#define XMALLOC(a, b, c)  fclMalloc(a)
#define XFREE(a, b, c)    fclFree(a)
#define XREALLOC(a, b, c, d) fclRealloc(a, b)
```

Standard string functions (`XMEMCPY`, `XSTRLEN`, etc.) are similarly mapped to `FCL_MEMCPY`, `FCL_STRLEN`, etc. via the `STRING_USER` define. Time functions use `fclTime()` and `fclCtime()`.

### Configure Flags

No autoconf `./configure` flags exist for this platform. Configuration is done entirely through `user_settings.h` defines and the VisualDSP (or CrossCore Embedded Studio) IDE project.

### IDE Integration

The VisualDSP project requires the following Fusion RTOS headers:

```c
#include "fusioncfg.h"    /* Platform configuration */
#include <builtins.h>      /* ADSP built-in functions */
#include <fclstdlib.h>     /* FCL stdlib replacements */
#include <fclstring.h>     /* FCL string replacements */
#include <fcltime.h>       /* FCL time functions */
#include <fss_telnet_shell.h>  /* Shell integration for test tasks */
```

For CrossCore Embedded Studio (CCES), you would adapt the VisualDSP project settings and `user_settings.h` to the CCES build system.

---

## 3. Platform-Specific Features

### Fusion RTOS Task Integration

The file `IDE/VisualDSP/wolf_tasks.c` provides integration with the Fusion RTOS task scheduler:

- `wolfcrypt_test_taskEnter()` — runs wolfCrypt test suite as a Fusion task
- `wolfcrypt_harness_taskEnter()` — runs FIPS harness as a Fusion task
- `wolf_task_start()` / `wolf_task_results()` — shell commands for starting tests and retrieving results
- `wolfFIPS_Module_start()` — initializes the FIPS module with a callback via `wolfCrypt_SetCb_fips()`
- Task stack size defaults to 100 KB (`WOLF_TASK_STACK_SIZE = 1024 * 100`)

### FIPS In-Core Integrity

The FIPS callback (`myFipsCb`) handles `IN_CORE_FIPS_E` errors by printing the expected hash value. On Blackfin, `NO_ATTRIBUTE_CONSTRUCTOR` ensures the integrity hash check is triggered manually rather than via constructor attributes, because the Blackfin runtime zeroes memory between constructor execution and `main()`.

### OpenSSL Compatibility Layer

The Blackfin `user_settings.h` enables `OPENSSL_EXTRA` and `OPENSSL_ALL` for compatibility with applications expecting OpenSSL APIs, along with `WOLFSSL_EVP_DECRYPT_LEGACY` for legacy EVP behavior.

### TLS 1.3 Support

The Blackfin configuration includes TLS 1.3 support (`WOLFSSL_TLS13`) with `HAVE_TLS_EXTENSIONS`, `HAVE_SUPPORTED_CURVES`, and `HAVE_FFDHE_4096`.

### No Hardware Crypto Offload

Unlike some embedded platforms (NXP CAAM, Nordic CryptoCell), there is no wolfSSL port for Analog Devices hardware crypto accelerators. All cryptographic operations run in software on the DSP core.

---

## 4. Common Issues

### `NO_ATTRIBUTE_CONSTRUCTOR` Is Mandatory

On ADSP Blackfin with Fusion RTOS, the runtime zeroes BSS memory after `__attribute__((constructor))` functions execute but before `main()` is called. This breaks FIPS self-test initialization. `NO_ATTRIBUTE_CONSTRUCTOR` must be defined to defer initialization to an explicit function call.

### Memory Alignment

DSP architectures often have strict alignment requirements. The `WOLFSSL_GENERAL_ALIGNMENT 4` setting ensures wolfSSL data structures are 4-byte aligned. If your specific Blackfin or SHARC variant requires different alignment (e.g., 8-byte for certain DMA operations), override this value.

### Endianness

Blackfin processors are little-endian. SHARC processors can be configured for either endianness depending on the variant. Verify that wolfSSL's endianness detection is correct for your target, or explicitly define `LITTLE_ENDIAN_ORDER` or `BIG_ENDIAN_ORDER` in `user_settings.h`.

### Stack Size

DSP platforms may have limited stack space. The default test task stack of 100 KB may need adjustment. For production use, `WOLFSSL_SMALL_STACK` can be enabled to reduce stack usage at the cost of additional heap allocations.

### Standard Library Replacements

The port overrides all standard library functions (`STRING_USER`, `XMALLOC_OVERRIDE`). If you are not using Fusion RTOS, you must provide your own replacements or remove these overrides and use the toolchain's standard library.

### No `/dev/random`

Although `NO_DEV_RANDOM` is not set by default in the VisualDSP `user_settings.h`, bare-metal and RTOS environments will not have `/dev/random`. Provide a hardware RNG seed source via `CUSTOM_RAND_GENERATE` or `CUSTOM_RAND_GENERATE_BLOCK`, or use the Hash-DRBG (`HAVE_HASHDRBG`) with a hardware seed.

### SHARC Floating-Point Considerations

SHARC processors are optimized for floating-point DSP operations. wolfSSL uses integer math exclusively for cryptographic operations, so SHARC floating-point hardware provides no acceleration. Ensure your build is not inadvertently using floating-point paths for integer operations, which could cause correctness issues.

---

## 5. Example Configuration

### Minimal `user_settings.h` — Blackfin (Non-FIPS)

```c
/* user_settings.h — wolfSSL for Analog Devices Blackfin DSP */

#ifndef WOLFSSL_USER_SETTINGS_H
#define WOLFSSL_USER_SETTINGS_H

/* Platform identification */
#define BLACKFIN_BUILD

/* Alignment — adjust for your specific DSP variant */
#define WOLFSSL_GENERAL_ALIGNMENT   4

/* Threading */
#define SINGLE_THREADED

/* Required on ADSP Blackfin — BSS zeroed after constructors */
#define NO_ATTRIBUTE_CONSTRUCTOR

/* Disable unavailable OS features */
#define NO_WRITEV
#define NO_MAIN_DRIVER
#define NO_DEV_RANDOM

/* Prevent min/max macro conflicts with <builtins.h> */
#define WOLFSSL_HAVE_MIN
#define WOLFSSL_HAVE_MAX

/* Math library */
#define USE_FAST_MATH
#define TFM_TIMING_RESISTANT
#define FP_MAX_BITS     4096

/* Memory — replace with your RTOS or bare-metal allocator */
#define XMALLOC_OVERRIDE
/* #define XMALLOC(n, h, t)  my_malloc(n) */
/* #define XFREE(p, h, t)    my_free(p)   */
/* #define XREALLOC(p, n, h, t) my_realloc(p, n) */

/* RNG — provide a hardware seed source */
#define HAVE_HASHDRBG
/* extern int my_rng_seed(unsigned char* output, unsigned int sz); */
/* #define CUSTOM_RAND_GENERATE_BLOCK  my_rng_seed */

/* Reduce memory footprint */
#define BENCH_EMBEDDED
#define WOLFSSL_SMALL_STACK

/* Algorithms */
#define HAVE_AES_CBC
#define HAVE_AESGCM
#define GCM_SMALL
#define WOLFSSL_SHA256
#define WOLFSSL_SHA384
#define WOLFSSL_SHA512
#define HAVE_ECC
#define ECC_TIMING_RESISTANT

/* Disable unused algorithms */
#define NO_RC4
#define NO_MD4
#define NO_PSK
#define NO_DES3

#endif /* WOLFSSL_USER_SETTINGS_H */
```

### Minimal `user_settings.h` — SHARC (Generic Embedded)

For SHARC, no `BLACKFIN_BUILD` define is used. Follow the generic embedded porting guide and adjust:

```c
/* user_settings.h — wolfSSL for Analog Devices SHARC DSP */

#ifndef WOLFSSL_USER_SETTINGS_H
#define WOLFSSL_USER_SETTINGS_H

/* Alignment — SHARC may require 4 or 8 byte alignment */
#define WOLFSSL_GENERAL_ALIGNMENT   4

#define SINGLE_THREADED
#define NO_WRITEV
#define NO_MAIN_DRIVER
#define NO_DEV_RANDOM
#define NO_FILESYSTEM
#define WOLFSSL_USER_IO

/* Required if SHARC runtime has same constructor issue as Blackfin */
/* #define NO_ATTRIBUTE_CONSTRUCTOR */

/* Math */
#define USE_FAST_MATH
#define TFM_TIMING_RESISTANT

/* Memory and string overrides — map to your RTOS/BSP functions */
#define XMALLOC_OVERRIDE
#define STRING_USER

/* Minimal cipher suite */
#define HAVE_AES_CBC
#define WOLFSSL_SHA256
#define NO_RC4
#define NO_MD4
#define NO_DES3

/* Reduce footprint */
#define WOLFSSL_SMALL_STACK
#define BENCH_EMBEDDED

#endif /* WOLFSSL_USER_SETTINGS_H */
```

---

## 6. Additional Resources

### Vendor Documentation (Public — No Login Required)

- **Blackfin Compiler & Library Manual** (PDF): analog.com/media/en/dsp-documentation/software-manuals/cces2-2-0_BlackfinCompilerAndLib_mn_rev1-6.pdf
- **SHARC Compiler Manual** (PDF): analog.com/media/en/dsp-documentation/software-manuals/cces2-2-0_SharcCompiler_mn_rev1-5.pdf
- **All Blackfin Manuals Index**: analog.com/en/lp/001/blackfin-manuals.html
- **CrossCore Embedded Studio (CCES) Product Page**: analog.com/en/resources/evaluation-hardware-and-software/software/adswt-cces.html
- **CCES Getting Started Guide (EngineerZone)**: ez.analog.com/dsp/software-and-development-tools/cces/w/documents/5330/crosscore-embedded-studio-getting-started

> **Note:** CrossCore Embedded Studio requires a license for use, but all documentation listed above is publicly accessible without registration.

### wolfSSL Source References

- **VisualDSP IDE project**: `IDE/VisualDSP/` — contains `user_settings.h` (Blackfin + FIPS configuration) and `wolf_tasks.c` (Fusion RTOS task integration)
- **Hexagon DSP project** (Qualcomm, not Analog Devices): `IDE/HEXAGON/` — separate DSP offload architecture for ECC-256 verify; not applicable to Blackfin/SHARC
- **DSP offload source**: `wolfcrypt/src/wc_dsp.c` — implements `WOLFSSL_DSP` remote handle management for Qualcomm Hexagon; reference only for understanding wolfSSL's DSP architecture
- **wolfSSL Porting Guide**: wolfssl.com/documentation/manuals/wolfssl/ — chapters on building wolfSSL and porting to embedded systems
