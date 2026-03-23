---
paths:
  - "**/itron*"
  - "**/ITRON*"
---

# TOPPERS/uITRON -- wolfSSL Platform Guide

## 1. Overview

uITRON (micro Industrial TRON) is a real-time OS specification widely used in Japanese
embedded systems, standardized by TOPPERS. wolfSSL supports two ITRON-family platforms:

- **uITRON4** -- The uITRON 4.0 specification. Enabled via `WOLFSSL_uITRON4`.
- **uT-Kernel 2** -- T-Kernel-based RTOS compatible with ITRON conventions. Enabled via `WOLFSSL_uTKERNEL2`.

Both share the same architecture: custom memory pool allocators backed by kernel memory
pool services, and semaphore-based mutexes. Common in automotive and industrial applications.

wolfSSL support includes:
- Custom memory allocator using ITRON variable-size memory pools
- Mutex implementation via ITRON semaphore primitives (`TA_TFIFO`, binary semaphore)
- No default hardware RNG -- users must provide `wc_GenerateSeed()` or `CUSTOM_RAND_GENERATE_BLOCK`
- MDK5-ARM IDE integration via Keil configuration wizard

## 2. Build Configuration

### uITRON4

Define `WOLFSSL_uITRON4` in `user_settings.h` or as a compiler define. When enabled:

| Setting               | Value / Effect                                      |
|-----------------------|-----------------------------------------------------|
| `XMALLOC_USER`       | Defined -- overrides default malloc/free/realloc    |
| `ITRON_POOL_SIZE`     | `1024*20` (20 KB default memory pool)               |
| `XMALLOC`            | Maps to `uITRON4_malloc(sz)`                        |
| `XREALLOC`           | Maps to `uITRON4_realloc(p, sz)`                    |
| `XFREE`              | Maps to `uITRON4_free(p)`                           |

Required headers: `<stddef.h>`, `"kernel.h"` (ITRON kernel API).

### uT-Kernel 2

Define `WOLFSSL_uTKERNEL2` for T-Kernel systems. Uses `tk_` prefixed API calls:

| Setting               | Value / Effect                                      |
|-----------------------|-----------------------------------------------------|
| `XMALLOC_OVERRIDE`   | Defined (unless `NO_TKERNEL_MEM_POOL` is set)       |
| `XMALLOC`            | Maps to `uTKernel_malloc(s)`                        |
| `XREALLOC`           | Maps to `uTKernel_realloc(p, n)`                    |
| `XFREE`              | Maps to `uTKernel_free(p)`                          |

Required header: `"tk/tkernel.h"`. Also remaps `fgets` via T-Monitor unless
`NO_STDIO_FGETS_REMAP` is defined.

### MDK5-ARM / Keil

Both platforms are selectable in `IDE/MDK5-ARM/Conf/user_settings.h`:
set `MDK_CONF_THREAD` to `11` (uITRON4) or `12` (uT-Kernel 2).

## 3. Platform-Specific Features

### Memory Pool Initialization

Both platforms require explicit memory pool init before any wolfSSL calls.

**uITRON4** -- Call `uITRON4_minit()` with the pool size:
```c
int ret = uITRON4_minit(ITRON_POOL_SIZE);  /* default: 20480 bytes */
```
Calls `acre_mpl()` to create a variable-size pool with `TA_TFIFO` attribute. Pool ID
is stored statically and used by all malloc/free/realloc calls.

**uT-Kernel 2** -- Call `uTKernel_init_mpool()`:
```c
int ret = uTKernel_init_mpool(20480);  /* size in bytes */
```
Calls `tk_cre_mpl()`. The pool object name is "wolfSSL" (T-Kernel 8-char limit).

### Mutex Implementation

Both platforms implement `wolfSSL_Mutex` as a struct with `T_CSEM sem` and `ID id`.
Mutexes are binary semaphores (`isemcnt=1`, `maxsem=1`) with `TA_TFIFO` ordering.

- **uITRON4**: `acre_sem`, `wai_sem`, `sig_sem`, `del_sem`
- **uT-Kernel 2**: `tk_cre_sem`, `tk_wai_sem`, `tk_sig_sem`, `tk_del_sem`

### Random Number Generation

Neither platform has a default seed implementation. Provide one of:
1. Implement `wc_GenerateSeed()` for your MCU's hardware RNG
2. Define `CUSTOM_RAND_GENERATE_BLOCK` pointing to your RNG function
3. Testing only: `WOLFSSL_GENSEED_FORTEST` (never in production)

## 4. Common Issues

### Memory pool not initialized
**Symptom**: Segfault or NULL pointer on first wolfSSL call (`wolfSSL_CTX_new`).
**Fix**: Call `uITRON4_minit()` or `uTKernel_init_mpool()` before `wolfSSL_Init()`.

### Pool size too small
**Symptom**: `MEMORY_E` during handshake. Default 20 KB is too small for TLS (needs 40-60 KB).
**Fix**: Increase pool size and enable `WOLFSSL_SMALL_STACK`:
```c
#undef  ITRON_POOL_SIZE
#define ITRON_POOL_SIZE (1024 * 60)
```

### realloc copies wrong size
The `realloc` implementations use `XMEMCPY(newp, p, sz)` where `sz` is the *new* size,
not the old. If growing a buffer, this reads beyond the original allocation. Avoid
realloc-heavy patterns on these platforms.

### No hardware RNG defined
**Symptom**: Build error or `NOT_COMPILED_IN` from `wc_GenerateSeed`.
**Fix**: Implement a seed function using your MCU's TRNG peripheral.

### Choosing between uITRON4 and uTKERNEL2
- `WOLFSSL_uITRON4` for TOPPERS/ASP, TOPPERS/JSP, or uITRON 4.0 compliant kernels
- `WOLFSSL_uTKERNEL2` for T-Kernel 2.0 / uT-Kernel 2.0 systems
- Do not define both simultaneously

## 5. Example Configuration

### Minimal uITRON4 user_settings.h

```c
#define WOLFSSL_uITRON4
#define WOLFSSL_SMALL_STACK
#define NO_FILESYSTEM
#define NO_WRITEV
#define SINGLE_THREADED          /* Remove if using ITRON tasks */
#define NO_OLD_TLS               /* TLS 1.2+ only */
#define NO_DSA
#define NO_RC4
#define NO_MD4
#define NO_PSK
#define NO_DES3
#define CUSTOM_RAND_GENERATE_BLOCK  my_rng_generate_block
#undef  ITRON_POOL_SIZE
#define ITRON_POOL_SIZE (1024 * 60)  /* 60 KB for TLS */
```

### Application startup sequence

```c
#include <wolfssl/ssl.h>

int wolfssl_itron_init(void) {
    int ret;
    /* 1. Memory pool must be initialized first */
    ret = uITRON4_minit(ITRON_POOL_SIZE);
    if (ret != 0) return ret;
    /* 2. Then wolfSSL library init */
    ret = wolfSSL_Init();
    if (ret != WOLFSSL_SUCCESS) return ret;
    /* 3. Normal wolfSSL usage from here */
    WOLFSSL_CTX* ctx = wolfSSL_CTX_new(wolfTLSv1_2_client_method());
    if (ctx == NULL) return MEMORY_E;
    return 0;
}
```

For uT-Kernel 2, replace `WOLFSSL_uITRON4` with `WOLFSSL_uTKERNEL2` and call
`uTKernel_init_mpool(60 * 1024)` instead. All other API usage is identical.
