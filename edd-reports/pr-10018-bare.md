# Bare Claude Response — PR #10018

The changes are complete. Here's a summary:

**Fix** (`wolfcrypt/src/pkcs12.c:337-340`): Added bounds check after `GetObjectId()` in the ContentInfo parsing loop. If the OID consumed more bytes than the ContentInfo SEQUENCE declared (`(localIdx - curIdx) > (word32)curSz`), returns `ASN_PARSE_E` instead of allowing the unsigned underflow at line 351 where `ci->dataSz` is computed.

**Test** (`tests/api/test_pkcs12.c`): Added `test_wc_d2i_PKCS12_oid_underflow` which loads a valid PKCS12 file, corrupts an OID length field to make `GetObjectId()` overrun the ContentInfo boundary, and verifies `wc_d2i_PKCS12()` returns an error instead of proceeding with the underflowed size.
