---
paths:
  - "**/IDE/IAR*/**"
  - "**/IDE/MDK*/**"
  - "**/IDE/Keil*/**"
  - "**/*.ewp"
---

# IAR + Keil IDEs — wolfSSL Platform Guide

## 1. Overview

wolfSSL provides support for embedded development using two popular commercial IDEs:

- **IAR Embedded Workbench for ARM (IAR EWARM)** — identified at compile time by the `__IAR_SYSTEMS_ICC__` preprocessor macro
- **Keil MDK-ARM** — supported through project files located in the `IDE/MDK-ARM/` directory tree

Both IDEs target ARM-based microcontrollers and are commonly used in professional embedded and IoT development. wolfSSL ships with pre-configured IDE project files for both environments, reducing the effort required to integrate TLS/cryptography into an existing embedded project.

---

## 2. Build Configuration

### IAR EWARM

**Key Compiler Macro:** `__IAR_SYSTEMS_ICC__`

This macro is automatically defined by the IAR compiler. wolfSSL's `settings.h` detects it and applies a diagnostic suppression pragma:

```c
#ifdef __IAR_SYSTEMS_ICC__
    #pragma diag_suppress=Pa089
#endif
```

This suppresses a specific IAR compiler warning (Pa089) that is not relevant to wolfSSL's code and would otherwise produce noise during builds.

**Project Files Location:**
```
IDE/IAR-EWARM/
├── .gitignore
├── Projects/
├── README
└── embOS/
```

The `Projects/` subdirectory contains IAR workspace and project files (`.eww`, `.ewp`). The `embOS/` subdirectory suggests support for SEGGER embOS RTOS integration within the IAR environment.

**Configure Flags:** No special `./configure` flags are required or documented for IAR. IAR builds are typically driven entirely through the IDE project files rather than the autoconf/configure build system.

### Keil MDK-ARM

**Project Files Location:**
```
IDE/MDK-ARM/
├── LPC43xx/
├── MDK-ARM/
├── Projects/
└── STM32F2xx_StdPeriph_Lib/
```

Pre-configured project files are provided for:
- **NXP LPC43xx** series microcontrollers
- **STMicroelectronics STM32F2xx** using the Standard Peripheral Library

These cover common ARM Cortex-M targets used in embedded TLS deployments.

### Recommended Defines (Both IDEs)

Based on the wolfSSL source material, the following defines are associated with the IAR/embedded TLS configuration context:

```c
#define HAVE_ECC
#define HAVE_ALPN
#define USE_WOLF_STRTOK        /* required when HAVE_ALPN is set */
#define HAVE_TLS_EXTENSIONS
#define HAVE_SUPPORTED_CURVES
#define HAVE_AESGCM
```

These are not IAR-specific requirements but represent a typical feature set for embedded TLS use cases targeted by these IDEs.

---

## 3. Platform-Specific Features

### Diagnostic Suppression (IAR)

The IAR compiler issues warning **Pa089** ("non-standard extension used") for certain constructs in wolfSSL. This is automatically suppressed via:

```c
#pragma diag_suppress=Pa089
```

This pragma is conditionally applied only when `__IAR_SYSTEMS_ICC__` is defined, so it does not affect other toolchains.

For non-IAR, non-GCC compilers (e.g., some Keil ARMCC versions), a different suppression is applied:

```c
#elif !defined(__GNUC__)
    #pragma diag_suppress=11
#endif
```

This suggests Keil ARMCC may also benefit from diagnostic suppression, handled automatically by wolfSSL's headers.

### RTOS Support

The presence of an `embOS/` subdirectory under `IDE/IAR-EWARM/` indicates that wolfSSL supports SEGGER embOS when building with IAR. For complete embOS integration guidance including threading, memory, and I/O configuration, see `platforms/embos.md`. For embOS RTOS architecture and API reference, see `integrations/embos.md`.

### Time / RTC

The source material notes a pattern relevant to embedded targets:

```c
/* Uncomment this setting if your toolchain does not offer time.h header */
/* #define USER_TIME */
```

If the IAR or Keil runtime library does not provide a functional `time.h` / `time()` implementation (common on bare-metal targets), define `USER_TIME` and provide your own `time()` function returning the current Unix timestamp.

### Hardware Crypto, Networking

