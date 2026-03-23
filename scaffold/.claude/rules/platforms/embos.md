---
paths:
  - "**/embos*"
  - "**/emBOS*"
---

# embOS (SEGGER) — wolfSSL Platform Guide

## 1. Overview

embOS is a priority-controlled preemptive RTOS from SEGGER Microcontroller GmbH, designed for deeply embedded systems. wolfSSL includes embOS support via pre-built IDE project files located at `IDE/IAR-EWARM/embOS/` in the wolfSSL source tree. The embOS-Ultra variant uses innovative cycle-based scheduling (no periodic tick interrupt) for improved precision and reduced power consumption.

wolfSSL on embOS is typically built using IAR Embedded Workbench or SEGGER Embedded Studio, configured via `user_settings.h`. embOS provides thread-safe mutex primitives with recursive locking and priority inheritance, making it well-suited for wolfSSL's threading model.

---

## 2. Build Configuration

### Primary Define

Enable embOS support in wolfSSL with:

```c
#define WOLFSSL_EMBOS
```

This is listed in `wolfssl/wolfcrypt/settings.h` as a platform selector. It must be explicitly enabled.

### How to Enable

**Option A — Define in `user_settings.h` (recommended):**

```c
#define WOLFSSL_USER_SETTINGS
```

Then in your `user_settings.h`:

```c
#define WOLFSSL_EMBOS
```

**Option B — Pass via compiler flags:**

```
-DWOLFSSL_EMBOS
```

### IDE / Project Files

wolfSSL ships with embOS project files for IAR Embedded Workbench:

```
IDE/IAR-EWARM/embOS/
```

This directory contains pre-configured IAR workspace and project files for building wolfSSL as a library targeting embOS. Use this as a starting point and adjust for your specific hardware BSP.

### Configure System

embOS targets do not use the autoconf `./configure` system. All configuration is done via `user_settings.h` or compiler defines. Ensure `WOLFSSL_USER_SETTINGS` is defined globally so wolfSSL loads your settings file.

---

## 3. Platform-Specific Features

### Threading

When `WOLFSSL_EMBOS` is defined, wolfSSL maps its internal mutex operations to embOS primitives:

| wolfSSL abstraction | embOS API |
|---------------------|-----------|
| `wolfSSL_Mutex` type | `OS_MUTEX` |
| `wc_InitMutex()` | `OS_MUTEX_Create()` |
| `wc_LockMutex()` | `OS_MUTEX_LockBlocked()` |
| `wc_UnLockMutex()` | `OS_MUTEX_Unlock()` |
| `wc_FreeMutex()` | `OS_MUTEX_Delete()` |

embOS mutexes are recursive (counter-based) and support priority inheritance natively — no additional configuration required.

### Networking

embOS does not include a built-in TCP/IP stack. Common networking options:

- **SEGGER emNet** (formerly embOS/IP): SEGGER's own TCP/IP stack; provides BSD-like socket API
- **lwIP**: Lightweight IP; use `WOLFSSL_LWIP` define alongside `WOLFSSL_EMBOS`
- **Custom I/O**: For non-standard network stacks, implement custom callbacks

For custom I/O callbacks:

```c
/* In user_settings.h */
#define WOLFSSL_USER_IO
```

Then register callbacks per-context or per-session:
```c
wolfSSL_CTX_SetIORecv(ctx, my_recv_cb);
wolfSSL_CTX_SetIOSend(ctx, my_send_cb);
```

### Hardware Cryptography

Many targets running embOS include hardware crypto accelerators. Common combinations:

| Hardware | wolfSSL Define | Notes |
|----------|----------------|-------|
| STM32 (F2/F4/F7/H7) | `WOLFSSL_STM32F2` etc. | STM32 HAL crypto, hash, RNG |
| NXP (i.MX, LPC) | `WOLFSSL_NXP_CAAM` | CAAM crypto accelerator |
| Renesas (RX, RA, RZ) | `WOLFSSL_RENESAS_TSIP` | TSIP/SCE hardware crypto |
| Microchip (ATECC608) | `WOLFSSL_ATECC508A` | Secure element for ECC |
| Infineon (OPTIGA) | `WOLFSSL_CRYPTOCELL` | Hardware-backed crypto |

Add the hardware crypto define alongside `WOLFSSL_EMBOS` in `user_settings.h`.

### Memory Allocation

**Default:** wolfSSL uses standard `malloc`/`free`. On embOS, ensure thread safety:

- If your toolchain's libc is already thread-safe via embOS hooks (check CPU-specific embOS manual), no override is needed
- Otherwise, map to embOS thread-safe heap:

```c
#define XMALLOC(s, h, t)     OS_HEAP_malloc((s))
#define XFREE(p, h, t)       { if ((p)) OS_HEAP_free((p)); }
#define XREALLOC(p, n, h, t) OS_HEAP_realloc((p), (n))
```

**Static memory** (no heap allocation):
```c
#define WOLFSSL_STATIC_MEMORY
```

---

## 4. Common Issues

### Stack Size

Embedded embOS tasks require careful stack sizing for TLS operations:
- **Minimum 8-12 KB** for the task performing TLS handshake (RSA-2048 / ECC-256)
- **16-20 KB** for larger key sizes, deep certificate chains, or TLS 1.3 with post-quantum
- Use `WOLFSSL_SMALL_STACK` to move large buffers to heap
- Enable stack checking during development (`OS_LIBMODE_S` or `OS_LIBMODE_DP`) to detect overflows via `OS_Error()`

