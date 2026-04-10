---
paths:
  - "**/wolfcrypt/test/test.c"
  - "**/wolfcrypt/src/cryptocb.c"
  - "**/wolfssl/wolfcrypt/cryptocb.h"
---

# Add Crypto Callback Support for an Algorithm

## When This Applies
Adding a new algorithm to the crypto callback (`WOLF_CRYPTO_CB`) test
infrastructure so it exercises hardware offload paths.

## Required Changes

1. **`wolfcrypt/test/test.c`** — Convert `wc_<algo>_init()` calls to
   `wc_<algo>_init_ex(key, NULL, devId)` so keys get a device ID.
   VERIFY: grep for `wc_<algo>_init` in test.c to find all call sites.

2. **`wolfcrypt/test/test.c`** — Add the algorithm's free handler case
   to `myCryptoDevCb`. VERIFY: read `myCryptoDevCb` to see existing
   handler dispatch pattern.

3. **`wolfcrypt/test/test.c`** — Call the algorithm's test function from
   `cryptocb_test()`. VERIFY: read `cryptocb_test()` for the call pattern.

All three are required — without `init_ex` wiring, callback handlers are
dead code (keys have no `devId`, so the callback never fires).

## Free Handler Convention

- Return `0` = callback handled cleanup (skip software free)
- Return `CRYPTOCB_UNAVAILABLE` = fall through to software cleanup
- For PKCS11: use conditional `if (ret == 0) ret = CRYPTOCB_UNAVAILABLE`
  when the caller's free function returns `int` (can propagate HSM errors).
  Use unconditional `ret = CRYPTOCB_UNAVAILABLE` when it returns `void`.

## Scope Boundaries

- This checklist is for CryptoCb TEST WIRING only.
- PKCS#11 algorithm integration is a separate task — see
  `checklists/add-pkcs11-algorithm.md`.
- Do NOT add `tests/api.c` changes for pure wolfCrypt callback work.
