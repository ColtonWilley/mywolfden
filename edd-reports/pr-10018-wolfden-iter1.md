# wolfDen Claude Response (iter1) — PR #10018

`curIdx = localIdx` (line 329) is set after `GetSequence` advances `localIdx`, and `curSz` is the content length returned by `GetSequence`. Since `localIdx + curSz <= size <= maxIdx <= UINT32_MAX` (GetSequence validates this), the addition `curIdx + (word32)curSz` won't overflow. The fix is safe.

The changes are correct and complete. Here's what was done across 3 files:

**Fix** (`wolfcrypt/src/pkcs12.c:337-341`): Added bounds check after `GetObjectId()` inside the ContentInfo parsing loop. If the OID consumed more bytes than the ContentInfo SEQUENCE declared (`localIdx > curIdx + (word32)curSz`), returns `ASN_PARSE_E` before reaching the unsigned subtraction at line 352 (`ci->dataSz = (word32)curSz - (localIdx - curIdx)`), preventing the underflow to ~4GB.

**Test** (`tests/api/test_pkcs12.c:241-272`): `test_wc_d2i_PKCS12_oid_underflow` crafts a PKCS12 DER where the inner ContentInfo SEQUENCE declares length 5 but contains an 11-byte OID. Expects `wc_d2i_PKCS12()` to return `ASN_PARSE_E`.

**Test registration** (`tests/api/test_pkcs12.h`): Added function declaration and `TEST_DECL_GROUP` entry in `TEST_PKCS12_DECLS`.

The fix uses the addition-form bounds check pattern (`a > b + c` instead of checking `a - b > c` after subtraction), which is the correct approach for unsigned arithmetic as documented in the wolfSSL discovered patterns.