### No `configure` System

embOS builds do not use autoconf. All configuration via `user_settings.h`:
```c
/* Required */
#define WOLFSSL_USER_SETTINGS
```

### File System

Most embOS targets lack a standard filesystem. Use buffer-based cert/key loading:

```c
#define NO_FILESYSTEM

/* Load certs from C arrays compiled into flash */
wolfSSL_CTX_load_verify_buffer(ctx, ca_cert_der, sizeof(ca_cert_der), SSL_FILETYPE_ASN1);
wolfSSL_CTX_use_certificate_buffer(ctx, dev_cert_der, sizeof(dev_cert_der), SSL_FILETYPE_ASN1);
wolfSSL_CTX_use_PrivateKey_buffer(ctx, dev_key_der, sizeof(dev_key_der), SSL_FILETYPE_ASN1);
```

### Entropy / Random Number Generation

Provide a hardware RNG source. Options:

```c
/* Option 1: Custom RNG block function */
#define CUSTOM_RAND_GENERATE_BLOCK  my_rng_function

/* Option 2: Use STM32 HAL RNG (if on STM32) */
#define STM32_RNG
```

If no hardware RNG is available, seed from a hardware timer or external entropy source. Never use pseudo-random seeds in production.

### Time Source

wolfSSL needs wall-clock time for certificate date validation:

```c
/* Option 1: Custom time function */
#define USER_TIME
/* Then implement: time_t my_time(time_t* t) */

/* Option 2: Disable date checking (development only!) */
#define NO_ASN_TIME
```

For production, use an RTC or NTP-synchronized time source. `OS_TIME_GetTime_ms()` provides embOS system uptime but not wall-clock time.

### embOS-Ultra Timeout Units

embOS-Ultra API uses **milliseconds** for all timed operations (unlike embOS-Classic which uses tick counts). This affects any timeout calculations in custom wolfSSL I/O callbacks:

```c
/* Correct for embOS-Ultra */
OS_TASK_Delay_ms(100);            // 100 milliseconds
OS_MUTEX_LockTimed(&mtx, 5000);  // 5 second timeout
```

### Calling Context

wolfSSL operations must run in a proper embOS **task context** — never from:
- ISR context (`OS_INT_Enter()`/`OS_INT_Leave()` bracket)
- Software timer callbacks
- `main()` before `OS_Start()` (for blocking calls)

Calling blocking wolfSSL functions from ISR or timer context will trigger `OS_Error()` with `OS_ERR_ILLEGAL_IN_ISR` or `OS_ERR_ILLEGAL_IN_TIMER`.

---

## 5. Example Configuration

Minimal `user_settings.h` for wolfSSL on embOS-Ultra with IAR EWARM:

```c
/* user_settings.h — wolfSSL on SEGGER embOS-Ultra */

#ifndef WOLFSSL_USER_SETTINGS_H
#define WOLFSSL_USER_SETTINGS_H

/* ---- Platform ---- */
#define WOLFSSL_EMBOS
#define WOLFSSL_IAR_ARM          /* If using IAR Embedded Workbench */

/* ---- Core TLS ---- */
#define WOLFSSL_TLS13
#define NO_OLD_TLS               /* Disable TLS 1.0 / 1.1 */

/* ---- Memory ---- */
#define WOLFSSL_SMALL_STACK      /* Reduce stack usage for embedded tasks */
/* #define WOLFSSL_STATIC_MEMORY */  /* Optional: fully static allocation */

/* ---- Filesystem ---- */
#define NO_FILESYSTEM            /* Load certs from buffers */

/* ---- Networking ---- */
#define WOLFSSL_USER_IO          /* Custom I/O callbacks for emNet/lwIP */

/* ---- Cipher suite tuning ---- */
#define NO_DES3
#define NO_RC4
#define NO_MD4

/* ---- Entropy ---- */
/* Provide hardware RNG for your target */
/* #define CUSTOM_RAND_GENERATE_BLOCK  my_rng_function */
/* #define STM32_RNG */              /* If on STM32 with HAL RNG */

/* ---- Time ---- */
/* Provide wall-clock time for cert validation */
/* #define USER_TIME */

/* ---- Hardware crypto (uncomment for your target) ---- */
/* #define WOLFSSL_STM32F4 */       /* STM32F4xx HAL crypto */
/* #define WOLFSSL_STM32F7 */       /* STM32F7xx HAL crypto */
/* #define WOLFSSL_NXP_CAAM */      /* NXP CAAM accelerator */
/* #define WOLFSSL_RENESAS_TSIP */  /* Renesas TSIP/SCE */

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

- **embOS-Ultra Manual:** SEGGER UM01076 (v5.20.0)
- **wolfSSL IAR/embOS project files:** `IDE/IAR-EWARM/embOS/` in wolfSSL source tree
- **wolfSSL Manual:** https://www.wolfssl.com/documentation/manuals/wolfssl/
- **SEGGER embOS:** https://www.segger.com/products/rtos/embos/
- **External embOS reference:** See `integrations/embos.md` for full embOS API and architecture details
