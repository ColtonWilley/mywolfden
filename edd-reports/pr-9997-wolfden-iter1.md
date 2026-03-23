# wolfDen Claude Response (iter1) — PR #9997

The fix is already in place. All instances of `GetCipherNameIana` usage in `wolfSSL_CIPHER_get_name()` are properly guarded with `!defined(WOLFSSL_QT)`.

The fix from commit `c952b694f` is **already present** in the current checkout (HEAD `45b31a182`). The `WOLFSSL_QT` guard exists in all three locations:

1. **`src/ssl.c:10616-10617`** — `wolfSSL_CIPHER_get_name()` correctly uses `!defined(WOLFSSL_QT)` to return internal names instead of IANA names for Qt builds
2. **`tests/api.c:13595-13596`** — Test expectation properly gated
3. **`tests/api.c:26633-26634`** — Crypto policy test properly gated

No changes needed — the restoration was already merged. Is there a different aspect of this you'd like me to look at?
