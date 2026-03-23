---
paths:
  - "**/zephyr*"
  - "**/Zephyr*"
---

# Zephyr RTOS — wolfSSL Platform Guide

## 1. Overview

Zephyr RTOS is a small, scalable, open-source real-time operating system designed for resource-constrained embedded and IoT devices. wolfSSL provides native support for Zephyr through the `WOLFSSL_ZEPHYR` define, which enables platform-specific adaptations including kernel headers, memory management, and system utilities appropriate for the Zephyr environment.

wolfSSL's Zephyr support includes automatic version detection to handle API differences across Zephyr kernel versions, ensuring compatibility with both older and newer Zephyr releases.

---

## 2. Build Configuration

### Primary Define

| Define | Purpose |
|---|---|
| `WOLFSSL_ZEPHYR` | Enables all Zephyr-specific platform adaptations in wolfSSL |

### Configure Flags

No specific `./configure` flags are documented in the available source material for this platform. Zephyr projects typically use CMake-based build systems rather than autoconf. Check the wolfSSL manual or the `wolfssl/wolfcrypt/settings.h` file for additional build guidance.

### Kernel Version Handling

wolfSSL automatically detects the Zephyr kernel version at compile time and includes the appropriate headers:

- **Zephyr >= 3.1.0** (`KERNEL_VERSION_NUMBER >= 0x30100`): Uses the namespaced header paths:
  ```c
  #include <zephyr/kernel.h>
  #include <zephyr/sys/printk.h>
  #include <zephyr/sys/util.h>
  ```

- **Zephyr < 3.1.0**: Uses the legacy (non-namespaced) header paths:
  ```c
  #include <kernel.h>
  #include <sys/printk.h>
  #include <sys/util.h>
  ```

wolfSSL detects the version header using `__has_include`:
```c
#if __has_include(<zephyr/version.h>)
    #include <zephyr/version.h>
#else
    #include <version.h>
#endif
```

This means wolfSSL should build correctly across a range of Zephyr versions without manual intervention.

### C++ Compatibility

When `WOLFSSL_ZEPHYR` is defined and C++ is in use, wolfSSL closes any open `extern "C"` block before including Zephyr headers:

```c
#ifdef __cplusplus
    }  /* extern "C" */
#endif
```

This is handled automatically within `settings.h`.

---

## 3. Platform-Specific Features

### Memory Management

wolfSSL maps its internal memory abstraction macros to Zephyr's memory functions. Based on the pattern seen in the source (consistent with other RTOS ports such as Apache Mynewt), the expected mappings are:

| wolfSSL Macro | Zephyr Function |
|---|---|
| `XMALLOC` | `k_malloc` or equivalent |
| `XREALLOC` | `k_realloc` or equivalent |
| `XFREE` | `k_free` or equivalent |

> **Note:** The exact Zephyr memory function mappings were partially visible in the source material. Verify the complete definitions in `wolfssl/wolfcrypt/settings.h` under `WOLFSSL_ZEPHYR`.

### Threading

Zephyr provides its own threading primitives. wolfSSL's mutex and threading abstractions are expected to map to Zephyr kernel synchronization objects (e.g., `k_mutex`). The specific threading integration details are not fully captured in the available source material — consult the wolfSSL manual or `wc_port.h` / `wc_port.c` for the complete implementation.

### Networking

Networking integration details for Zephyr are not covered in the available source material. Zephyr uses its own BSD-like socket API (`CONFIG_NET_SOCKETS`). wolfSSL's I/O callbacks or Zephyr socket layer integration should be reviewed in the wolfSSL Zephyr example applications and the wolfSSL manual.

### Hardware Cryptography

Hardware crypto acceleration support for Zephyr is not described in the available source material. Check the wolfSSL manual and any Zephyr-specific example projects for hardware acceleration options relevant to your target SoC.

---

## 4. Common Issues

### Header Path Changes (Zephyr 3.1.0+)

Zephyr 3.1.0 introduced namespaced header paths (e.g., `<zephyr/kernel.h>` instead of `<kernel.h>`). wolfSSL handles this automatically via the version detection logic described above. If you encounter header-not-found errors, verify that:

- `WOLFSSL_ZEPHYR` is defined in your build.
- Your Zephyr version header (`version.h` or `zephyr/version.h`) is accessible to the compiler.

### C++ Linkage

If building wolfSSL in a mixed C/C++ Zephyr project, be aware that wolfSSL explicitly closes the `extern "C"` block before including Zephyr headers. Ensure your project's include order and linkage declarations are consistent with this behavior.

### Stack Sizing

Embedded RTOS environments like Zephyr have limited stack space. wolfSSL TLS operations can require significant stack depth. It is recommended to:

- Allocate sufficient stack for any thread performing TLS handshakes (commonly 8 KB or more, depending on cipher suites and key sizes).
- Use wolfSSL's `--enable-smallstack` build option or equivalent `user_settings.h` defines if stack space is constrained.

> **Note:** Specific stack size recommendations for Zephyr are not provided in the available source material. Consult the wolfSSL manual for embedded stack usage guidance.

### `__has_include` Availability

The version detection logic relies on `__has_include`, a compiler extension supported by GCC and Clang. If your toolchain does not support `__has_include`, wolfSSL falls back to including `<version.h>` directly. Ensure your toolchain supports this extension or that the correct version header is available on the include path.

---

## 5. Example Configuration

### Minimal `user_settings.h` for Zephyr

```c
/* user_settings.h — minimal wolfSSL configuration for Zephyr RTOS */

/* Required: identify the platform */
#define WOLFSSL_ZEPHYR

/* Recommended: use a user_settings.h file instead of autoconf */
#define WOLFSSL_USER_SETTINGS

/* TLS 1.3 support (optional, remove if not needed) */
#define WOLFSSL_TLS13

/* Reduce memory footprint for embedded targets */
#define WOLFSSL_SMALL_STACK
#define NO_FILESYSTEM          /* typical for embedded targets */

/* Disable unused features to reduce code size */
#define NO_OLD_TLS             /* disable TLS 1.0 and 1.1 */
#define NO_DSA
#define NO_DH                  /* remove if DH cipher suites are needed */
#define NO_RC4
#define NO_MD4

/* Enable required algorithms */
#define HAVE_TLS_EXTENSIONS
#define HAVE_SUPPORTED_CURVES
#define HAVE_AESGCM
#define HAVE_ECC
#define USE_FAST_MATH          /* or WOLFSSL_SP_MATH for smaller footprint */

/* Entropy / RNG — adjust based on available hardware RNG */
/* #define CUSTOM_RAND_GENERATE_BLOCK  my_rng_function */
```

### Notes on This Configuration

- `WOLFSSL_ZEPHYR` is the only strictly required define for platform support; all other entries are recommendations for typical embedded use.
- `NO_FILESYSTEM` is commonly needed on Zephyr targets that do not have a filesystem.
- Adjust algorithm enables/disables based on your application's cipher suite requirements.
- If your Zephyr target has a hardware RNG, configure the `CUSTOM_RAND_GENERATE_BLOCK` macro accordingly.

---

## Further Reading

The available source material for this platform is limited to the header inclusion and version detection logic in `settings.h`. For complete documentation on:

- Full memory, threading, and networking integration
- Hardware acceleration options
- Example Zephyr applications

Consult the [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/) and the `wolfssl-examples` repository for any Zephyr-specific sample projects.
