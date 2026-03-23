# Bare Claude Response — PR #9992

The cherry-pick applied cleanly. Here's a summary of all the changes:

**Spelling fixes (typos in `#ifdef` guards):**
- `HAVE_CURVE22519` → `HAVE_CURVE25519` in `snifftest.c`
- `WOLFSSL_ASNC_CRYPT` → `WOLFSSL_ASYNC_CRYPT` in `tests/api.c`
- `WOLFSSL_SM4_EBC` → `WOLFSSL_SM4_ECB` in `wolfcrypt/src/evp.c`
- `WOLFSSL_SH224` → `WOLFSSL_SHA224` in `renesas_fspsm_internal.h`

**Removed invalid/typo entries from `.wolfssl_known_macro_extras`:**
- `HAVE_CURVE22519` (typo for `HAVE_CURVE25519`)
- `HAVE_FACON` (typo for `HAVE_FALCON`)
- `WOLFSSL_ASNC_CRYPT` (typo for `WOLFSSL_ASYNC_CRYPT`)
- `WOLFSSL_NO_CLIENT` (invalid/unused)
- `WOLFSSL_SH224` (typo for `WOLFSSL_SHA224`)
- `WOLFSSL_SM4_EBC` (typo for `WOLFSSL_SM4_ECB`)

**Added inline documentation** for build options in 18 source files:
- `src/internal.c` — Connection & Buffers, Cipher Suite, Certificate Validation, Handshake, Session Tickets, TLS 1.3, DTLS, Compatibility, Async, Hardware, Hardening categories
- `src/ssl.c` — OpenSSL Compatibility, Session Management, etc.
- `src/tls.c` — TLS extension/protocol options
- `src/tls13.c` — TLS 1.3 specific options
- `wolfcrypt/src/aes.c` — AES modes and hardware acceleration options
- `wolfcrypt/src/asn.c` — ASN.1/X.509 parsing options
- `wolfcrypt/src/cryptocb.c` — Crypto callback options
- `wolfcrypt/src/curve448.c`, `des3.c`, `ecc.c`, `hmac.c`, `md5.c`, `pkcs7.c`, `poly1305.c`, `random.c`, `rsa.c`, `sha.c`, `sha3.c`, `sha512.c`, `wc_port.c`

**Additional test changes in `tests/api.c`:**
- Removed OCSP_WANT_READ from handshake retry loops
- Simplified MLKEM/KYBER test configurations  
- Fixed LMS test file handle leak (missing `fclose` on error path)
- Removed `test_tls13_nonblock_ocsp_low_mfl` test declaration

All changes are now staged and ready. Would you like me to commit these changes?
