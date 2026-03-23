# wolfDen Claude Response (baseline) — PR #9997

The fix is already applied in the working tree. Here's what was done and why:

## What PR #9831 broke

PR #9831 ("Fixes to run python with --enable-all") removed the `WOLFSSL_QT` guard from `wolfSSL_CIPHER_get_name()` in `src/ssl.c`. This changed the behavior so that when `WOLFSSL_QT` is defined, `GetCipherNameIana()` is called instead of `wolfSSL_get_cipher_name_from_suite()` (which returns the internal/OpenSSL-style name). Qt expects internal cipher names, not IANA names.

## Fix (already applied in working tree)

Three changes across two files:

1. **`src/ssl.c:10613`** — Added `&& !defined(WOLFSSL_QT)` to the preprocessor guard in `wolfSSL_CIPHER_get_name()`, so Qt builds use the internal name path.

2. **`tests/api.c:13592`** — Added matching `!defined(WOLFSSL_QT)` guard to the test that checks IANA cipher name output from `SSL_CIPHER_get_name()`.

3. **`tests/api.c:26631`** — Added matching `!defined(WOLFSSL_QT)` guard to the security level cipher policy test that checks IANA-style cipher name substring matching.

This matches the fix in PR #9997 (`c952b694f`). Would you like me to commit these changes?
