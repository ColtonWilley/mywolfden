---
paths:
  - "repos/osp/**/stunnel/**"
---

# stunnel — External Platform Summary

## Current State

- **Latest version**: 5.77 (as of configure.ac `AC_INIT([stunnel],[5.77])`)
- **Copyright**: 1998–2025, Michal Trojnara
- **License**: GPL v2+, with a special exception permitting linking against OpenSSL-licensed libraries
- **Purpose**: TLS offloading/load-balancing proxy; wraps non-TLS-aware services (POP2/3, IMAP, etc.) with TLS without modifying the underlying application
- **Build system**: Autoconf/Automake (`configure.ac`, generated `configure` script)
- **Threading models**: ucontext, pthread, fork — selectable at configure time

---

## Architecture

### TLS/Crypto Layer
stunnel uses the **OpenSSL API** throughout. All TLS context setup, certificate handling, CRL/OCSP, and session management are implemented against OpenSSL's public API. wolfSSL integrates by providing an OpenSSL compatibility layer (`--enable-opensslextra`, `--enable-opensslall`).

### Key source modules relevant to TLS integration:

| File | Role |
|------|------|
| `src/ssl.c` | Global OpenSSL initialization: entropy, compression, engine setup, `SSL_CTX` ex_data callbacks |
| `src/ctx.c` | Per-service `SSL_CTX` construction: certificate loading, DH/ECDH params, SNI callbacks, CRL/OCSP configuration |
| `src/client.c` | TLS handshake execution per connection (client mode) |
| `src/server.c` | TLS handshake execution per connection (server mode) |
| `src/prototypes.h` | Central header; controls compile-time feature flags |

### Version-gated API usage
`src/ssl.c` and `src/ctx.c` contain extensive `#if OPENSSL_VERSION_NUMBER` guards:
- `>= 0x10100000L` — OpenSSL 1.1.0+ API paths (new-style init, ex_data signatures)
- `>= 0x10101000L` — OpenSSL 1.1.1+ paths (TLS 1.3, passphrase caching changes)
- `>= 0x30000000L` — OpenSSL 3.x paths (provider model, `CRYPTO_EX_DATA` signature changes)

wolfSSL's `OPENSSL_VERSION_NUMBER` define must match a supported branch to select correct code paths. Mismatches here are a common source of build failures.

### DH Parameters
`src/ctx.c` conditionally compiles DH support under `#ifndef OPENSSL_NO_DH`. On OpenSSL ≥ 1.1.1, DH params can be loaded from a URI via a store (`dh_load_from_store`); on older versions, `dh_read()` is used. wolfSSL must expose `OPENSSL_NO_DH` or implement the relevant DH store APIs accordingly.

### SNI
SNI callback (`servername_cb`) is compiled under `#ifndef OPENSSL_NO_TLSEXT`. wolfSSL must define `SSL_CTRL_SET_TLSEXT_HOSTNAME` and related compat macros, or `OPENSSL_NO_TLSEXT` must be defined to disable the path.

---

## wolfSSL Integration Notes

### Build System
- stunnel uses `./configure` with `--with-ssl=<path>` to point to an OpenSSL-compatible library directory
- To use wolfSSL: build wolfSSL with `--enable-opensslall --enable-opensslextra --enable-stunnel` (wolfSSL ships a dedicated `--enable-stunnel` configure flag that activates required compat APIs)
- Ensure wolfSSL's include path provides `openssl/ssl.h`, `openssl/crypto.h`, `openssl/x509v3.h`, etc.
- Set `CFLAGS` and `LDFLAGS` to point to wolfSSL's include/lib directories before running stunnel's `configure`

### API Compatibility Requirements
wolfSSL must implement or stub the following for stunnel to build and function:

| API Area | Specific Requirements |
|----------|-----------------------|
| `SSL_CTX` lifecycle | `SSL_CTX_new`, `SSL_CTX_free`, `SSL_CTX_set_options` |
| Certificate loading | `SSL_CTX_use_certificate_file`, `SSL_CTX_use_PrivateKey_file`, `SSL_CTX_load_verify_locations` |
| CRL | `X509_STORE_set_flags(X509_V_FLAG_CRL_CHECK)`, `X509_STORE_add_crl`, `X509_STORE_CTX` |
| OCSP | `SSL_CTX_set_tlsext_status_cb`, `OCSP_*` APIs if stapling is enabled |
| DH | `DH_new`, `SSL_CTX_set_tmp_dh` (or `SSL_CTX_set_dh_auto`) — or define `OPENSSL_NO_DH` |
| SNI | `SSL_CTX_set_tlsext_servername_callback` — or define `OPENSSL_NO_TLSEXT` |
| ex_data | `SSL_get_ex_new_index`, `SSL_get_ex_data`, `SSL_set_ex_data` with correct callback signatures for the targeted version number |
| Entropy | `RAND_*` APIs used in `ssl.c` initialization |

