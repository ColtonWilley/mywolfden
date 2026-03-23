---
paths:
  - "**/safertos*"
  - "**/SafeRTOS*"
---

# SafeRTOS (WITTENSTEIN) — wolfSSL Platform Guide

## 1. Overview

SafeRTOS is a safety-certified real-time operating system from WITTENSTEIN High Integrity Systems. It is a derivative of FreeRTOS that has been redesigned, tested, and independently certified to IEC 61508 SIL 3 and ISO 26262 ASIL D standards. SafeRTOS is used in automotive, industrial, medical, and aerospace applications where functional safety certification is required.

wolfSSL supports SafeRTOS through the `WOLFSSL_SAFERTOS` define in `wolfssl/wolfcrypt/settings.h` (line ~1791). When enabled, wolfSSL configures its threading primitives, memory allocation, and internal abstractions for compatibility with the SafeRTOS API. The SafeRTOS support block is also implicitly activated when `WOLFSSL_LSR` is defined (line ~1784), which sets `WOLFSSL_SAFERTOS` along with several constrained-environment defaults.

> **Key difference from FreeRTOS:** Although SafeRTOS is derived from FreeRTOS, it has modified API signatures, a different error handling model (API functions return error codes rather than void), and memory allocation is static-only by default. Do not assume FreeRTOS code ports directly — API calls and error handling patterns require adjustment.

---

## 2. Build Configuration

### Primary Define

Enable SafeRTOS support in wolfSSL with:

```c
#define WOLFSSL_SAFERTOS
```

This is recognized in `wolfssl/wolfcrypt/settings.h` and triggers SafeRTOS-specific threading and memory configuration.

### How to Enable

**Option A — Define in `user_settings.h` (recommended for embedded targets):**

```c
#define WOLFSSL_USER_SETTINGS
```

Then in your `user_settings.h`:

```c
#define WOLFSSL_SAFERTOS
```

**Option B — Pass via compiler flags:**

```
-DWOLFSSL_SAFERTOS
```

### What the Define Enables

When `WOLFSSL_SAFERTOS` is defined, `settings.h` applies the following configuration:

| Behavior | Detail |
|----------|--------|
| Threading | Includes `SafeRTOS/semphr.h` (unless `SINGLE_THREADED`) |
| Heap | Includes `SafeRTOS/heap.h` (unless `WOLFSSL_NO_MALLOC`) |
| `XMALLOC` | Maps to `pvPortMalloc()` |
| `XFREE` | Maps to `vPortFree()` |
| `XREALLOC` | Maps to `pvPortRealloc()` (when needed for Ed25519/Ed448 or non-fastmath) |
| Mutex type | `wolfSSL_Mutex` is a struct containing `mutexBuffer[portQUEUE_OVERHEAD_BYTES]` + `xSemaphoreHandle` |

### Related Define: `WOLFSSL_LSR`

The `WOLFSSL_LSR` define (for Luminary Stellaris platform) automatically sets `WOLFSSL_SAFERTOS` along with:

```c
#define WOLFSSL_LOW_MEMORY
#define NO_WRITEV
#define NO_SHA512
#define NO_DH
#define NO_DSA
#define NO_DEV_RANDOM
#define NO_WOLFSSL_DIR
#define WOLFSSL_LWIP
#define WOLFSSL_SAFERTOS
```

If you are on a Stellaris/Tiva C platform with SafeRTOS, `WOLFSSL_LSR` provides a pre-tuned configuration. Otherwise, define `WOLFSSL_SAFERTOS` directly and select features individually.

### Configure Flags

SafeRTOS builds do not use the autoconf `./configure` system. All configuration is done via `user_settings.h` or compiler defines. Ensure `WOLFSSL_USER_SETTINGS` is defined globally so wolfSSL loads your settings file.

### IDE / Project Files

No SafeRTOS-specific IDE project files are included in the wolfSSL source tree. SafeRTOS itself is a commercially licensed product — project setup depends on the target hardware, the SafeRTOS variant purchased, and the customer's chosen toolchain (IAR EWARM, Keil MDK, GCC ARM, etc.).

---

## 3. Platform-Specific Features

### Threading

