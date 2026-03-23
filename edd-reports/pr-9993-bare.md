# Bare Claude Response — PR #9993

The fix is straightforward:

**Problem:** `wolfSSL_CTX_set1_sigalgs_list()` and `wolfSSL_set1_sigalgs_list()` didn't recognize brainpool as a signature algorithm string. The `sig_names[]` lookup table in `src/internal.c` was missing a brainpool entry, so passing `"BRAINPOOL+SHA256"` (or SHA384/SHA512) would fail.

**Changes:**

1. **`src/internal.c:29352`** — Added `{ ecc_brainpool_sa_algo, "BRAINPOOL" }` to the `sig_names[]` array, guarded by `#ifdef HAVE_ECC_BRAINPOOL`. This allows `GetSigAlgFromName()` to recognize `"BRAINPOOL"` and map it to `ecc_brainpool_sa_algo`. The downstream `AddSuiteHashSigAlgo()` already handles `ecc_brainpool_sa_algo` correctly, mapping it to the appropriate TLS 1.3 brainpool signature scheme wire values (`ECDSA_BRAINPOOLP256R1TLS13_SHA256`, etc.).

2. **`tests/api.c:15762`** — Added test cases for `"BRAINPOOL+SHA256"` with both `wolfSSL_CTX_set1_sigalgs_list()` and `wolfSSL_set1_sigalgs_list()`, guarded by `#ifdef HAVE_ECC_BRAINPOOL` and `#ifndef NO_SHA256`.
