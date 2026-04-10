---
paths:
  - "**/wc_pkcs11.c"
  - "**/cryptocb.c"
  - "**/wolfcrypt/test/test.c"
---

# PKCS#11 vs CryptoCb: Separate Concerns

## PKCS#11 Algorithm Integration
- Centers on `wolfcrypt/src/wc_pkcs11.c` (~500+ lines of new functions)
- Changes: `pkcs11.h`, `wc_pkcs11.h`, algorithm headers, algorithm source
- Does NOT involve `wolfcrypt/test/test.c` unless PR scope explicitly
  includes CryptoCb testing

## CryptoCb Test Wiring
- Centers on `wolfcrypt/test/test.c` changes
- Involves: `init_ex` conversion, `myCryptoDevCb` handler, `cryptocb_test()` call
- Does NOT involve `wc_pkcs11.c`

## When Both Apply
Only when the PR explicitly targets BOTH PKCS#11 integration AND crypto
callback test coverage. Do not conflate one with the other.
