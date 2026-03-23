---
paths:
  - "repos/osp/**/curl/**"
  - "**/vtls/wolfssl*"
---

# curl — External Platform Summary

## Current State

- **Latest release:** curl/libcurl 8.19.1 (release 274)
- **License:** MIT-like (curl license)
- **Repository:** https://github.com/curl/curl
- **Supported TLS backends:** wolfSSL, OpenSSL/BoringSSL/LibreSSL, GnuTLS, mbedTLS, Rustls, Schannel (Windows), Secure Transport (Apple), BearSSL
- **Relevant recent fix:** `curl-wolfssl.m4: fix to use the correct value for pkg-config directory` (8.19.1 release)
- **Planned removals:** TLS-SRP support, NTLM (opt-in), RTMP, SMB (opt-in) — no wolfSSL-specific deprecations noted

---

## Architecture

### TLS Abstraction Layer (`lib/vtls/`)

curl uses a backend-agnostic TLS abstraction. All TLS backends implement a common `Curl_ssl` vtable interface. The active backend is selected at build time; only one TLS backend is active per build (with limited exceptions for QUIC).

**Backend files present in `lib/vtls/`:**
| File | Backend |
|------|---------|
| `wolfssl.c` / `wolfssl.h` | wolfSSL |
| `openssl.c` / `openssl.h` | OpenSSL / BoringSSL / LibreSSL |
| `gtls.c` / `gtls.h` | GnuTLS |
| `mbedtls.c` / `mbedtls.h` | mbedTLS |
| `rustls.c` / `rustls.h` | Rustls |
| `schannel.c` / `schannel.h` | Windows Schannel |
| `apple.c` / `apple.h` | Apple Secure Transport |
| `cipher_suite.c` / `cipher_suite.h` | Shared cipher name/IANA mapping (mbedTLS, Rustls) |
| `hostcheck.c` / `hostcheck.h` | Hostname verification helpers |
| `keylog.c` / `keylog.h` | TLS key logging (SSLKEYLOGFILE) |

**Note:** `wolfssl.c` is not shown in the directory listing provided but is the primary integration file referenced throughout curl's build system and documentation.

### Connection Filter Architecture

curl uses a connection filter (`Curl_cfilter`) model. TLS is implemented as a filter layer stacked over the transport. This means:
- TLS connect/disconnect is handled via filter `connect`/`close` callbacks
- Session data and SSL state are stored per-filter instance
- ALPN negotiation and SNI are set during filter initialization before the handshake

### Session Resumption

Session resumption is managed through `lib/vtls/vtls.c` using a session cache keyed on hostname, port, and TLS parameters. The wolfSSL backend stores and retrieves `WOLFSSL_SESSION` objects through this cache. The cache is shared across easy handles within the same multi handle.

---

## wolfSSL Integration Notes

### Build System

**Autotools:**
```sh
./configure --with-wolfssl[=PATH]
```
- Detection logic is in `curl-wolfssl.m4` (in the `m4/` directory)
- **Known fix in 8.19.1:** `curl-wolfssl.m4` was corrected to use the proper value for the pkg-config directory — ensure you are on 8.19.1+ if using pkg-config-based wolfSSL detection
- Sets `USE_WOLFSSL` preprocessor define
- Links against `-lwolfssl`

**CMake:**
```cmake
cmake -DCURL_USE_WOLFSSL=ON -DWOLFSSL_ROOT=<path> ..
```
- CMake module: `CMake/FindWolfSSL.cmake`
- Sets `CURL_USE_WOLFSSL` cache variable

### Compile-Time Defines

| Define | Purpose |
|--------|---------|
| `USE_WOLFSSL` | Enables wolfSSL backend in libcurl |
| `HAVE_WOLFSSL_USEALPN` | Enables ALPN support (requires wolfSSL built with ALPN) |
| `WOLFSSL_ALLOW_SSLV3` | Required if SSLv3 compatibility is needed (not recommended) |

### ALPN Support

- Controlled by `HAVE_WOLFSSL_USEALPN` at compile time
- Uses `wolfSSL_UseALPN()` API
- ALPN is required for HTTP/2 (`h2`) negotiation — if ALPN is absent, curl falls back to HTTP/1.1 even when HTTP/2 is requested
- wolfSSL must be built with `--enable-alpn` (default in most builds)
- **Debug check:** Run `curl -v --http2 https://example.com` and look for `ALPN: offers h2` in verbose output; absence indicates ALPN is not compiled in

### SNI Support

