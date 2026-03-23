---
paths:
  - "**/zephyr*/**"
---

# Zephyr RTOS — External Platform Summary

## Current State

- **Active project**: Zephyr is a scalable, security-focused RTOS maintained by the Linux Foundation under the Zephyr Project. Source at `github.com/zephyrproject-rtos/zephyr`.
- **Supported architectures**: ARM (Cortex-A/R/M), x86, ARC, Xtensa, RISC-V, SPARC, MIPS, and others.
- **TLS backend model**: Zephyr uses a Kconfig-selectable TLS credentials backend system. The default/primary backend is `CONFIG_TLS_CREDENTIALS_BACKEND_VOLATILE` (in-memory). A protected storage backend (`CONFIG_TLS_CREDENTIALS_BACKEND_PROTECTED_STORAGE`) is available for TF-M-enabled builds.
- **Build system**: CMake + west (west is the meta-tool for workspace and module management). wolfSSL integrates as a west module.
- **TLS library selection**: Zephyr's networking stack is designed around mbedTLS as the primary TLS library. wolfSSL integration requires explicit configuration to replace or supplement this.

---

## Architecture

### Networking Stack
- Zephyr's network stack (`subsys/net/`) is layered: L2 drivers → IP stack → socket API → TLS socket layer.
- TLS is exposed via BSD-like socket API with `SO_SEC_TAG_LIST`, `TLS_PEER_VERIFY`, and related socket options.
- The `net_app` API (older, largely superseded by direct socket API) provided higher-level TLS credential attachment; current code uses `tls_credentials` API directly.

### TLS Credentials Subsystem (`subsys/net/lib/tls_credentials/`)
- Provides a **global credential store** shared across all TLS contexts.
- Credentials are identified by `sec_tag_t` (integer tag) and `enum tls_credential_type` (CA cert, server cert, private key, PSK, PSK identity).
- Pool size controlled by `CONFIG_TLS_MAX_CREDENTIALS_NUMBER` (Kconfig integer, default typically 4).
- **Volatile backend** (`tls_credentials.c`): stores raw pointers/lengths in a static array; credentials must remain valid for the lifetime of use.
- **Protected storage backend** (`tls_credentials_trusted.c`): uses PSA Protected Storage API; requires TF-M.
- Credential digest uses PSA SHA-256 + base64 (`tls_credentials_digest_raw.c`); requires `CONFIG_PSA_WANT_ALG_SHA_256` and `CONFIG_BASE64`.
- Internal mutex (`k_mutex`) protects the credential array; initialized at `POST_KERNEL` via `SYS_INIT`.

### Kconfig TLS Backend Selection
- `CONFIG_TLS_CREDENTIALS_BACKEND_VOLATILE` — default, in-RAM storage.
- `CONFIG_TLS_CREDENTIALS_BACKEND_PROTECTED_STORAGE` — PSA PS-backed, TF-M required.
- `CONFIG_MBEDTLS` — enables mbedTLS; the `tls_credentials` CMakeLists links `mbedTLS` library when this is set.
- wolfSSL does **not** have a corresponding `zephyr_library_link_libraries_ifdef` entry in the upstream `tls_credentials/CMakeLists.txt`; this linkage must be handled in the wolfSSL module's own CMake or application `CMakeLists.txt`.

---

## wolfSSL Integration Notes

### Build System
- wolfSSL integrates as a **west external module**. The `west.yml` manifest in the application workspace must reference the wolfSSL module:
  ```yaml
  - name: wolfssl
    path: modules/crypto/wolfssl
    url: https://github.com/wolfSSL/wolfssl
  ```
- Zephyr's module system picks up `zephyr/module.yml` from the wolfSSL repo, which registers CMake and Kconfig fragments.
- wolfSSL provides its own `Kconfig` and `CMakeLists.txt` under `zephyr/` in the wolfSSL source tree. These must be present and correct for the module to build.
- `CONFIG_WOLFSSL=y` enables the wolfSSL module. Ensure it does not conflict with `CONFIG_MBEDTLS=y` — both should not be enabled simultaneously for the same TLS socket path.

### TLS Credentials API Integration
- The upstream `tls_credentials` subsystem is **mbedTLS-aware** (explicit `zephyr_library_link_libraries_ifdef(CONFIG_MBEDTLS mbedTLS)`). wolfSSL must hook into credential retrieval separately.
- wolfSSL's Zephyr port must call `credential_get()` / `credential_next_get()` (internal API in `tls_internal.h`) or the public `tls_credential_get()` to retrieve certs/keys by `sec_tag_t` and load them into wolfSSL contexts (`wolfSSL_CTX_load_verify_buffer`, `wolfSSL_CTX_use_certificate_buffer`, `wolfSSL_CTX_use_PrivateKey_buffer`).
- Credential buffers in the volatile backend are **raw pointers** — they are not copied. wolfSSL must consume them before the application frees or modifies the buffer.
- `CONFIG_TLS_MAX_CREDENTIALS_NUMBER` must be set high enough to hold all certs, keys, and PSK entries used by the application. Default is often too low (4) for multi-connection scenarios.

