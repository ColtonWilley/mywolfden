---
paths:
  - "repos/osp/**/openvpn/**"
---

# OpenVPN — External Platform Summary

## Current State

- **Active development branch:** 2.8 (development cycle started; changelog notes formal pre-release not yet tagged as of source snapshot)
- **Last stable series:** 2.6.x / 2.7.x (community downloads at https://openvpn.net/community-downloads/)
- **License:** GPL v2
- **Crypto backend selection:** Compile-time via `--with-crypto-library=` (`openssl`, `mbedtls`). wolfSSL is consumed through the OpenSSL compatibility layer (`--with-crypto-library=openssl` pointing to wolfSSL headers/libs).
- **Build system:** Autoconf/Automake (`configure.ac` + `version.m4`); CMake path available for Windows (see `README.cmake.md`).
- **PKCS#11 support:** Available as a separate configure option; uses `pkcs11-helper` library, not direct PKCS#11 calls from OpenVPN itself.

---

## Architecture

### Crypto Backend Abstraction

OpenVPN separates crypto concerns into two independent backend layers:

| Layer | Purpose | Backend files |
|---|---|---|
| **Data channel crypto** | Symmetric encryption/decryption of tunnel packets (AES-GCM, ChaCha20-Poly1305, HMAC) | `src/openvpn/crypto_openssl.c` / `crypto_mbedtls.c` |
| **Control channel TLS** | TLS handshake, certificate validation, key exchange | `src/openvpn/ssl_openssl.c` / `ssl_mbedtls.c` |

Both layers implement a common abstract interface defined in:
- `src/openvpn/crypto_backend.h` — symmetric crypto ops
- `src/openvpn/ssl_backend.h` — TLS context and session ops

The compile-time guard is `ENABLE_CRYPTO_OPENSSL` (set when `--with-crypto-library=openssl`).

### TLS Context Lifecycle (ssl_openssl.c)

```
tls_init_lib()
  └─ SSL_get_ex_new_index()          # registers per-SSL session pointer slot

tls_ctx_server_new() / tls_ctx_client_new()
  └─ SSL_CTX_new_ex(tls_libctx, ...)  # uses global OSSL_LIB_CTX* tls_libctx

[certificate/key loading]
[verify callbacks]

SSL handshake per tunnel session
```

- **`tls_libctx`** is a global `OSSL_LIB_CTX *` used for all `SSL_CTX_new_ex()` calls. This is the OpenSSL 3.x provider context. wolfSSL's compatibility layer must satisfy `SSL_CTX_new_ex` with a valid lib context argument or handle `NULL` gracefully.
- `SSLv23_server_method()` / `SSLv23_client_method()` are used — these are the version-flexible methods (equivalent to `TLS_method()` in OpenSSL 1.1+). wolfSSL compat must map these.

### OpenSSL 3.x Provider / Store API Usage

```c
#if OPENSSL_VERSION_NUMBER >= 0x30000000L
#define HAVE_OPENSSL_STORE_API
#include <openssl/ui.h>
#include <openssl/store.h>
#include <openssl/provider.h>
#include <openssl/core_names.h>
#endif
```

When wolfSSL reports `OPENSSL_VERSION_NUMBER >= 0x30000000L`, OpenVPN activates the OpenSSL 3 provider/store code paths. wolfSSL's compat layer must implement or stub:
- `OSSL_LIB_CTX` / `SSL_CTX_new_ex`
- `OSSL_STORE_*` APIs (for URI-based cert/key loading)
- `OSSL_PROVIDER_*` APIs
- `OSSL_PARAM` / `OSSL_CORE_NAMES_*`

### Engine API (Legacy)

```c
#if HAVE_OPENSSL_ENGINE
#include <openssl/engine.h>
// ENGINE_by_id("dynamic"), ENGINE_ctrl_cmd_string(), ENGINE_init(), etc.
#endif
```

Engine support is conditional on `HAVE_OPENSSL_ENGINE`. If wolfSSL compat does not implement the ENGINE API, ensure `HAVE_OPENSSL_ENGINE` is not defined during the build.

### External Key (xkey) Provider

`src/openvpn/xkey_common.h` and `xkey_provider.c` implement an OpenSSL 3-style custom provider for external/hardware private keys (used with `--management-external-key` and PKCS#11 flows). This uses:
- `OSSL_PROVIDER` registration
- `EVP_PKEY` with custom key operations
- Relevant to wolfSSL when hardware key offload is needed

### Certificate Chain Handling

OpenVPN loads certificate chains via:
- `SSL_CTX_use_certificate_chain_file()` — PEM file with leaf + intermediates
- `SSL_CTX_add_extra_chain_cert()` — individual intermediate addition
- `X509_STORE` / `SSL_CTX_set_verify()` for CA trust store

wolfSSL compat must correctly handle multi-certificate PEM files in `SSL_CTX_use_certificate_chain_file` and propagate the full chain during TLS handshake.

### PKCS#11 Integration Path

OpenVPN uses `pkcs11-helper` as an abstraction over PKCS#11 tokens. The flow is:
```
OpenVPN --pkcs11-providers / --pkcs11-id
  └─ pkcs11-helper library
       └─ PKCS#11 module (.so / .dll)
```
OpenVPN itself does not call PKCS#11 C_* functions directly. wolfSSL PKCS#11 integration at the OpenVPN level means ensuring the `pkcs11-helper` library can use wolfSSL's OpenSSL compat for any crypto it delegates upward, or using wolfSSL's native PKCS#11 support at the library level independently.

---

## wolfSSL Integration Notes

### Build Configuration

```bash
# Point OpenVPN to wolfSSL's OpenSSL compatibility headers and library
./configure \
  --with-crypto-library=openssl \
  CPPFLAGS="-I/path/to/wolfssl/include -I/path/to/wolfssl/include/wolfssl" \
  LDFLAGS="-L/path/to/wolfssl/lib" \
  LIBS="-lwolfssl"
```

wolfSSL must be built with:
```bash
./configure --enable-opensslall --enable-opensslextra --enable-des3 \
            --enable-pkcs11 --enable-certgen --enable-keygen \
            --enable-tls13 --enable-dtls
```

### Version Number Collision (`OPENSSL_VERSION_NUMBER`)

**Critical issue:** If wolfSSL's compat header defines `OPENSSL_VERSION_NUMBER >= 0x30000000L`, OpenVPN enables OpenSSL 3 code paths (`HAVE_OPENSSL_STORE_API`, provider APIs, `SSL_CTX_new_ex` with `OSSL_LIB_CTX`). wolfSSL must implement:
- `SSL_CTX_new_ex(OSSL_LIB_CTX *libctx, const char *propq, const SSL_METHOD *method)` — at minimum accept and ignore `libctx`/`propq` parameters
- `OSSL_LIB_CTX` type (can be opaque/typedef'd to void)

If wolfSSL reports a version number below `0x30000000L`, these paths are skipped and the integration is simpler, but verify that `SSLv23_server_method` / `SSLv23_client_method` are defined in the compat layer.

### `SSL_get_ex_new_index` / `SSL_set_ex_data` / `SSL_get_ex_data`

OpenVPN stores a `struct tls_session *` pointer in each SSL object using the ex_data mechanism:
```c
mydata_index = SSL_get_ex_new_index(0, "struct session *", NULL, NULL, NULL);
// later:
SSL_set_ex_data(ssl, mydata_index, session);
SSL_get_ex_data(ssl, mydata_index)
```
wolfSSL compat must implement the full `SSL_get_ex_new_index` / `SSL_set_ex_data` / `SSL_get_ex_data` API. Failure here causes NULL pointer dereferences in verify callbacks.

### Certificate Chain Loading

`SSL_CTX_use_certificate_chain_file()` must:
1. Load the leaf certificate as the primary cert
2. Load all subsequent PEM blocks as extra chain certs via `SSL_CTX_add_extra_chain_cert()`

wolfSSL's implementation must not stop at the first certificate in the PEM file. Verify with a 3-level chain (leaf + intermediate + root).

### EVP Cipher/Digest API (Data Channel)

`crypto_openssl.c` uses:
- `EVP_CIPHER_CTX_new()` / `EVP_EncryptInit_ex()` / `EVP_DecryptInit_ex()`
- `EVP_aes_256_gcm()`, `EVP_aes_128_gcm()`, `EVP_chacha20_poly1305()`
- `EVP_MD_CTX_new()` / `EVP_DigestInit_ex()` for HMAC/hash
- `HMAC_CTX_new()` / `HMAC_Init_ex()`
- `EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, ...)` — GCM IV length control
- `EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, ...)` / `EVP_CTRL_GCM_SET_TAG`

wolfSSL must implement `EVP_CTRL_GCM_*` ctrl codes. Missing GCM tag handling is a common failure point.

### KDF (HKDF / TLS PRF)

```c
#if !defined(LIBRESSL_VERSION_NUMBER)
#include <openssl/kdf.h>
#endif
```

OpenVPN uses `EVP_PKEY_CTX` KDF operations for TLS key material derivation. wolfSSL compat must implement `EVP_PKEY_CTX_new_id(EVP_PKEY_HKDF, ...)` and associated `EVP_PKEY_CTX_set_hkdf_*` functions, or the `EVP_KDF` API if the OpenSSL 3 path is active.

### ENGINE API

If `HAVE_OPENSSL_ENGINE` is detected, OpenVPN calls:
- `ENGINE_by_id()`, `ENGINE_ctrl_cmd_string()`, `ENGINE_init()`, `ENGINE_set_default()`, `ENGINE_free()`

wolfSSL does not implement the ENGINE API. Ensure `HAVE_OPENSSL_ENGINE` is not set (pass `--disable-openssl-engine` if the configure script supports it, or ensure wolfSSL headers do not define `OPENSSL_HAS_ECC_ENGINE` / related guards that trigger engine detection).

### PKCS#11 with wolfSSL

wolfSSL's native PKCS#11 support (`--enable-pkcs11`) operates at the wolfSSL internal layer, not through the OpenSSL ENGINE API. For OpenVPN's `pkcs11-helper`-based flow, wolfSSL is transparent — `pkcs11-helper` handles token interaction and presents keys/certs to OpenVPN via the OpenSSL compat API (`EVP_PKEY`, `X509`). Ensure wolfSSL compat correctly handles `EVP_PKEY` objects created externally and passed into `SSL_CTX_use_PrivateKey()`.

### Common Failure Modes

| Symptom | Likely Cause |
|---|---|
| `SSL_CTX_new` returns NULL | `SSLv23_server/client_method()` not implemented or `SSL_CTX_new_ex` signature mismatch |
| Segfault in TLS verify callback | `SSL_get_ex_data(ssl, mydata_index)` returns NULL — ex_data not implemented |
| Handshake fails with cert error | `SSL_CTX_use_certificate_chain_file` drops intermediate certs |
| GCM decryption failures | `EVP_CTRL_GCM_SET_TAG` / `EVP_CTRL_GCM_GET_TAG` not implemented |
| Build fails on `OSSL_LIB_CTX` | wolfSSL version number ≥ 0x30000000 but `SSL_CTX_new_ex` not in compat layer |
| Build fails on `ENGINE_*` | wolfSSL headers trigger `HAVE_OPENSSL_ENGINE` — stub or disable |
| PKCS#11 token not found | `pkcs11-helper` built against system OpenSSL, not wolfSSL — ABI mismatch |

---

## Key Files

| File | Role |
|---|---|
| `configure.ac` | Build system; `--with-crypto-library=openssl` selects OpenSSL backend; sets `ENABLE_CRYPTO_OPENSSL`; detects `HAVE_OPENSSL_ENGINE` |
| `src/openvpn/ssl_openssl.c` | Control channel TLS backend — `SSL_CTX` lifecycle, cert/key loading, verify callbacks, xkey provider registration |
| `src/openvpn/crypto_openssl.c` | Data channel crypto backend — EVP cipher/digest/HMAC, engine setup, KDF |
| `src/openvpn/ssl_backend.h` | Abstract TLS backend interface implemented by `ssl_openssl.c` |
| `src/openvpn/crypto_backend.h` | Abstract crypto backend interface implemented by `crypto_openssl.c` |
| `src/openvpn/openssl_compat.h` | Shims for OpenSSL API version differences (1.0.x → 1.1.x → 3.x); review for wolfSSL compat gaps |
| `src/openvpn/xkey_common.h` / `xkey_provider.c` | External key provider (OpenSSL 3 custom provider); used for hardware/PKCS#11 private keys |
| `src/openvpn/ssl_verify_openssl.c` | X.509 certificate verification logic; uses `X509_*`, `X509_STORE_*`, `X509_NAME_*` APIs |
| `src/openvpn/pkcs11.c` / `pkcs11_backend_openssl.c` | PKCS#11 integration via `pkcs11-helper`; OpenSSL compat used for cert/key object handling |
| `src/openvpn/ssl.h` | OpenVPN protocol description and TLS session state structures |
| `sample/sample-keys/` | Test certificates — use for initial integration smoke testing only |
