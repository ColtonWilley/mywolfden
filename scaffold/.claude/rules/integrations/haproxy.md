---
paths:
  - "repos/osp/**/haproxy/**"
---

# HAProxy — External Platform Summary

## Current State

- **Latest stable branch**: 3.x series; as of the source material, **3.4-dev6** is the current development snapshot (2026/03/05). Production deployments typically use 3.2 or 3.0 LTS.
- HAProxy is actively maintained with frequent releases. The CHANGELOG shows continuous SSL/TLS-related fixes and cleanups.
- wolfSSL is an explicitly supported TLS backend via `USE_OPENSSL_WOLFSSL=1` in the Makefile build system.
- CI pipelines cover multiple TLS backends (AWS-LC, standard OpenSSL); wolfSSL is not in the listed CI badges but is a documented build option.

---

## Architecture

### Process/Thread Model
- HAProxy uses a **multi-process + multi-thread** model. Each worker process runs multiple threads (configured via `nbthread`). All TLS operations occur within these worker threads.
- Thread safety is critical: OpenSSL-compatible locking callbacks must be functional. wolfSSL must be built with thread safety enabled (`--enable-opensslextra --enable-threadlocal` or equivalent).

### TLS Integration Layer
- All TLS logic is abstracted behind an **OpenSSL-compatible API layer**. HAProxy does not have a native wolfSSL code path — it uses wolfSSL's OpenSSL compatibility layer exclusively.
- The central TLS source file is `src/ssl_sock.c`. It includes OpenSSL headers only via `include/haproxy/openssl-compat.h` (never directly). This indirection is where wolfSSL headers must be substituted.
- Key subsystems:
  - **`ssl_sock.c`**: Core TLS handshake, session management, certificate loading, SNI dispatch, verify callbacks.
  - **`ssl_ckch.c` / `ssl_crtlist.c`**: Certificate and key store management (ckch = cert/key/chain).
  - **`ssl_ocsp.c`**: OCSP stapling implementation.
  - **`ssl_gencert.c`**: Dynamic certificate generation (used for SSL bumping/interception).
  - **`shctx.c`**: Shared SSL session cache across processes using shared memory.
  - **`quic_ssl.c` / `quic_openssl_compat.c`**: QUIC TLS integration (separate from standard TLS path).

### Certificate Handling
- Certificates are loaded at startup and managed in a tree structure (ebtree). Dynamic cert loading/replacement is supported via CLI (`set ssl cert`).
- SNI-based certificate selection uses `SSL_CTX_set_tlsext_servername_callback` — must be functional in wolfSSL compat layer.
- Certificate chains, DH params, and ECDH curves are configured per bind/server context.

### OCSP
- OCSP stapling is implemented in `ssl_ocsp.c`. HAProxy fetches and caches OCSP responses, stapling them via `SSL_CTX_set_tlsext_status_cb` / `SSL_set_tlsext_status_ocsp_resp`.
- A background task periodically refreshes OCSP responses. This requires wolfSSL OCSP stapling support to be compiled in (`--enable-ocsp`).

---

## wolfSSL Integration Notes

### Build System
- Enable with: `make USE_OPENSSL_WOLFSSL=1`
- The Makefile sets `USE_OPENSSL=1` implicitly and routes include/library paths to wolfSSL. Verify `SSL_INC` and `SSL_LIB` point to the wolfSSL installation.
- wolfSSL must be built with `--enable-opensslextra --enable-opensslall` (or at minimum the subset of APIs HAProxy uses). Missing compat symbols will cause link errors.
- Recommended wolfSSL configure flags for HAProxy:
  ```
  --enable-opensslextra --enable-opensslall --enable-ocsp --enable-ocspstapling
  --enable-sni --enable-tlsv10 --enable-session-certs --enable-keying-material
  ```

### Header Compatibility
- **Do not** add `#include <openssl/xxx.h>` directly in HAProxy source. All OpenSSL includes go through `include/haproxy/openssl-compat.h`. wolfSSL's `<wolfssl/openssl/ssl.h>` and related headers must be mapped there.
- The comment in `ssl_sock.c` and `ssl_sock-t.h` explicitly warns: *"do NOT include openssl/xxx.h here, do it in openssl-compat.h"*. This is the single point to patch for wolfSSL header paths.