When `WOLFSSL_SAFERTOS` is defined and `SINGLE_THREADED` is not, wolfSSL includes `SafeRTOS/semphr.h` and uses SafeRTOS semaphore primitives for mutex operations:

| wolfSSL abstraction | SafeRTOS mapping |
|---------------------|------------------|
| `wolfSSL_Mutex` type | Struct with `mutexBuffer` + `xSemaphoreHandle` |
| Mutex operations | Via SafeRTOS semaphore API |

The mutex struct includes a `mutexBuffer` sized to `portQUEUE_OVERHEAD_BYTES`, which SafeRTOS uses for static semaphore storage. This differs from FreeRTOS, which can dynamically allocate semaphore control blocks.

### Memory Allocation

SafeRTOS uses static memory allocation by design. wolfSSL maps its memory functions to the SafeRTOS port allocator:

```c
#define XMALLOC(s, h, type)   pvPortMalloc((s))
#define XFREE(p, h, type)     vPortFree((p))
#define XREALLOC(p, n, h, t)  pvPortRealloc((p), (n))
```

These mappings are applied unless `XMALLOC_USER`, `NO_WOLFSSL_MEMORY`, or `WOLFSSL_STATIC_MEMORY` is defined. The `XREALLOC` mapping is only needed when not using `USE_FAST_MATH` or when Ed25519/Ed448 is enabled.

For fully static wolfSSL memory allocation (no heap at all):

```c
#define WOLFSSL_STATIC_MEMORY
```

### Networking

SafeRTOS does not include a TCP/IP stack. The networking layer depends on what stack is paired with SafeRTOS on your platform:

- **lwIP**: Common pairing; use `WOLFSSL_LWIP` alongside `WOLFSSL_SAFERTOS`
- **Custom I/O**: For vendor-specific or proprietary stacks, use custom I/O callbacks:

```c
#define WOLFSSL_USER_IO
```

Then register callbacks:
```c
wolfSSL_CTX_SetIORecv(ctx, my_recv_cb);
wolfSSL_CTX_SetIOSend(ctx, my_send_cb);
```

### Hardware Cryptography

No hardware crypto acceleration is specific to SafeRTOS itself. Enable hardware crypto defines based on the target SoC. Common examples for platforms that run SafeRTOS:

| Hardware | wolfSSL Define |
|----------|----------------|
| TI Tiva C / Stellaris | Hardware RNG, AES (via `WOLFSSL_LSR` defaults) |
| STM32 (F2/F4/F7/H7) | `WOLFSSL_STM32F2`, `WOLFSSL_STM32F4`, etc. |
| NXP i.MX / LPC | `WOLFSSL_NXP_CAAM` or `FREESCALE_USE_LTC` |
| Renesas RX/RA | `WOLFSSL_RENESAS_TSIP` |

---

## 4. Common Issues

### SafeRTOS API Differs from FreeRTOS

SafeRTOS functions return error codes (e.g., `pdPASS`, `errQUEUE_FULL`) where FreeRTOS equivalents may return void or use different conventions. wolfSSL's internal SafeRTOS mutex code accounts for this, but any custom application code interfacing with both wolfSSL and SafeRTOS directly must check SafeRTOS return values.

### Static Memory Model

SafeRTOS enforces static memory allocation. The `pvPortMalloc`/`vPortFree` functions in SafeRTOS operate on a pre-allocated memory pool. Ensure the pool is large enough for wolfSSL's runtime allocation needs. For a typical TLS 1.3 connection with RSA-2048:
- **40-80 KB** of heap pool recommended (varies with cipher suite and certificate chain depth)
- Use `WOLFSSL_STATIC_MEMORY` for fully deterministic, pool-based allocation if heap sizing is difficult

### Stack Size

SafeRTOS tasks require careful stack sizing:
- **Minimum 8-16 KB** for TLS handshake operations
- **16-24 KB** for larger key sizes (RSA-4096, deep cert chains, or post-quantum)
- Use `WOLFSSL_SMALL_STACK` to move large buffers to heap and reduce per-call stack usage

SafeRTOS provides stack overflow detection that can be enabled per-task — use it during development.

