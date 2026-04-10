# Zephyr RTOS Platform

> One-line summary: Zephyr version detection, CMake module integration, Kconfig symbols, and TLS credential subsystem gotchas for wolfSSL.

**When to read**: integrating wolfSSL as a Zephyr west module, debugging build or credential issues, or replacing mbedTLS with wolfSSL in a Zephyr project.

---

## Core Define

| Define | Purpose |
|--------|---------|
| `WOLFSSL_ZEPHYR` | Enables all Zephyr-specific adaptations (headers, memory, threading) |

## Kernel Version Detection

wolfSSL auto-detects the Zephyr kernel version at compile time:

- **Zephyr >= 3.1.0**: uses namespaced headers (`<zephyr/kernel.h>`, `<zephyr/sys/printk.h>`)
- **Zephyr < 3.1.0**: uses legacy headers (`<kernel.h>`, `<sys/printk.h>`)

Detection uses `__has_include(<zephyr/version.h>)`. If your toolchain lacks `__has_include` support, wolfSSL falls back to `<version.h>` directly.

## West Module Integration

wolfSSL integrates as a west external module. Application `west.yml` must reference it:

```yaml
- name: wolfssl
  path: modules/crypto/wolfssl
  url: https://github.com/wolfSSL/wolfssl
```

wolfSSL provides `zephyr/module.yml`, `zephyr/Kconfig`, and `zephyr/CMakeLists.txt` in the wolfSSL source tree.

## Critical Kconfig Symbols

| Symbol | Purpose |
|--------|---------|
| `CONFIG_WOLFSSL=y` | Enable wolfSSL module |
| `CONFIG_MBEDTLS=n` | **Must disable** -- both cannot be active simultaneously |
| `CONFIG_TLS_CREDENTIALS=y` | Enable TLS credential store |
| `CONFIG_NET_SOCKETS_TLS=y` | TLS socket layer |
| `CONFIG_TLS_MAX_CREDENTIALS_NUMBER` | Credential pool size (default 4 -- often too low) |
| `CONFIG_ENTROPY_GENERATOR=y` | Required for wolfSSL RNG |
| `CONFIG_MAIN_STACK_SIZE` | Increase to 8-16 KB for TLS handshakes |
| `CONFIG_TEST_RANDOM_GENERATOR=y` | Dev-only fallback if no HW RNG on board |

## TLS Credential Subsystem

Zephyr's `tls_credentials` API is **mbedTLS-aware by default**. wolfSSL must:

1. Retrieve credentials via `tls_credential_get()` or internal `credential_get()` (declared in `tls_internal.h` -- not a public header)
2. Load into wolfSSL context via `wolfSSL_CTX_load_verify_buffer()`, `*_use_certificate_buffer()`, `*_use_PrivateKey_buffer()`
3. Consume credential buffers immediately -- volatile backend stores raw pointers, not copies

The wolfSSL module's CMake may need to add `subsys/net/lib/tls_credentials` to include directories for `tls_internal.h` access.

## C++ Compatibility

When `WOLFSSL_ZEPHYR` is defined with C++, wolfSSL automatically closes the `extern "C"` block before including Zephyr headers. Handled in `settings.h`.

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| Duplicate symbol conflicts at link time | Both `CONFIG_MBEDTLS` and `CONFIG_WOLFSSL` enabled | Set `CONFIG_MBEDTLS=n` explicitly |
| `tls_credential_add()` returns `-ENOMEM` | Credential pool exhausted | Increase `CONFIG_TLS_MAX_CREDENTIALS_NUMBER` |
| Header not found: `<zephyr/kernel.h>` | `WOLFSSL_ZEPHYR` not defined, or version.h not accessible | Verify define is set in build |
| Hard fault during TLS handshake | Thread stack too small | Increase `CONFIG_MAIN_STACK_SIZE` or thread stack to 8-16 KB |
| RNG failure | No entropy source configured | Set `CONFIG_ENTROPY_GENERATOR=y` with HW entropy driver |
| `tls_credentials_digest_raw.c` compile failure | PSA SHA-256 not bridged when wolfSSL is crypto provider | Enable `CONFIG_PSA_WANT_ALG_SHA_256` + `CONFIG_BASE64` |
| Module not found at build | `west update` not run after `west.yml` change | Run `west update`; verify `ZEPHYR_WOLFSSL_MODULE_DIR` |

## What This File Does NOT Cover

Zephyr installation, west tool usage, board-specific configuration. See `embedded-common.md` for cross-platform patterns (stack sizing, RNG, certificate loading).
