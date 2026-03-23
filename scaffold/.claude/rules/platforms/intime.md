---
paths:
  - "**/intime*"
  - "**/INtime*"
---

# TenAsys INtime RTOS — wolfSSL Platform Guide

## 1. Overview

INtime is a real-time operating system from TenAsys Corporation that provides a deterministic RTOS kernel running alongside the Windows operating system on x86/x64 hardware. INtime enables hard real-time applications to coexist with Windows on the same processor, using INtime's own scheduler for time-critical tasks while Windows handles non-real-time operations.

wolfSSL supports INtime RTOS through the `INTIME_RTOS` define. This define is recognized across multiple wolfSSL source files including `settings.h`, `wc_port.h`, `wolfio.h`, `types.h`, `tfm.h`, and `logging.h`. wolfSSL ships with a complete example `user_settings.h` and IDE project files in the `IDE/INTIME-RTOS/` directory.

INtime provides a subset of Windows-compatible APIs plus its own native RTOS APIs. A key aspect of wolfSSL's INtime integration is that `INTIME_RTOS` explicitly excludes the `USE_WINDOWS_API` define — even though compilation occurs on Windows with MSVC, wolfSSL uses INtime's native POSIX-like socket and threading APIs instead of Win32.

---

## 2. Build Configuration

### Primary Define

Enable INtime RTOS support in wolfSSL with:

```c
#define INTIME_RTOS
```

This is **not** listed as a commented-out option in the top section of `settings.h`. Instead, it is referenced in conditional blocks throughout wolfSSL's headers. Define it in your `user_settings.h` or compiler flags.

### How to Enable

**Option A — Define in `user_settings.h` (recommended):**

```c
#define WOLFSSL_USER_SETTINGS
```

Then in your `user_settings.h`:

```c
#undef  INTIME_RTOS
#define INTIME_RTOS
```

The example `user_settings.h` in `IDE/INTIME-RTOS/` uses the `#undef`/`#define` pattern consistently to avoid redefinition warnings.

**Option B — Pass via compiler flags:**

```
-DINTIME_RTOS
```

### What the Define Controls

The `INTIME_RTOS` define affects wolfSSL behavior in several subsystems:

| Area | Effect |
|------|--------|
| Windows API exclusion | Prevents `USE_WINDOWS_API` from being defined, even under `_WIN32` (`settings.h` line ~1452) |
| Socket I/O | Includes `<rt.h>`, `<sys/types.h>`, `<sys/socket.h>`, `<netdb.h>`, `<netinet/in.h>`, `<netinet/tcp.h>` via `wolfio.h` |
| Threading | Mutex type is `RTHANDLE` (INtime native handle); thread type is `uintptr_t` with `__stdcall` convention (`wc_port.h`, `types.h`) |
| Filesystem | Uses `_stat64`, `_findfirst64`/`_findnext64`/`_findclose64` for directory operations (`wc_port.h`) |
| String functions | Uses `strtok_s()` (same as Windows) for `XSTRTOK` (`types.h`) |
| Intrinsics | Disables Intel intrinsics / `FAST_ROTATE` to avoid MSVC-specific rotate intrinsics (`types.h`) |
| Logging | `__func__` macro defined as `NULL` since INtime's compiler context does not support it (`logging.h`) |
| TFM math | Undefines `long64` before redefining it, to handle INtime's type conflicts (`tfm.h`) |

### IDE / Project Files

wolfSSL includes INtime RTOS project files at:

```
IDE/INTIME-RTOS/
```

This directory contains `user_settings.h` with a comprehensive configuration including:
- Full ECC support (multiple curve sizes, custom curves, Brainpool, Koblitz)
- RSA with fast math (4096-bit max)
- AES-GCM, ChaCha20/Poly1305, Ed25519/Curve25519
- DTLS, OCSP, CRL, PKCS#7, SNI, ALPN, session tickets
- OpenSSL compatibility layer (`OPENSSL_EXTRA`, `OPENSSL_ALL`)
- Side-channel protections (timing resistant, RSA blinding)

### Configure System

