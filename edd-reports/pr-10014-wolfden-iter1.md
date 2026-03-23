# wolfDen Claude Response (iter1) — PR #10014

The fix is already applied locally. Let me verify it's correct:

1. **Guard condition**: `WOLFSSL_SHA384 || WOLFSSL_SHA512` — matches `sha512.h`'s own internal guard at line 32. Correct.
2. **Placement**: Between `sha256.h` (unconditional) and SM3 include. Follows the existing pattern. Correct.
3. **Usage**: `WC_SHA384_DIGEST_SIZE` (guarded by `WOLFSSL_SHA384`) and `WC_SHA512_DIGEST_SIZE` (guarded by `WOLFSSL_SHA512`) are used in the `AsnHashes` struct at lines 2672-2677. Both constants are defined in `sha512.h`.
4. **No circular include risk**: `sha512.h` includes only `types.h` and optionally `fips.h` — no path back to `asn.h`.

The fix is correct and already applied. The local diff shows exactly the right change: adding `#include <wolfssl/wolfcrypt/sha512.h>` guarded by `#if defined(WOLFSSL_SHA384) || defined(WOLFSSL_SHA512)` after `sha256.h` and before `sm3.h`.

**Summary**: PR #9761 added the `AsnHashes` struct to `asn.h` which references `WC_SHA384_DIGEST_SIZE` and `WC_SHA512_DIGEST_SIZE` from `sha512.h`, but didn't add the corresponding include. The fix (already applied as a local unstaged change) adds the guarded include at `wolfssl/wolfcrypt/asn.h:86-88`. The guard `WOLFSSL_SHA384 || WOLFSSL_SHA512` mirrors `sha512.h`'s own internal gate, which is the correct pattern per the discovered-patterns rule about conditional include guards.