The source material does not document specific hardware crypto acceleration or networking stack integration for IAR or Keil targets beyond what is shown above. Refer to the wolfSSL manual and the platform-specific README files within the IDE project directories for details on:

- Hardware RNG integration
- Hardware AES acceleration (e.g., STM32 crypto peripheral)
- TCP/IP stack integration (LwIP, etc.)

---

## 4. Common Issues

### Warning Pa089 (IAR)

**Issue:** IAR compiler emits Pa089 warnings during wolfSSL compilation.  
**Resolution:** This is handled automatically by wolfSSL's `settings.h` when `__IAR_SYSTEMS_ICC__` is detected. No user action is required.

### Missing `time()` Implementation

**Issue:** Bare-metal IAR or Keil targets may not have a working `time()` function, causing TLS certificate validation failures or build errors.  
**Resolution:** Define `USER_TIME` in your `user_settings.h` and implement a custom `time()` that returns the current epoch time from your RTC or network time source.

### Stack Size

**Issue:** wolfSSL's TLS handshake and cryptographic operations require significant stack space. Default stack sizes in IAR/Keil projects are often too small.  
**Resolution:** The source material does not specify an exact minimum, but embedded wolfSSL deployments commonly require **4–8 KB of stack** for TLS operations. Consult the wolfSSL manual for current recommendations and adjust your linker/startup configuration accordingly.

### `USE_WOLF_STRTOK`

**Issue:** Some embedded C runtimes (including those bundled with IAR or Keil) may have a non-reentrant or missing `strtok()`.  
**Resolution:** When `HAVE_ALPN` is enabled, define `USE_WOLF_STRTOK` to use wolfSSL's internal implementation instead of the platform's.

### Keil ARMCC Diagnostic Warning 11

**Issue:** Keil ARMCC may emit warning 11 for wolfSSL code.  
**Resolution:** wolfSSL's `settings.h` suppresses this automatically for non-GCC, non-IAR compilers via `#pragma diag_suppress=11`.

---

## 5. Example Configuration

The following is a minimal `user_settings.h` suitable as a starting point for IAR EWARM or Keil MDK-ARM projects. Adjust feature flags to match your application's requirements and available memory.

```c
/* user_settings.h — wolfSSL for IAR EWARM / Keil MDK-ARM */

#ifndef WOLFSSL_USER_SETTINGS_H
#define WOLFSSL_USER_SETTINGS_H

/* ---- Core TLS Features ---- */
#define HAVE_TLS_EXTENSIONS
#define HAVE_SUPPORTED_CURVES
#define HAVE_ALPN
#define USE_WOLF_STRTOK        /* Required with HAVE_ALPN on embedded runtimes */

/* ---- Cryptography ---- */
#define HAVE_ECC
#define HAVE_AESGCM

/* ---- Embedded / Bare-Metal Adjustments ---- */

/* Define if your runtime does not provide a working time() */
/* #define USER_TIME */

/* Reduce memory footprint for constrained targets */
#define WOLFSSL_SMALL_STACK
#define NO_FILESYSTEM          /* If no file system is available */
#define NO_WRITEV

/* ---- Optional: Disable unused algorithms to save code space ---- */
/* #define NO_DES3 */
/* #define NO_RC4  */
/* #define NO_MD4  */

#endif /* WOLFSSL_USER_SETTINGS_H */
```

> **Note:** Always define `WOLFSSL_USER_SETTINGS` in your IDE project's global preprocessor settings (compiler options) so that wolfSSL picks up `user_settings.h` instead of relying on `settings.h` defaults.

---

## 6. Assembly and Inline Assembly

When wolfSSL is built with `WOLFSSL_ARMASM` on IAR or Keil, the Thumb-2 and ARM32 inline assembly paths are activated via `_c.c` files. These compilers interact differently with inline assembly than GCC.

### WOLFSSL_NO_VAR_ASSIGN_REG

IAR and Keil do not support GCC's `register ... __asm__("rN")` syntax. The `_c.c` file headers auto-define `WOLFSSL_NO_VAR_ASSIGN_REG` when `__IAR_SYSTEMS_ICC__` or `__KEIL__` is detected. This switches to a code path where the compiler freely assigns registers to operands instead of using fixed register bindings. This is the most common source of IAR/Keil-specific assembly bugs — see `compiler-toolchain-assembly.md` for the full correctness model.

### IAR Stack Alignment