### Common Issues
1. **`CONFIG_MBEDTLS` and `CONFIG_WOLFSSL` both enabled**: Causes duplicate symbol conflicts. Explicitly set `CONFIG_MBEDTLS=n` when using wolfSSL.
2. **Missing `tls_internal.h` access**: `credential_get()` and `credential_next_get()` are declared in `tls_internal.h` (not a public header). wolfSSL's Zephyr glue code must include this via a relative path or the wolfSSL module must add `subsys/net/lib/tls_credentials` to its include directories.
3. **Credential pool exhaustion**: Symptoms are `tls_credential_add()` returning `-ENOMEM`. Increase `CONFIG_TLS_MAX_CREDENTIALS_NUMBER`.
4. **Digest/PSA dependency**: `tls_credentials_digest_raw.c` requires `CONFIG_PSA_WANT_ALG_SHA_256` + `CONFIG_BASE64`. If wolfSSL is the crypto provider and PSA is not bridged, this will fail to compile or return `-ENOTSUP` at runtime.
5. **Stack size**: wolfSSL TLS handshakes require significant stack. `CONFIG_MAIN_STACK_SIZE` and thread stack sizes often need to be 8–16 KB minimum. Symptoms are hard faults or stack overflow panics during handshake.
6. **Entropy source**: wolfSSL requires `CONFIG_ENTROPY_GENERATOR=y` and a hardware entropy driver. On boards without hardware RNG, `CONFIG_TEST_RANDOM_GENERATOR=y` can be used for development only.
7. **west module not found at build**: Confirm `west update` has been run after modifying `west.yml`. Check that `ZEPHYR_WOLFSSL_MODULE_DIR` is set or discoverable.
8. **Protected storage backend + wolfSSL**: The `tls_credentials_trusted.c` backend is only compiled when `CONFIG_TLS_CREDENTIALS_BACKEND_PROTECTED_STORAGE=y` and requires TF-M. wolfSSL's PSA bridge must be enabled (`WOLFSSL_HAVE_PSA`) for this path to function.

### API Flow (Typical TLS Client)
```
tls_credential_add(tag, TLS_CREDENTIAL_CA_CERTIFICATE, buf, len)
  → stored in credentials[] array (volatile backend)

socket(AF_INET, SOCK_STREAM, IPPROTO_TLS_1_2)
setsockopt(fd, SOL_TLS, TLS_SEC_TAG_LIST, &tag, sizeof(tag))
  → wolfSSL glue retrieves credential via credential_get(tag, ...)
  → loads into WOLFSSL_CTX via *_buffer() APIs

connect(fd, ...)  → triggers TLS handshake
```

---

## Key Files

| File/Path | Purpose |
|---|---|
| `subsys/net/lib/tls_credentials/tls_credentials.c` | Volatile credential store implementation; `credential_get()`, `credential_next_get()`, `credential_next_tag_get()` |
| `subsys/net/lib/tls_credentials/tls_internal.h` | Internal credential struct and function declarations; required by wolfSSL glue code |
| `subsys/net/lib/tls_credentials/Kconfig` | Defines `CONFIG_TLS_CREDENTIALS_BACKEND_VOLATILE`, `CONFIG_TLS_CREDENTIALS_BACKEND_PROTECTED_STORAGE`, `CONFIG_TLS_MAX_CREDENTIALS_NUMBER` |
| `subsys/net/lib/tls_credentials/CMakeLists.txt` | Conditionally compiles backends; links mbedTLS — wolfSSL linkage must be added externally |
| `subsys/net/lib/tls_credentials/tls_credentials_digest_raw.c` | SHA-256/base64 digest for raw credentials; PSA-dependent |
| `modules/crypto/wolfssl/zephyr/Kconfig` | wolfSSL module Kconfig (in wolfSSL repo); defines `CONFIG_WOLFSSL` and feature flags |
| `modules/crypto/wolfssl/zephyr/CMakeLists.txt` | wolfSSL module build rules; must add include path for `tls_internal.h` if needed |
| `west.yml` (application workspace) | West manifest; must declare wolfSSL as a module for it to be included in the build |
| `prj.conf` (application) | Primary Kconfig configuration; set `CONFIG_WOLFSSL=y`, `CONFIG_MBEDTLS=n`, `CONFIG_TLS_CREDENTIALS=y`, `CONFIG_NET_SOCKETS_TLS=y` |
