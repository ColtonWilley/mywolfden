---
paths:
  - "**/openssl/**"
  - "**/compatibility*"
  - "**/opensslextra*"
  - "**/src/ssl.c"
  - "**/src/internal.c"
  - "**/wolfssl/ssl.h"
  - "**/wolfssl/internal.h"
  - "**/src/x509.c"
---

# OpenSSL Compatibility Layer

## Overview
wolfSSL provides an OpenSSL-compatible API layer enabling drop-in replacement for many OpenSSL applications.
- Enable: `--enable-opensslextra` (common subset) or `--enable-opensslall` (fuller compatibility)
- Headers: `wolfssl/openssl/ssl.h` provides `SSL_*` → `wolfSSL_*` mappings via macros
- Define `OPENSSL_EXTRA` or `OPENSSL_ALL` in user_settings.h for IDE builds

## Migration Strategy

### Choosing the Right Path
For any library replacement project, evaluate these approaches in order:

1. **Compatibility shim branches**: wolfSSL maintains library-specific compat branches and the `osp/` directory on GitHub with patches for common applications. For large migrations, always check GitHub for existing shims first — they can save weeks of work.
2. **OpenSSL compat layer**: If migrating from a library that is itself OpenSSL-API-compatible (or close to it), the `--enable-opensslextra` / `--enable-opensslall` path may be the fastest route. This gives you `SSL_*`, `EVP_*`, `BIO_*` compatibility.
3. **Direct API mapping**: For small projects (under ~50 call sites), mapping directly to wolfCrypt/wolfSSL native APIs is clean and maintainable.

**Rule of thumb**: For 100+ call-site migrations, always recommend a shim or compatibility layer first, with manual API mapping as a supplement for anything the shim doesn't cover.

### Key Resources
- wolfSSL GitHub `osp/` directory — application patches and compatibility shims
- wolfSSL blog (wolfssl.com/blog) — migration guides and walkthroughs
- wolfSSL porting guide in the manual — platform-level porting instructions

## Migrating from Other TLS Libraries

### mbedTLS / Mbed TLS
wolfSSL provides a **compatibility shim** for mbedTLS migration on GitHub. Check the wolfSSL GitHub repository for mbedTLS compat branches. wolfSSL has also published migration blog posts covering the transition.

Key API mappings:
- `mbedtls_ssl_*` → `wolfSSL_*` (TLS operations)
- `mbedtls_pk_*` → `wolfSSL_CTX_use_PrivateKey_*` / `wolfSSL_CTX_use_certificate_*`
- `mbedtls_md_*` → `wc_Hash*` / `wc_Sha256*` (hashing)
- `mbedtls_cipher_*` → `wc_Aes*` / `wc_Des3*` (symmetric crypto)
- `mbedtls_entropy_*` / `mbedtls_ctr_drbg_*` → `wc_InitRng` / `wc_RNG_GenerateBlock`

wolfSSL replaces mbedTLS on Mbed OS — see `living/external-mbed-os.md` for that platform integration.

### BoringSSL
BoringSSL is a Google fork of OpenSSL. The **OpenSSL compat layer** (`--enable-opensslextra` or `--enable-opensslall`) is the primary migration path. Most BoringSSL-based applications use OpenSSL-compatible APIs. See also the Android platform guide for Android-specific BoringSSL replacement.

### GnuTLS
No dedicated compatibility shim exists for GnuTLS. Options:
- **OpenSSL compat layer**: If the application also supports OpenSSL, use `--enable-opensslextra`.
- **Native API mapping**: Map GnuTLS functions to wolfSSL equivalents (`gnutls_init` → `wolfSSL_new`, `gnutls_handshake` → `wolfSSL_connect`/`wolfSSL_accept`, etc.).

## Common Migration Issues

### Missing API Functions
**Symptom**: "undefined reference to `SSL_X`" or "implicit declaration"
**Triage**:
1. Is the function implemented? Search in `src/ssl.c` or `wolfcrypt/src/`
2. Which compat level? Some functions need `--enable-opensslall` not just `--enable-opensslextra`
3. Check: function may exist under a different name or need an extra enable flag
4. Some OpenSSL functions have no wolfSSL equivalent — check compatibility docs

### API Behavioral Differences
- `SSL_CTX_set_options()`: most options supported but some are no-ops
- `SSL_read()` / `SSL_write()`: partial write behavior may differ
- Error codes: wolfSSL error codes don't map 1:1 to OpenSSL ERR_* codes
- `BIO` layer: basic BIO support available with `--enable-opensslextra`, full BIO with `--enable-opensslall`
- `EVP` interface: available with `--enable-opensslextra` but not all algorithms implemented
- `X509` functions: most common functions supported, some return types differ

