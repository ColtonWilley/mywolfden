---
paths:
  - "**/asn.c"
  - "**/certs/**"
  - "**/*cert*"
---

# Certificate and X.509 Patterns

## Certificate Loading Issues
**Most common problem**: Format mismatch between PEM and DER.
- `wolfSSL_CTX_use_certificate_file()` — auto-detects format but needs correct `SSL_FILETYPE_PEM` or `SSL_FILETYPE_ASN1`
- `wolfSSL_CTX_use_certificate_buffer()` — for embedded systems without filesystem
- Certificate chain: load in order (leaf first, then intermediates, then root)
- PKCS#12 loading: `wolfSSL_CTX_use_PKCS12_file()` or parse with `wc_d2i_PKCS12()`

## Chain Validation Failures
**Error -313 (ASN_NO_SIGNER_E)**: Missing CA in trust store.
- Check: are all intermediates in the chain?
- Check: is the root CA loaded via `wolfSSL_CTX_load_verify_locations()`?
- Self-signed certs need the cert itself loaded as CA, or verification disabled
- Maximum chain depth: default 6, configurable with `wolfSSL_CTX_set_verify_depth()`

**Error -173 (ASN_SIG_CONFIRM_E)**: Signature doesn't verify.
- Check: correct CA for this cert?
- Check: cert data corrupted or truncated?
- Check: hash algorithm supported? (SHA-1 certs may fail with SHA-1 disabled)

**Error -152/-153 (date errors)**: Certificate date validation.
- Common on embedded: system clock not set (stuck at epoch)
- Fix: set system time before TLS, or use `wolfSSL_CTX_set_verify()` with custom callback to skip date check
- `NO_ASN_TIME` define disables all date checking

## OCSP (Online Certificate Status Protocol)
- Enable: `--enable-ocsp` or `#define HAVE_OCSP`
- Stapling: `--enable-ocsp-stapling` (server sends OCSP response with cert)
- Must-staple: server cert has must-staple extension → connection fails if no staple
- Custom OCSP callback: `wolfSSL_CTX_SetOCSP_Cb()` for custom validation
- OCSP responder URL: extracted from cert's AIA extension automatically

## CRL (Certificate Revocation List)
- Enable: `--enable-crl` or `#define HAVE_CRL`
- Load CRL: `wolfSSL_CTX_LoadCRL()` or `wolfSSL_LoadCRL()`
- CRL monitoring: `wolfSSL_CTX_EnableCRL()` with `WOLFSSL_CRL_MONITOR`
- Missing CRL: if CRL checking enabled but no CRL available → connection fails
- CRL format: PEM or DER, same format considerations as certificates

## Certificate Generation with wolfCrypt
- CSR generation: `wc_MakeCertReq()` → `wc_SignCert()`
- Self-signed: `wc_MakeSelfCert()` or `wc_MakeCert()` + `wc_SignCert()`
- Key generation: `wc_MakeRsaKey()` or `wc_ecc_make_key()`
- Output formats: `wc_DerToPem()` for PEM conversion

## Common Pitfalls
- Loading cert before key → some APIs require key first
- PEM file with multiple certs → only first cert loaded by some APIs
- Windows line endings (CRLF) in PEM files → usually OK but can cause issues on some platforms
- Cert with key usage restrictions → may not match intended use (server vs client)
- ECC cert with RSA cipher suite (or vice versa) → MATCH_SUITE_ERROR

## Adding Per-Connection Certificate Verification Parameters

When adding a new parameter that influences certificate verification during
TLS handshake (expected hostname, IP address, pinned key hash, etc.):

1. **Internal state**: Add a `buffer <name>` field to the `Buffers` struct
   in `wolfssl/internal.h`. This holds per-connection dynamic data freed
   on session teardown.
2. **Public API**: Declare the setter in `wolfssl/ssl.h` with `WOLFSSL_ABI`
   and `WOLFSSL_API`. Follow the `wolfSSL_check_domain_name()` pattern.
3. **Implementation**: In `src/ssl.c`, use `WOLFSSL_ENTER`, null-check the
   `ssl` pointer, allocate with `XMALLOC(..., ssl->heap, DYNAMIC_TYPE_DOMAIN)`.
4. **Verification hook**: The stored value is consumed in the peer cert
   check in `src/internal.c`. Follow the OPENSSL_EXTRA dual-path pattern
   (see coding-standards.md).
5. **Cleanup**: Add `XFREE` for the new buffer field in the resource
   cleanup function in `src/internal.c`.

This four-file pattern (internal.h, ssl.h, ssl.c, internal.c) applies to
any new cert verification hook.

### OPENSSL_EXTRA Dual-Path Verification

Certificate verification features have two runtime paths that must not
double-check:

- **Native path** (`#ifndef OPENSSL_EXTRA`): uses `ssl->buffers.<field>`
  directly in `ProcessPeerCerts` / `DoCertificate`.
- **Compat path** (`#ifdef OPENSSL_EXTRA`): uses `ssl->param->*` fields
  set via `X509_VERIFY_PARAM` APIs, checked by the OpenSSL compat layer.

The native check in `internal.c` **must** be guarded with
`#ifndef OPENSSL_EXTRA` so only one path runs. Omitting this guard
causes the same verification to fire twice (once natively, once through
the compat shim), which can produce confusing double-failures or mask
bugs in one path.

### Naming Convention for Compat Fields

Fields that mirror OpenSSL's `X509_VERIFY_PARAM` use OpenSSL's naming,
not wolfSSL camelCase. For example, the IP-address ASCII buffer is
`ipasc` (matching OpenSSL's `ip_asc`), not `ipAddr`. Check the
corresponding `wolfSSL_X509_VERIFY_PARAM_*` function names in `ssl.c`
for the canonical spelling before naming a new field.
