# wolfDen Claude Response (baseline) — PR #10018

All three files now match master exactly. Here's a summary of the fix:

**The bug (zd21389):** In `GetSafeContent()` at `pkcs12.c:351`, `ci->dataSz` is computed as `(word32)curSz - (localIdx - curIdx)`. If a malformed PKCS12 has a ContentInfo SEQUENCE that declares a length smaller than the OID it contains (e.g., SEQUENCE says 5 bytes but the OID is 11 bytes on the wire), the subtraction underflows to ~4GB since `dataSz` is `word32` (unsigned).

**The fix (3 files):**

1. **`wolfcrypt/src/pkcs12.c`** — Added bounds check after `GetObjectId()`:
   ```c
   /* Check that OID did not consume more than the sequence length */
   if (localIdx > curIdx + (word32)curSz) {
       freeSafe(safe, pkcs12->heap);
       return ASN_PARSE_E;
   }
   ```
   Uses `localIdx > curIdx + (word32)curSz` rather than `(localIdx - curIdx) > (word32)curSz` to avoid a potential underflow in the check itself.

2. **`tests/api/test_pkcs12.c`** — Added `test_wc_d2i_PKCS12_oid_underflow` with a crafted minimal PKCS12 DER that triggers the exact condition (ContentInfo SEQ length=5, OID=11 bytes). Asserts `ASN_PARSE_E` specifically.

3. **`tests/api/test_pkcs12.h`** — Declared the new test and added it to `TEST_PKCS12_DECLS`.
