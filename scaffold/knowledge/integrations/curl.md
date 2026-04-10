# curl + wolfSSL Integration

> One-line summary: how curl's vtls backend maps to wolfSSL APIs, and what breaks when wolfSSL is misconfigured.

**When to read**: Building curl with wolfSSL as TLS backend, debugging TLS failures in curl+wolfSSL, or working on the vtls wolfSSL backend code.

---

## vtls Backend Architecture

curl uses a backend-agnostic TLS abstraction in `lib/vtls/`. Each backend implements a `Curl_ssl` vtable. Only one TLS backend is active per build (limited exceptions for QUIC). TLS is implemented as a connection filter (`Curl_cfilter`) layer stacked over transport.

| File | Role |
|------|------|
| `lib/vtls/wolfssl.c` | Primary wolfSSL backend implementation |
| `lib/vtls/wolfssl.h` | wolfSSL backend header |
| `lib/vtls/vtls.c` | Generic TLS dispatch; session cache management |
| `m4/curl-wolfssl.m4` | Autotools detection macro for wolfSSL |
| `CMake/FindWolfSSL.cmake` | CMake wolfSSL detection module |

## Build Flags and Defines

**wolfSSL side**: `./configure --enable-curl` (sets `HAVE_CURL`, enables required OpenSSL compat surface)

**curl side (autotools)**: `./configure --with-wolfssl[=PATH]`
**curl side (CMake)**: `cmake -DCURL_USE_WOLFSSL=ON -DWOLFSSL_ROOT=<path> ..`

| Compile-time define (in curl) | Purpose |
|------|---------|
| `USE_WOLFSSL` | Enables wolfSSL backend in libcurl |
| `HAVE_WOLFSSL_USEALPN` | Enables ALPN support (requires wolfSSL `--enable-alpn`) |

## wolfSSL API Usage in wolfssl.c

Key wolfSSL APIs called by the curl backend:

| API | Purpose |
|-----|---------|
| `wolfSSL_CTX_new()` / `wolfSSL_CTX_free()` | Context lifecycle |
| `wolfSSL_new()` / `wolfSSL_free()` | Per-connection SSL object |
| `wolfSSL_UseSNI()` | SNI hostname injection |
| `wolfSSL_UseALPN()` | ALPN protocol list |
| `wolfSSL_connect()` | Handshake initiation |
| `wolfSSL_get_peer_certificate()` | Peer cert for verification |
| `wolfSSL_get1_session()` / `wolfSSL_set_session()` | Session resumption |
| `wolfSSL_CTX_load_verify_locations()` | CA certificate loading |
| `wolfSSL_CTX_use_certificate_file()` / `wolfSSL_CTX_use_PrivateKey_file()` | Client cert/key |

## Session Resumption

Sessions are stored as `WOLFSSL_SESSION*` objects in curl's generic session cache (keyed on hostname + port + TLS version). Cache is shared across easy handles within the same multi handle. Uses `wolfSSL_get1_session()` to save and `wolfSSL_set_session()` to restore.

**Gotcha**: Session resumption silently fails if wolfSSL lacks session cache support -- no error returned, but a full handshake happens every time.

## ALPN / SNI Behavior

- ALPN uses `wolfSSL_UseALPN()`, required for HTTP/2 (`h2`). Without it, curl falls back to HTTP/1.1 silently.
- SNI uses `wolfSSL_UseSNI()`, sent automatically for HTTPS unless hostname is an IP address.
- **Debug check**: `curl -v --http2 https://example.com` -- look for `ALPN: offers h2`; absence means ALPN not compiled in.

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| `configure` fails to find wolfSSL | pkg-config dir mismatch | `m4/curl-wolfssl.m4` (fixed in curl 8.19.1) |
| ALPN not negotiated, HTTP/2 silently downgrades | wolfSSL built without `--enable-alpn` | Check `HAVE_WOLFSSL_USEALPN` in `curl_config.h` |
| Certificate verification failure | CA bundle path not set; wolfSSL does not use system CA store by default | `wolfSSL_CTX_load_verify_locations()` -- set `CURLOPT_CAINFO`/`CURLOPT_CAPATH`, or build wolfSSL with `--enable-sys-ca-certs` |
| TLS handshake errors with TLS 1.3 | wolfSSL missing `--enable-tls13` or cipher mismatch | Check cipher list with `CURLOPT_TLS13_CIPHERS` |
| Session resumption not working | wolfSSL session cache disabled | Rebuild wolfSSL with session cache; check `wolfSSL_CTX_set_session_cache_mode()` |
| `wolfSSL_CTX_load_verify_locations` fails | Wrong CA file format or relative path | Ensure PEM format; use absolute paths |
| Mutual TLS (client cert) failures | Key/cert format mismatch | wolfSSL requires PEM or DER; verify `CURLOPT_SSLCERT` and `CURLOPT_SSLKEY` types match |

## Diagnostic Checklist

1. Confirm `USE_WOLFSSL` defined in generated `curl_config.h`
2. Confirm `HAVE_WOLFSSL_USEALPN` present if HTTP/2 needed
3. `curl --version` should show `wolfssl` in SSL backend line
4. `curl -v` to inspect SNI, ALPN, and cert verification steps
5. `wolfssl-config --cflags` or inspect `options.h` in wolfSSL install to verify build flags

## What This File Does NOT Cover

- General curl usage or libcurl programming
- curl installation procedures
- Non-wolfSSL TLS backends (OpenSSL, GnuTLS, etc.)
- QUIC/HTTP3 integration specifics