### Compile-Time Compatibility
```c
#include <wolfssl/options.h>       // Must be first (if using autoconf build)
#include <wolfssl/openssl/ssl.h>   // OpenSSL compat headers
#include <wolfssl/openssl/err.h>
#include <wolfssl/openssl/evp.h>
```
**Common mistake**: Including system OpenSSL headers instead of wolfSSL's openssl/ headers.

### Linking
- wolfSSL installs `libwolfssl` not `libssl`/`libcrypto`
- Use `pkg-config wolfssl --libs` for correct linking
- Some build systems need `-DEXTERNAL_OPTS_OPENVPN` or similar for specific app compatibility

## Application-Specific Compat Notes

### nginx
- Requires `--enable-nginx` (enables specific compat functions nginx needs)
- Or use `--enable-opensslall --enable-nginx`

### curl
- Requires `--enable-curl` or specific compat flag set
- curl 7.80+ has improved wolfSSL backend

### OpenVPN
- Requires `--enable-openvpn` for OpenVPN-specific compat
- Data channel offload may need additional flags

### stunnel
- Requires `--enable-stunnel`
- Needs threading support enabled

### Apache httpd
- Requires `--enable-apache-httpd`
- mod_ssl compatibility layer

## EVP Interface
The `EVP_*` functions provide a high-level crypto interface:
- `EVP_DigestInit()` / `EVP_DigestUpdate()` / `EVP_DigestFinal()` — hashing
- `EVP_EncryptInit()` / `EVP_EncryptUpdate()` / `EVP_EncryptFinal()` — symmetric
- `EVP_PKEY_*` — asymmetric operations
- Not all algorithms available through EVP — check what's enabled

## Application-Specific Behavior Modifiers

Beyond `OPENSSL_EXTRA`, wolfSSL defines per-application compat macros that
modify API return values and behavior:

- `WOLFSSL_QT`, `WOLFSSL_NGINX`, `WOLFSSL_HAPROXY`, `WOLFSSL_APACHE_HTTPD`
- These are enabled by `--enable-qt`, `--enable-nginx`, etc.
- They gate `#ifdef` blocks in `src/ssl.c` that change function behavior —
  e.g., `wolfSSL_CIPHER_get_name()` returns IANA names by default but
  internal/OpenSSL-style names when `WOLFSSL_QT` is defined

When modifying cipher name resolution, certificate handling, or error
behavior in `ssl.c`, check for application-compat `#ifdef` guards that
may fork the code path. These guards interact with `WOLFSSL_CIPHER_INTERNALNAME`
and `NO_ERROR_STRINGS`. A refactor that removes or restructures an `#ifdef`
block in `ssl.c` must preserve all application-compat guards within it.

## Dual Code Paths in Core Files

Many wolfSSL public API functions have two implementations or code paths:

- **Native path** (default): Direct wolfSSL implementation using internal
  structures and functions.
- **OpenSSL-compat path** (`#ifdef OPENSSL_EXTRA`): Delegates to or
  integrates with OpenSSL-compatible structures (`X509_VERIFY_PARAM`,
  `SSL_CTX` extensions, BIO layer, etc.).

When adding a new public API function, check whether the closest existing
analog has dual paths. If it does, your new function likely needs both:
- The native implementation for non-OPENSSL_EXTRA builds
- The OPENSSL_EXTRA path that wires into the compat infrastructure

Common locations for dual paths:
- `src/ssl.c` — Public API functions often have `#ifdef OPENSSL_EXTRA`
  blocks that set verify params, store data in compat structs, or call
  compat helper functions.
- `src/internal.c` — Certificate verification in `ProcessPeerCerts()` has
  separate verification logic gated on `#ifndef OPENSSL_EXTRA` (native)
  vs `#ifdef OPENSSL_EXTRA` (compat verify-param path).
- `wolfssl/ssl.h` — API declarations may have different signatures or
  additional overloads under OPENSSL_EXTRA.

## External Resources
- **wolfSSL blog** (wolfssl.com/blog): Migration guides, performance comparisons, integration walkthroughs
- **wolfSSL GitHub `osp/` directory**: Application-specific patches and compatibility shims for nginx, Apache, stunnel, OpenVPN, and others
- **wolfSSL porting guide** (in the manual): Platform-level porting instructions for custom RTOS/OS environments
- **wolfSSL examples repo** (`wolfssl-examples` on GitHub): Working code samples for TLS, DTLS, crypto operations, and PKCS#11