### `pvPortRealloc` Availability

The `XREALLOC` macro maps to `pvPortRealloc()`, but not all SafeRTOS ports provide this function. If your port lacks it:
- Use `USE_FAST_MATH` (which avoids most realloc calls), or
- Define `XMALLOC_USER` and provide your own realloc implementation

The wolfSSL FreeRTOS community has a reference `pvPortRealloc` implementation: https://github.com/wolfSSL/wolfssl-freertos/pull/3/files

### Entropy / Random Number Generation

SafeRTOS does not provide an entropy source. Provide a hardware RNG:

```c
/* Option 1: Custom seed function */
#define CUSTOM_RAND_GENERATE_BLOCK  my_rng_function

/* Option 2: Custom rand type + generator */
#define CUSTOM_RAND_TYPE      unsigned int
#define CUSTOM_RAND_GENERATE  my_rand_generate
```

If using `WOLFSSL_LSR`, `NO_DEV_RANDOM` is already defined, and you must supply a hardware RNG source.

### No `configure` System

SafeRTOS builds never use autoconf. All configuration must be in `user_settings.h`:
```c
#define WOLFSSL_USER_SETTINGS
```

---

## 5. Example Configuration

Minimal `user_settings.h` for wolfSSL on SafeRTOS:

```c
/* user_settings.h — wolfSSL on WITTENSTEIN SafeRTOS */

#ifndef WOLFSSL_USER_SETTINGS_H
#define WOLFSSL_USER_SETTINGS_H

/* ---- Platform ---- */
#define WOLFSSL_SAFERTOS

/* ---- Core TLS ---- */
#define WOLFSSL_TLS13
#define NO_OLD_TLS               /* Disable TLS 1.0 / 1.1 */

/* ---- Memory ---- */
#define WOLFSSL_SMALL_STACK      /* Reduce stack usage */
/* #define WOLFSSL_STATIC_MEMORY */  /* Optional: fully static allocation */

/* ---- Math ---- */
#define USE_FAST_MATH            /* Avoids realloc, uses stack-based math */
#define TFM_TIMING_RESISTANT

/* ---- Filesystem ---- */
#define NO_FILESYSTEM            /* Load certs from buffers */
#define NO_WRITEV

/* ---- Networking ---- */
#define WOLFSSL_USER_IO          /* Custom I/O callbacks */
/* #define WOLFSSL_LWIP */       /* Uncomment if using lwIP */

/* ---- Cipher suite tuning ---- */
#define NO_DES3
#define NO_RC4
#define NO_MD4

/* ---- Security hardening ---- */
#define ECC_TIMING_RESISTANT
#define WC_RSA_BLINDING

/* ---- Entropy ---- */
/* Provide hardware RNG for your target */
#define NO_DEV_RANDOM
/* #define CUSTOM_RAND_GENERATE_BLOCK  my_rng_function */

/* ---- Debug (disable for production) ---- */
/* #define DEBUG_WOLFSSL */

#endif /* WOLFSSL_USER_SETTINGS_H */
```

Build with `WOLFSSL_USER_SETTINGS` defined as a global compiler flag:
```
-DWOLFSSL_USER_SETTINGS
```

---

## 6. Related Resources

- **SafeRTOS Sample User Manual (public PDF):** https://highintegritysystems.com/downloads/manuals_and_datasheets/Sample_SafeRTOS_User_Manual.pdf
- **TI-hosted SafeRTOS User Manual (public PDF):** https://ti.com/lit/ug/spmu040a/spmu040a.pdf
- **SafeRTOS Datasheet:** https://highintegritysystems.com/downloads/manuals_and_datasheets/SafeRTOS_Datasheet.pdf
- **Full Design Assurance Pack (DAP):** IEC 61508 SIL 3 certification artifacts; requires purchase from WITTENSTEIN
- **wolfSSL Manual:** https://www.wolfssl.com/documentation/manuals/wolfssl/
- **wolfSSL FreeRTOS pvPortRealloc reference:** https://github.com/wolfSSL/wolfssl-freertos/pull/3/files
- **WITTENSTEIN High Integrity Systems:** https://www.highintegritysystems.com/safertos/
