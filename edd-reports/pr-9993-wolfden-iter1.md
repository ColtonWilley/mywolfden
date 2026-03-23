# wolfDen Claude Response (iter1) — PR #9993

The fix looks good and complete. Here's the summary:

**Problem**: `wolfSSL_CTX_set1_sigalgs_list()` and `wolfSSL_set1_sigalgs_list()` couldn't parse brainpool signature algorithm strings (e.g., `"BRAINPOOL+SHA256"` or `"ECDSA-BRAINPOOL+SHA256"`). The `sig_names[]` lookup table in `src/internal.c:29332` was missing entries for brainpool, so `GetSigAlgFromName()` returned 0 (no match) and the parse failed.

**Fix** (already applied in working tree):
- **`src/internal.c`**: Added `"ECDSA-BRAINPOOL"` and `"BRAINPOOL"` → `ecc_brainpool_sa_algo` entries to `sig_names[]`, both guarded by `#ifdef HAVE_ECC_BRAINPOOL`
- **`tests/api.c`**: Added test coverage for both string forms on both CTX and SSL APIs

No other changes are needed — `AddSuiteHashSigAlgo()` already correctly maps `ecc_brainpool_sa_algo` + hash to the proper TLS 1.3 wire-format values (`ECDSA_BRAINPOOLP256R1TLS13_SHA256`, etc.).

The PR checklist items:
- **Tests**: Added
- **Doxygen**: The existing `wolfSSL_CTX_set1_sigalgs_list` docs should mention brainpool as a valid algorithm name if there's doxygen for it, but this is a minor doc update
- **READMEs**: Not typically needed for this kind of fix
- **Manual**: Could mention brainpool in the sigalgs_list documentation

Want me to check for existing doxygen docs to update, or is this ready to go?