IAR enforces a maximum alignment for automatic (stack-allocated) variables that may be stricter than GCC's. When `WOLFSSL_USE_ALIGN` is active (auto-defined by `WOLFSSL_ARMASM`), macros like `ALIGN16` may request alignment that exceeds IAR's stack limit. This causes compile errors like `'Auto variable cannot have a stricter alignment than the stack'`.

**Investigation pattern:** Check `wolfssl/wolfcrypt/types.h` for the `WOLFSSL_ALIGN()` macro — it may contain compiler-specific caps for IAR (`__ICCARM__`). If no cap exists for the customer's wolfSSL version, the options are: (a) override `ALIGN16`/`ALIGN32`/`ALIGN64` in `user_settings.h` to a supported value, or (b) undefine `WOLFSSL_USE_ALIGN` (safe for correctness on Cortex-M without NEON, may affect performance). Do NOT hardcode IAR's specific limit — verify via IAR documentation or tag as `[UNVERIFIED]`.

### IAR Static Clustering

IAR's "static clustering" optimization reorders static variables and code for cache efficiency. This can interact with inline assembly assumptions about data layout. Customers may report that disabling static clustering for a specific `_c.c` file "fixes" incorrect output. This is typically a symptom of a clobber list or register constraint bug that static clustering exposes — investigate the clobber list rather than accepting the workaround.

### WOLFSSL_ARMASM_INLINE

This define gates whether the `_c.c` inline assembly path is compiled. When using IAR/Keil with `WOLFSSL_ARMASM`, verify that `WOLFSSL_ARMASM_INLINE` is defined — without it, the inline assembly code is excluded and the build may fall back to C implementations or fail to link.

### Keil ARMCC 5 vs Arm Compiler 6

Keil MDK-ARM supports two compiler backends:
- **ARMCC 5 (legacy)** — Uses proprietary inline assembly syntax. wolfSSL detects it via `__KEIL__` and `__ARMCC_VERSION`.
- **Arm Compiler 6 (armclang, Clang-based)** — Supports GCC-compatible inline assembly syntax. May handle `__asm__` blocks natively but may not support `register ... __asm__("rN")`.

**Investigation pattern:** Check which compiler version the customer uses. The `_c.c` file header shows which versions are handled. If the customer uses Arm Compiler 6 and the generated code doesn't have an armclang detection block, it may need one.

---

## Additional Resources

- wolfSSL Manual: [https://www.wolfssl.com/documentation/](https://www.wolfssl.com/documentation/)
- IAR project README: `IDE/IAR-EWARM/README`
- Keil project files: `IDE/MDK-ARM/Projects/`
- For embOS-specific configuration: `IDE/IAR-EWARM/embOS/`

**IAR Documentation (Public -- freely downloadable PDFs)**:
- IAR C/C++ Development Guide for ARM -- covers compiling, linking, data storage, C/C++ language extensions, linker configuration. Multiple versions hosted on IAR's own servers at wwwfiles.iar.com
- IAR IDE Project Management and Building Guide
- Available for multiple target architectures (ARM, AVR, STM8, etc.)

**Arm/Keil CMSIS Documentation (Public -- open source Apache 2.0)**:
- CMSIS-Driver API: Full API docs at arm-software.github.io/CMSIS_6/main/Driver/index.html, GitHub source at github.com/ARM-software/CMSIS-Driver
- RTX5 RTOS: Full docs at arm-software.github.io/CMSIS-RTX/latest/index.html, GitHub source at github.com/ARM-software/CMSIS-RTX (Apache 2.0)
- CMSIS-Driver covers: CAN, Ethernet, I2C, MCI, NAND, Flash, SAI, SPI, Storage, USART, USB, GPIO, VIO, WiFi
- **Important note**: CMSIS-Driver does NOT include a dedicated crypto driver API. Crypto in the CMSIS/Keil ecosystem is handled through PSA Crypto API (Mbed TLS / TF-M), not CMSIS-Driver.
- RTX5 is shipped free with Keil MDK and is fully open source

> **Disclaimer:** The source material available for this guide is limited. The information above reflects what is directly supported by wolfSSL's source code and project structure. For complete IAR and Keil integration details — including specific hardware crypto drivers, RTOS threading configuration, and memory benchmarks — consult the official wolfSSL manual and the README files shipped with the IDE project directories.
