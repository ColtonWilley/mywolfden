---
paths:
  - "repos/osp/**/nginx/**"
  - "**/ngx_*"
---

# nginx — External Platform Summary

## Current State

nginx is an actively developed, production-stable web server, reverse proxy, load balancer, and API gateway distributed under a 2-clause BSD license. It is available in two tracks:

- **Stable**: Critical fixes only, backported from mainline
- **Mainline**: Latest features and bugfixes (built from `master`)

Enterprise support and distributions are provided by F5, Inc. The project is actively maintained with regular releases. wolfSSL integration is supported via the wolfSSL OpenSSL compatibility layer.

---

## Architecture

### Process Model
- **Master process**: Reads/evaluates configuration, manages worker lifecycle
- **Worker processes**: Handle all I/O including TLS handshakes; count is configurable or auto-set to CPU core count
- Workers share data via shared memory zones (relevant for session cache sharing across workers)

### Module System
- Modules are compiled as **static** (build-time) or **dynamic** (runtime-loaded)
- TLS functionality lives in the `ngx_http_ssl_module` and the underlying `ngx_event_openssl` layer
- Build-time module inclusion is controlled via `./configure` flags; `nginx -V` shows compiled-in modules

### TLS/Crypto Layer (`src/event/ngx_event_openssl.c`)
nginx's entire TLS stack is abstracted through OpenSSL API calls in this single file. Key functional areas:

| Area | Relevant Functions/Macros |
|---|---|
| Session caching | `ngx_ssl_new_session`, `ngx_ssl_get_cached_session`, `ngx_ssl_remove_session`, `ngx_ssl_expire_sessions` |
| Session tickets | `ngx_ssl_ticket_key_callback`, `ngx_ssl_rotate_ticket_keys` — guarded by `#ifdef SSL_CTRL_SET_TLSEXT_TICKET_KEY_CB` |
| OCSP stapling | Separate callback path within the same file |
| TLS 1.3 / Early Data | `ngx_ssl_try_early_data`, `ngx_ssl_recv_early`, `ngx_ssl_write_early` — guarded by `#ifdef SSL_READ_EARLY_DATA_SUCCESS` |
| Handshake | `ngx_ssl_handshake_handler` |
| Verify callback | `ngx_ssl_verify_callback` |
| Info callback | `ngx_ssl_info_callback` |

Session cache is implemented as a **red-black tree in shared memory** (`ngx_ssl_session_rbtree_insert_value`), shared across all worker processes.

---

## wolfSSL Integration Notes

### Build System
nginx uses a custom `auto/` configure script system. OpenSSL library detection and linking is handled by:
- `auto/lib/openssl/conf` — detection logic
- `auto/lib/openssl/make` — build rules
- `auto/lib/openssl/makefile.msvc` / `makefile.bcc` — Windows variants

To substitute wolfSSL, use the `--with-wolfssl` configure flag (requires wolfSSL built with `--enable-nginx` or equivalent OpenSSL compatibility options):

```bash
./configure --with-wolfssl=/path/to/wolfssl --with-http_ssl_module
make
```

wolfSSL must be compiled with its OpenSSL compatibility layer enabled. Recommended wolfSSL build flags:
```bash
./configure --enable-opensslextra --enable-nginx \
            --enable-ocsp --enable-ocspstapling \
            --enable-session-ticket --enable-tls13
```

### API Compatibility Points

| nginx Feature | OpenSSL API Used | wolfSSL Notes |
|---|---|---|
| Session tickets | `SSL_CTRL_SET_TLSEXT_TICKET_KEY_CB` / `HMAC_CTX` / `EVP_CIPHER_CTX` | Requires `--enable-session-ticket`; `HMAC_CTX` compat must be present |
| TLS 1.3 early data | `SSL_READ_EARLY_DATA_SUCCESS` define | wolfSSL TLS 1.3 early data support must be enabled; define must be exposed via compat header |
| OCSP stapling | `X509_STORE_CTX`, OCSP callback APIs | Requires `--enable-ocsp --enable-ocspstapling` |
| Session ID context | `OPENSSL_VERSION_NUMBER >= 0x10100003L` conditional | wolfSSL compat layer should expose matching version number or the `const` qualifier on `ngx_ssl_get_cached_session` may mismatch |
| Cert compression (zlib) | `TLSEXT_cert_compression_zlib` | Not typically needed; guarded by `#ifdef` |

### Common Issues

1. **`SSL_CTRL_SET_TLSEXT_TICKET_KEY_CB` not defined**: Session ticket callback won't compile. Ensure wolfSSL exposes this define in its OpenSSL compat headers (`wolfssl/openssl/ssl.h`).

2. **`SSL_READ_EARLY_DATA_SUCCESS` missing**: TLS 1.3 early data path is compiled out. If nginx is expected to handle 0-RTT, verify wolfSSL exposes this define.

3. **`HMAC_CTX` / `EVP_CIPHER_CTX` API mismatches**: The ticket key callback uses both directly. wolfSSL's compat implementations of these structs/functions must match the expected OpenSSL 1.1.x API signatures (heap-allocated opaque structs with `_new`/`_free`).

4. **`OPENSSL_VERSION_NUMBER` version gating**: nginx uses `>= 0x10100003L` to select `const u_char *id` in the session lookup callback. wolfSSL's reported version number must be set appropriately in the compat layer to match the expected signature.

5. **Shared memory session cache**: nginx manages its own session cache in shared memory and calls `SSL_CTX_sess_set_new_cb` / `SSL_CTX_sess_set_get_cb` / `SSL_CTX_sess_set_remove_cb`. wolfSSL must support these callbacks correctly; conflicts with wolfSSL's internal session cache can cause double-free or missed resumptions. Consider disabling wolfSSL's internal cache (`SSL_CTX_set_session_cache_mode(SSL_SESS_CACHE_OFF)`).

6. **Worker process fork safety**: TLS contexts are initialized in the master process and inherited by workers. wolfSSL's internal state (e.g., RNG, mutex initialization) must be fork-safe or re-initialized post-fork.

7. **`nginx -V` output**: After building, verify `--with-wolfssl=...` appears in the configure arguments to confirm the correct library was linked.

---

## Key Files

| File/Path | Purpose |
|---|---|
| `src/event/ngx_event_openssl.c` | **Primary TLS integration file** — all OpenSSL API calls for handshake, session management, tickets, OCSP, early data |
| `src/event/ngx_event_openssl.h` | TLS type definitions (`ngx_ssl_t`, `ngx_ssl_conn_t`, session types) |
| `src/event/ngx_event_openssl_stapling.c` | OCSP stapling implementation |
| `auto/lib/openssl/conf` | Build-time OpenSSL/wolfSSL detection logic — first place to check if library is not found |
| `auto/lib/openssl/make` | Linker flags and include path injection for OpenSSL/wolfSSL |
| `auto/options` | Defines `--with-wolfssl` option handling |
| `conf/nginx.conf` | Runtime TLS directives: `ssl_certificate`, `ssl_session_cache`, `ssl_session_tickets`, `ssl_stapling` |
| `src/http/modules/ngx_http_ssl_module.c` | HTTP SSL module — maps nginx config directives to `ngx_ssl_t` API calls |

### Key nginx.conf TLS Directives for wolfSSL Testing

```nginx
ssl_protocols       TLSv1.2 TLSv1.3;
ssl_session_cache   shared:SSL:10m;
ssl_session_tickets on;
ssl_stapling        on;
ssl_stapling_verify on;
```