INtime builds use Visual Studio (MSVC) with the INtime SDK. The autoconf `./configure` system is not used. All configuration is via `user_settings.h`.

---

## 3. Platform-Specific Features

### Threading

When `INTIME_RTOS` is defined, wolfSSL uses INtime's native threading primitives:

| wolfSSL abstraction | INtime type |
|---------------------|-------------|
| `wolfSSL_Mutex` | `RTHANDLE` (INtime kernel object handle) |
| `THREAD_RETURN` | `unsigned int` |
| `THREAD_TYPE` | `uintptr_t` (temporarily renamed to avoid conflict with INtime's own `THREAD_TYPE`) |
| Thread calling convention | `__stdcall` |

wolfSSL handles a naming conflict between its internal `THREAD_TYPE` and INtime's `THREAD_TYPE` by temporarily renaming via `INTIME_THREAD_TYPE`, then restoring after the wolfSSL type definitions.

The INtime port includes `<rt.h>` and `<io.h>` for RTOS kernel services.

### Networking

INtime provides a BSD-compatible socket API. wolfSSL's `wolfio.h` includes the standard POSIX socket headers when `INTIME_RTOS` is defined:

```c
#include <rt.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netdb.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
```

This means wolfSSL's default socket I/O layer works with INtime without needing `WOLFSSL_USER_IO`. The socket API is available from INtime's TCP/IP stack, which operates within the real-time kernel.

### Filesystem

INtime provides filesystem access through POSIX-like APIs. wolfSSL maps its directory operations to INtime's `_stat64` and `_findfirst64`/`_findnext64` family. The example `user_settings.h` does **not** define `NO_FILESYSTEM`, meaning file-based certificate loading is available by default.

### Memory and Alignment

The example configuration sets:

```c
#define WOLFSSL_GENERAL_ALIGNMENT   4
#define WOLFSSL_HAVE_MIN            /* Platform provides min() */
#define WOLFSSL_HAVE_MAX            /* Platform provides max() */
```

Standard `malloc`/`free` from the INtime C runtime are used by default. The example does not override `XMALLOC`/`XFREE`.

### Hardware Cryptography

INtime runs on standard x86/x64 PC hardware. Hardware crypto depends on the processor:
- **AES-NI**: Available on Intel/AMD processors with AES-NI support; use `WOLFSSL_AESNI` and `HAVE_INTEL_RDSEED`
- **Intel RDRAND/RDSEED**: For hardware entropy

Note: The example `user_settings.h` does not enable these by default — the INtime compiler/intrinsics environment may require validation before enabling processor-specific acceleration.

---

## 4. Common Issues

### Windows API Exclusion

The most important behavior of `INTIME_RTOS` is preventing `USE_WINDOWS_API` from being defined. Without `INTIME_RTOS`, compiling under MSVC with `_WIN32` defined would activate the Win32 API path, which is incompatible with INtime's kernel. Always ensure `INTIME_RTOS` is defined before any wolfSSL headers are included.

### `THREAD_TYPE` Name Conflict

INtime's headers define their own `THREAD_TYPE`. wolfSSL works around this by:
1. Saving INtime's `THREAD_TYPE` as `INTIME_THREAD_TYPE`
2. Defining wolfSSL's own `THREAD_TYPE` as `uintptr_t`
3. Restoring the original after wolfSSL's type block

This is handled automatically in `types.h`, but be aware of it if you encounter unexpected type errors when mixing wolfSSL and INtime threading code.

### `__func__` Not Available

INtime's MSVC-based compilation environment does not support `__func__` in all contexts. wolfSSL defines `__func__` as `NULL` when `INTIME_RTOS` is defined with `DEBUG_WOLFSSL` enabled. Debug log output will show `NULL` instead of function names. Use `__FUNCTION__` (MSVC extension) if you need function names in custom debug output.

### `HAVE_THREAD_LS` Not Supported

The example `user_settings.h` includes a comment: "Note: HAVE_THREAD_LS is not supported for INtime RTOS." Do not define `HAVE_THREAD_LS` — thread-local storage via `__declspec(thread)` is not available in the INtime environment.

### Stack Size

The example configuration sets `WOLF_EXAMPLES_STACK` to `(1<<17)` (128 KB) for the wolfSSL example/test threads. For production:
- Allocate at least **16-32 KB** for TLS handshake threads
- Use `WOLFSSL_SMALL_STACK` if stack space is constrained (commented out by default in the example)

### Intel Intrinsics Disabled

`INTIME_RTOS` disables `INTEL_INTRINSICS` and `FAST_ROTATE` in `types.h`. This means wolfSSL will not use MSVC's `_lrotl`/`_lrotr` intrinsics. If your INtime build environment supports these intrinsics reliably, you may need to test and manually re-enable them.

### No `configure` System

INtime builds use Visual Studio with the INtime SDK toolchain. All configuration via `user_settings.h`:
```c
#define WOLFSSL_USER_SETTINGS
```

---

## 5. Example Configuration

The following is a reduced `user_settings.h` for INtime RTOS. For the full-featured example, see `IDE/INTIME-RTOS/user_settings.h`.

```c
/* user_settings.h — wolfSSL on TenAsys INtime RTOS */

#ifndef WOLFSSL_USER_SETTINGS_H
#define WOLFSSL_USER_SETTINGS_H

#ifdef __cplusplus
extern "C" {
#endif

/* ---- Platform ---- */
#undef  INTIME_RTOS
#define INTIME_RTOS

#define WOLFSSL_GENERAL_ALIGNMENT   4
#define WOLFSSL_HAVE_MIN
#define WOLFSSL_HAVE_MAX
#define NO_WRITEV
#define NO_MAIN_DRIVER

/* ---- Threading ---- */
/* #define SINGLE_THREADED */  /* Uncomment for single-threaded use */

/* ---- Math ---- */
#define USE_FAST_MATH
#define TFM_TIMING_RESISTANT
#ifdef USE_FAST_MATH
    #define FP_MAX_BITS     4096   /* Supports RSA-2048 */
#endif

/* ---- Crypto ---- */
#define HAVE_ECC
#define ECC_TIMING_RESISTANT
#define HAVE_AESGCM
#define HAVE_CHACHA
#define HAVE_POLY1305
#define HAVE_ONE_TIME_AUTH
#define HAVE_CURVE25519
#define HAVE_ED25519

/* ---- Security hardening ---- */
#define WC_RSA_BLINDING
#define ECC_TIMING_RESISTANT

/* ---- Cipher suite tuning ---- */
#define NO_RC4
#define NO_MD4

/* ---- TLS features ---- */
#define HAVE_TLS_EXTENSIONS
#define HAVE_SUPPORTED_CURVES
#define HAVE_EXTENDED_MASTER
#define HAVE_SNI
#define HAVE_ALPN

/* ---- Benchmark / Test ---- */
#define BENCH_EMBEDDED
#define USE_CERT_BUFFERS_2048
#define USE_CERT_BUFFERS_256

/* ---- Debug (disable for production) ---- */
/* #define DEBUG_WOLFSSL */

#ifdef __cplusplus
}
#endif

#endif /* WOLFSSL_USER_SETTINGS_H */
```

Build with `WOLFSSL_USER_SETTINGS` defined in Visual Studio project properties (C/C++ -> Preprocessor -> Preprocessor Definitions):
```
WOLFSSL_USER_SETTINGS
```

---

## 6. Related Resources

- **TenAsys Guides & Manuals:** https://tenasys.com/resources/documentation/
- **INtime SDK Online Help:** https://support.tenasys.com/intimehelp/
- **INtime for Windows User Guide (PDF):** https://tenasys.com/wp-content/uploads/2016/08/INtimeForWindows40UsersGuide.pdf
- **INtime RTOS Datasheet:** https://tenasys.com/wp-content/uploads/2021/08/TenAsys-INtime-RTOS-datasheet-07022024.pdf
- **wolfSSL INtime IDE project files:** `IDE/INTIME-RTOS/` in the wolfSSL source tree
- **wolfSSL Manual:** https://www.wolfssl.com/documentation/manuals/wolfssl/
- **TenAsys Corporation:** https://www.tenasys.com/
