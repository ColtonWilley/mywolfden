# wolfDen Claude Response (baseline) — PR #9993

Both changes look correct. Here's the summary:

## Investigation

**Issue (zd#21227):** Users could not use `"ECDSA-BRAINPOOL"` as a signature algorithm name in `wolfSSL_CTX_set1_sigalgs_list()` / `wolfSSL_set1_sigalgs_list()`. Only the short name `"BRAINPOOL"` was recognized.

**Root cause:** The `sig_names[]` table in `src/internal.c:29352` only had `{ ecc_brainpool_sa_algo, "BRAINPOOL" }`. The more natural name `"ECDSA-BRAINPOOL"` (following the `"RSA-PSS"` convention of `<keytype>-<variant>`) was missing.

**Note:** This was already fixed upstream as PR #9993 (commit `8354eb71c`, merged as `3e8338dbc`), but that merge is after our current checkout (`056b95235`).

## Fix

**`src/internal.c`** — Added `{ ecc_brainpool_sa_algo, "ECDSA-BRAINPOOL" }` to the `sig_names[]` table (placed after `ECDSA`, before `ED25519`, matching the upstream fix placement).

**`tests/api.c`** — Added test cases for `"ECDSA-BRAINPOOL+SHA256"` with both `wolfSSL_CTX_set1_sigalgs_list()` and `wolfSSL_set1_sigalgs_list()`, guarded by `HAVE_ECC_BRAINPOOL` and `!NO_SHA256`.

Both the existing `"BRAINPOOL"` name and the new `"ECDSA-BRAINPOOL"` name are now supported as aliases for `ecc_brainpool_sa_algo`. The `AddSuiteHashSigAlgo` function already handles the brainpool sig algo correctly, mapping it to the appropriate TLS 1.3 wire codes (`ECDSA_BRAINPOOLP{256,384,512}R1TLS13_SHA{256,384,512}`), so no changes are needed there.