### Certificate Verification
- stunnel calls `SSL_CTX_set_verify` with `SSL_VERIFY_PEER` and custom verify callbacks
- CRL checking is enabled via `X509_STORE_set_flags` with `X509_V_FLAG_CRL_CHECK` and/or `X509_V_FLAG_CRL_CHECK_ALL`
- wolfSSL CRL must be enabled at build time: `--enable-crl`
- OCSP stapling requires `--enable-ocsp` and `--enable-ocspstapling` in wolfSSL

### Common Integration Issues

1. **`OPENSSL_VERSION_NUMBER` mismatch**: wolfSSL reports a version number that selects an incompatible code path in `ctx.c`/`ssl.c`. Check which branch stunnel's `#if` guards select and verify wolfSSL implements those exact API signatures (especially `CRYPTO_EX_DATA` dup/free callback signatures differ between 1.1.x and 3.x).

2. **`cb_dup_addr` / `cb_free_addr` signature mismatch**: `ssl.c` has three distinct signatures for `cb_dup_addr` gated on version number. wolfSSL's reported `OPENSSL_VERSION_NUMBER` must match the signature wolfSSL actually implements.

3. **Missing `OPENSSL_NO_*` guards**: If wolfSSL does not implement DH store URI loading or SNI extensions, the corresponding `OPENSSL_NO_DH` / `OPENSSL_NO_TLSEXT` macros must be defined to exclude those code paths.

4. **Passphrase/PEM handling**: `ctx.c` uses `PEM_BUFSIZE` and a `PW_CB_DATA` struct for passphrase callbacks. Verify wolfSSL's `PEM_BUFSIZE` definition and `pem_password_cb` signature match.

5. **Threading model interaction**: stunnel's ucontext/pthread/fork model affects how OpenSSL locking callbacks are set up. wolfSSL's threading layer must be compatible; use `--enable-singlethreaded` only if stunnel is built with fork mode.

6. **OCSP/CRL at runtime**: Failures often appear as `X509_V_ERR_*` codes in verify callbacks. Enable wolfSSL debug logging (`--enable-debug`) and stunnel `debug = 7` simultaneously to correlate errors.

---

## Key Files

| File | Purpose |
|------|---------|
| `configure.ac` | Autoconf input; version declaration (5.77), SSL library detection, thread model selection |
| `src/ssl.c` | Global TLS library init; ex_data index registration; entropy setup |
| `src/ctx.c` | Per-service `SSL_CTX` construction; certificate/key loading; DH/ECDH; SNI; CRL/OCSP hooks |
| `src/prototypes.h` | Master header; all feature-flag `#define`s and struct declarations |
| `src/client.c` | Client-side handshake and post-handshake verification |
| `src/server.c` | Server-side handshake |
| `src/config.h` | Autoconf-generated; contains `USE_PTHREAD`, `USE_UCONTEXT`, etc. |
| `INSTALL.W32.md` | Windows build notes (relevant for wolfSSL Windows integration) |
| `INSTALL.FIPS.md` | FIPS build notes (relevant if using wolfSSL FIPS-validated build) |

### Configuration Points (stunnel.conf)
| Directive | TLS Relevance |
|-----------|--------------|
| `cert` / `key` | Certificate and private key paths → `SSL_CTX_use_certificate_file` |
| `CAfile` / `CApath` | Trust anchor → `SSL_CTX_load_verify_locations` |
| `CRLfile` / `CRLpath` | CRL sources → `X509_STORE_add_crl` / `X509_STORE_set_flags` |
| `verify` | Verification depth/mode → `SSL_CTX_set_verify` |
| `OCSPaia` | OCSP via AIA extension → requires wolfSSL OCSP support |
| `sslVersion` / `sslVersionMin/Max` | Protocol version constraints → `SSL_CTX_set_min_proto_version` |
| `ciphers` | Cipher suite string → `SSL_CTX_set_cipher_list` |
| `debug` | Log verbosity; set to `7` for full TLS debug output |
