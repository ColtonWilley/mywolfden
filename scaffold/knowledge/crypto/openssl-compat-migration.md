# OpenSSL Compatibility Layer & Migration

> One-line summary: migration decision tree, OPENSSL_EXTRA vs OPENSSL_ALL scope, API mapping pitfalls, and application-specific compat macros.

**When to read**: Migrating an application from OpenSSL/mbedTLS/BoringSSL to wolfSSL, debugging compat layer build errors, or modifying code in `src/ssl.c` near `#ifdef OPENSSL_EXTRA` blocks.

---

## Migration Decision Tree

1. **Check for existing shims first** — wolfSSL maintains compat branches and the `osp/` directory on GitHub with patches for common applications. For large migrations, this saves weeks.
2. **OpenSSL compat layer** — If migrating from an OpenSSL-API-compatible library (including BoringSSL), use `--enable-opensslextra` / `--enable-opensslall`.
3. **Direct API mapping** — For small projects (<50 call sites), map directly to wolfCrypt/wolfSSL native APIs.

**Rule of thumb**: For 100+ call-site migrations, always recommend a shim or compat layer first.

## OPENSSL_EXTRA vs OPENSSL_ALL Scope

| Feature Area | `--enable-opensslextra` (`OPENSSL_EXTRA`) | `--enable-opensslall` (`OPENSSL_ALL`) |
|-------------|:-:|:-:|
| `SSL_*` / `wolfSSL_*` core TLS API | Yes | Yes |
| `EVP_*` (digest, cipher, pkey) | Partial | Fuller |
| `BIO` layer | Basic | Full |
| `X509` functions | Most common | Extended |
| `SSL_CTX_set_options()` | Most options (some no-ops) | More options |
| App-specific compat (`--enable-nginx`, etc.) | No | No (separate flags) |

## Application-Specific Compat Macros

Beyond `OPENSSL_EXTRA`, wolfSSL defines per-application macros that **modify API return values and behavior**:

| Flag | Macro | Effect |
|------|-------|--------|
| `--enable-nginx` | `WOLFSSL_NGINX` | Changes cipher name format, certificate handling |
| `--enable-qt` | `WOLFSSL_QT` | IANA vs internal cipher names in `wolfSSL_CIPHER_get_name()` |
| `--enable-haproxy` | `WOLFSSL_HAPROXY` | HAProxy-specific behavior |
| `--enable-apache-httpd` | `WOLFSSL_APACHE_HTTPD` | mod_ssl compatibility |
| `--enable-openvpn` | `EXTERNAL_OPTS_OPENVPN` | OpenVPN-specific compat |
| `--enable-curl` | — | curl backend compat |
| `--enable-stunnel` | `WOLFSSL_STUNNEL` | Requires threading enabled |

**Warning**: These macros gate `#ifdef` blocks in `src/ssl.c` that change function behavior. When refactoring `ssl.c`, preserve all application-compat guards within modified `#ifdef` blocks.

## Dual Code Paths Pattern

Many wolfSSL API functions have two implementations:

- **Native path** (default): Direct wolfSSL implementation
- **OpenSSL-compat path** (`#ifdef OPENSSL_EXTRA`): Integrates with compat structures (`X509_VERIFY_PARAM`, BIO layer, etc.)

Locations with dual paths:
- `src/ssl.c` — Public API with `#ifdef OPENSSL_EXTRA` blocks
- `src/internal.c` — `ProcessPeerCerts()` has separate verify logic per path
- `wolfssl/ssl.h` — API declarations may differ under `OPENSSL_EXTRA`

When adding a new public API function, check if the closest existing analog has dual paths. If so, your function likely needs both.

## Common Migration Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| `undefined reference to SSL_X` | Function needs `--enable-opensslall` not just `--enable-opensslextra` | Try `--enable-opensslall` or check if function exists under different name |
| System OpenSSL headers included instead of wolfSSL's | Wrong include path | Use `#include <wolfssl/openssl/ssl.h>` not `<openssl/ssl.h>` |
| `options.h` not included first | Autoconf build requires it | `#include <wolfssl/options.h>` must be first include |
| Linking fails — `libssl` not found | wolfSSL installs `libwolfssl`, not `libssl`/`libcrypto` | Use `pkg-config wolfssl --libs` |
| Error codes don't match | wolfSSL error codes != OpenSSL `ERR_*` codes | Map errors through `wolfSSL_ERR_error_string()` |
| `SSL_read`/`SSL_write` partial write differs | Behavioral difference from OpenSSL | Check return values carefully |

## mbedTLS Migration Quick Reference

wolfSSL provides a compat shim — check GitHub for mbedTLS compat branches.

| mbedTLS API | wolfSSL Equivalent |
|------------|-------------------|
| `mbedtls_ssl_*` | `wolfSSL_*` |
| `mbedtls_pk_*` | `wolfSSL_CTX_use_PrivateKey_*` / `_certificate_*` |
| `mbedtls_md_*` | `wc_Hash*` / `wc_Sha256*` |
| `mbedtls_cipher_*` | `wc_Aes*` / `wc_Des3*` |
| `mbedtls_entropy_*` / `mbedtls_ctr_drbg_*` | `wc_InitRng` / `wc_RNG_GenerateBlock` |

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| Cipher name mismatch at runtime | App-compat macro (`WOLFSSL_QT` etc.) changes name format | `ssl.c` `wolfSSL_CIPHER_get_name()` |
| Verify callback not called | `OPENSSL_EXTRA` not defined — native verify path taken instead | `internal.c` `ProcessPeerCerts()` |
| EVP function returns unsupported | Algorithm not enabled at configure time | Check `--enable-*` flags |
| Refactor broke nginx but not curl | Removed `#ifdef WOLFSSL_NGINX` guard during cleanup | `src/ssl.c` app-compat guards |

## What This File Does NOT Cover

- Generic OpenSSL API documentation
- History of OpenSSL or BoringSSL
- Vendor documentation links (go stale)
- Performance comparisons between wolfSSL and OpenSSL
