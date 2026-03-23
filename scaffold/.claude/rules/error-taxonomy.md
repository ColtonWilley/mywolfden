---
paths:
  - "**/error-crypt.h"
  - "**/error-ssl.h"
  - "**/src/ssl.c"
  - "**/src/internal.c"
---

# wolfSSL Error Code Taxonomy

Error codes are negative integers defined in `wolfssl/wolfcrypt/error-crypt.h` (wolfCrypt) and `wolfssl/error-ssl.h` (wolfSSL/TLS). Use `wolfSSL_ERR_error_string()` to get human-readable names.

## Error Code Ranges

| Range | Subsystem | Examples |
|-------|-----------|---------|
| -100 to -299 | wolfCrypt core | ASN, RSA, ECC, AES, hash errors |
| -300 to -399 | TLS/SSL protocol | Handshake, record, alert errors |
| -400 to -499 | I/O and socket | Socket errors, timeout, connection |
| -501 and below | Extended features | OCSP, CRL, DTLS, async crypto |

## Finding Error Codes

Error constants are defined in `wolfssl/wolfcrypt/error-crypt.h` (wolfCrypt)
and `wolfssl/error-ssl.h` (wolfSSL/TLS). Always Grep for the constant name
to find the current number — numbers change between versions.

**Error codes and log messages are independent evidence.** A log message
near a numeric error code may describe a different failure at a different
call layer. wolfSSL propagates errors through multiple layers. Trace the
actual return path — the error that surfaces at the TLS layer is often
different from the one the inner wolfCrypt function produced.

### Most Common Error Constants

- **ASN_NO_SIGNER_E** — No CA to verify peer cert. Check
  `wolfSSL_CTX_load_verify_locations()` or CA bundle.
- **MATCH_SUITE_ERROR** — No common cipher suite. Check enable flags
  and `wolfSSL_CTX_set_cipher_list()`.
- **BAD_FUNC_ARG** — NULL pointer or invalid parameter to API function.
- **RNG_FAILURE_E** — RNG init/seed failure. Check entropy source on embedded.
- **SOCKET_ERROR_E** — Underlying socket error. Check I/O callbacks.
- **ASN_PARSE_E** — Malformed ASN.1 data. Check cert format (PEM vs DER).

### Choosing the Right Error Code

- **`BAD_FUNC_ARG`** — Input validation at API entry: NULL pointers,
  out-of-range lengths, invalid enum values. Use this for checks that
  run before any real work begins.
- **Subsystem-specific codes** (`ECC_BAD_ARG_E`, `RSA_WRONG_TYPE_E`,
  `AES_GCM_AUTH_E`, etc.) — Failures during algorithm execution where
  the error is semantically meaningful to the subsystem.
- **`BUFFER_E`** — Output buffer too small (caller must provide bigger buffer).

When adding a bounds check on input length before `XMEMCPY`, use
`BAD_FUNC_ARG`. Check adjacent code in the same function for precedent.

## Debugging Approach

1. **Get the error code**: `wolfSSL_get_error(ssl, ret)` after any failed API call
2. **Get the string**: `wolfSSL_ERR_error_string(err, buffer)` for human-readable name
3. **Enable debug logging**: compile with `--enable-debug` or `#define DEBUG_WOLFSSL`, then `wolfSSL_Debugging_ON()`
4. **Check the alert**: if TLS, `wolfSSL_get_alert_history()` shows what alert was sent/received
5. **Search the code**: Grep for the error constant to find where it's returned

## Error vs. Alert Mapping

TLS alerts (sent on the wire) map to wolfSSL error constants:
- `close_notify` (0) — graceful shutdown
- `unexpected_message` (10) — protocol error
- `bad_record_mac` (20) — VERIFY_MAC_ERROR
- `handshake_failure` (40) — MATCH_SUITE_ERROR or other negotiation failure
- `certificate_unknown` (46) — DOMAIN_NAME_MISMATCH or ASN_NO_SIGNER_E
- `unknown_ca` (48) — ASN_NO_SIGNER_E
- `decode_error` (50) — ASN_PARSE_E