### API Compatibility Issues (Common)
| HAProxy Feature | Required wolfSSL API | Notes |
|---|---|---|
| SNI dispatch | `SSL_CTX_set_tlsext_servername_callback` | Must be enabled in wolfSSL build |
| OCSP stapling | `SSL_CTX_set_tlsext_status_cb`, `SSL_set_tlsext_status_ocsp_resp` | Requires `--enable-ocsp` |
| Session resumption (shared cache) | `SSL_CTX_sess_set_new_cb`, `SSL_CTX_set_session_id_context` | Shared memory cache (`shctx`) may need verification |
| Dynamic cert generation | `X509_*`, `EVP_PKEY_*`, `RSA_generate_key_ex` | `ssl_gencert.c` uses extensive X.509 APIs |
| Client cert verification | `SSL_CTX_set_verify`, `X509_STORE_*` | Verify callback stores error codes in connection state |
| Cipher/curve configuration | `SSL_CTX_set_cipher_list`, `SSL_CTX_set1_curves_list` | Named curve support must be compiled in |
| TLS 1.3 | `SSL_CTX_set_ciphersuites` | wolfSSL TLS 1.3 must be enabled |
| Engine support | `ENGINE_*` | `USE_ENGINE=1` — not applicable with wolfSSL; do not combine |
| QUIC | `quic_openssl_compat.c` | `USE_QUIC_OPENSSL_COMPAT=1` path; wolfSSL QUIC API compatibility is limited |

### Multi-Threading
- HAProxy calls `CRYPTO_set_locking_callback` / `CRYPTO_set_id_callback` (OpenSSL 1.0.x style) or relies on OpenSSL 1.1+ built-in thread safety. wolfSSL must handle these correctly or stub them safely.
- Each thread creates its own `SSL` objects from shared `SSL_CTX`. wolfSSL's `SSL_CTX` must be thread-safe for concurrent `SSL_new()` calls.
- The shared session cache (`shctx`) uses HAProxy's own spinlocks around session callbacks — verify wolfSSL session callback invocation is compatible.

### QUIC Considerations
- `USE_QUIC_OPENSSL_COMPAT=1` enables a QUIC path using standard OpenSSL APIs (limited features). wolfSSL QUIC support via this path is untested in mainline. Avoid combining `USE_QUIC` (requires quictls/BoringSSL QUIC API) with wolfSSL.

### Known Friction Points
1. **`SSL_CTX_set_alpn_select_cb`** — required for HTTP/2; verify wolfSSL compat.
2. **`SSL_get_peer_cert_chain`** vs `SSL_get_peer_certificate`** — HAProxy uses both; wolfSSL compat layer behavior may differ on chain depth.
3. **`SSL_CTX_set_keylog_callback`** — used for debug/SSLKEYLOGFILE; may be absent in wolfSSL builds without `--enable-keylog-export`.
4. **`X509_get_ext_d2i` for SAN/CN extraction** — used in certificate verification and logging; requires full X.509 extension support.
5. **`SSL_SESSION` serialization** — used in the shared cache; wolfSSL's session serialization format differs from OpenSSL's `i2d_SSL_SESSION`/`d2i_SSL_SESSION`.

---

## Key Files

| File | Purpose |
|---|---|
| `Makefile` | Build entry point; `USE_OPENSSL_WOLFSSL=1` flag defined here; controls `SSL_INC`/`SSL_LIB` paths |
| `include/haproxy/openssl-compat.h` | **Primary header shim** — all OpenSSL/wolfSSL includes and API compatibility macros go here |
| `src/ssl_sock.c` | Core TLS socket layer: handshake, SNI, verify callbacks, session management |
| `include/haproxy/ssl_sock-t.h` | TLS connection state types and flag definitions |
| `src/ssl_ckch.c` | Certificate/key/chain store; dynamic cert CLI operations |
| `src/ssl_crtlist.c` | Certificate list management for SNI-based dispatch |
| `src/ssl_ocsp.c` | OCSP stapling fetch, cache, and stapling callbacks |
| `src/ssl_gencert.c` | Dynamic X.509 certificate generation (SSL interception) |
| `src/shctx.c` | Shared SSL session cache (cross-process, shared memory) |
| `src/ssl_utils.c` | Utility functions: cipher name lookup, cert info extraction |
| `src/quic_ssl.c` | QUIC TLS integration (quictls API path) |
| `src/quic_openssl_compat.c` | QUIC compatibility layer for standard OpenSSL API |
| `doc/configuration.txt` | Reference for `ssl-*` bind/server directives, `tune.ssl.*` globals |