- SNI is set via `wolfSSL_UseSNI()` during SSL context setup in `wolfssl.c`
- SNI is sent automatically for HTTPS connections unless `CURLOPT_SSL_VERIFYHOST` is disabled or the hostname is an IP address
- wolfSSL must be built with `--enable-sni` (default)

### Session Resumption

- wolfSSL backend participates in curl's generic session cache
- Sessions are stored as `WOLFSSL_SESSION*` objects
- `wolfSSL_get1_session()` / `wolfSSL_set_session()` are used for save/restore
- Session resumption requires the same hostname, port, and TLS version to match cache key
- **Common issue:** Session resumption silently fails if wolfSSL is built without session cache support (`--enable-sessioncerts` or similar); no error is returned, but a full handshake occurs every time

### Common Integration Issues

| Issue | Cause | Resolution |
|-------|-------|------------|
| `configure` fails to find wolfSSL | pkg-config dir mismatch | Upgrade to curl 8.19.1+; verify `wolfssl.pc` is in the expected prefix |
| ALPN not negotiated | wolfSSL built without `--enable-alpn` | Rebuild wolfSSL with ALPN; verify `HAVE_WOLFSSL_USEALPN` is set in `curl_config.h` |
| Certificate verification failure | CA bundle path not set | Set `CURLOPT_CAINFO` or `CURLOPT_CAPATH`; wolfSSL does not use the system CA store by default unless built with `--enable-sys-ca-certs` |
| TLS handshake errors with TLS 1.3 | wolfSSL version mismatch or missing cipher | Verify wolfSSL is built with `--enable-tls13`; check cipher list with `CURLOPT_TLS13_CIPHERS` |
| Session resumption not working | wolfSSL session cache disabled | Rebuild wolfSSL with session cache enabled; check `wolfSSL_CTX_set_session_cache_mode()` |
| `wolfSSL_CTX_load_verify_locations` fails | Wrong CA file format or path | Ensure PEM format; use absolute paths |
| Mutual TLS (client cert) failures | Key/cert format mismatch | wolfSSL requires PEM or DER; verify `CURLOPT_SSLCERT` and `CURLOPT_SSLKEY` types match |

### wolfSSL-Specific API Usage in `wolfssl.c`

Key wolfSSL APIs called by curl's wolfSSL backend:
- `wolfSSL_CTX_new()` / `wolfSSL_CTX_free()` — context lifecycle
- `wolfSSL_new()` / `wolfSSL_free()` — per-connection SSL object
- `wolfSSL_UseSNI()` — SNI hostname injection
- `wolfSSL_UseALPN()` — ALPN protocol list
- `wolfSSL_connect()` — handshake initiation
- `wolfSSL_get_peer_certificate()` — peer cert retrieval for verification
- `wolfSSL_get1_session()` / `wolfSSL_set_session()` — session resumption
- `wolfSSL_CTX_load_verify_locations()` — CA certificate loading
- `wolfSSL_CTX_use_certificate_file()` / `wolfSSL_CTX_use_PrivateKey_file()` — client cert/key

---

## Key Files

| File | Purpose |
|------|---------|
| `lib/vtls/wolfssl.c` | Primary wolfSSL TLS backend implementation |
| `lib/vtls/wolfssl.h` | wolfSSL backend header |
| `lib/vtls/vtls.c` | Generic TLS dispatch layer; session cache management |
| `lib/vtls/vtls.h` | TLS abstraction interface definitions |
| `m4/curl-wolfssl.m4` | Autotools detection macro for wolfSSL (fixed in 8.19.1) |
| `CMake/FindWolfSSL.cmake` | CMake wolfSSL detection module |
| `configure.ac` | Top-level autotools configure; `--with-wolfssl` option defined here |
| `CMakeLists.txt` | Top-level CMake build; `CURL_USE_WOLFSSL` option |
| `include/curl/curl.h` | Public API; `CURLOPT_SSL*` option definitions |
| `lib/urldata.h` | Internal connection/session data structures including SSL state |
| `curl_config.h` (generated) | Build-time feature flags; check for `USE_WOLFSSL`, `HAVE_WOLFSSL_USEALPN` |

### Diagnostic Checklist for wolfSSL Integration

1. Confirm `USE_WOLFSSL` is defined in the generated `curl_config.h`
2. Confirm `HAVE_WOLFSSL_USEALPN` is present if HTTP/2 is required
3. Run `curl --version` and verify `wolfssl` appears in the SSL backend line
4. Use `curl -v` to inspect SNI, ALPN, and certificate verification steps
5. Check wolfSSL build flags with `wolfssl-config --cflags` or inspect `options.h` in the wolfSSL install
