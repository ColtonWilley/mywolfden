# wolfDen Claude Response (baseline) — PR #10014

The fix is already applied as an uncommitted change in the working tree. It matches the fix from commit `cdc9c0a49` on another branch. The fix is correct:

**Problem**: PR #9761 (OCSP responder) added the `AsnHashes` struct to `asn.h` which uses `WC_SHA384_DIGEST_SIZE` and `WC_SHA512_DIGEST_SIZE`, but didn't add the corresponding `#include <wolfssl/wolfcrypt/sha512.h>`. This worked in most compilation units because `sha512.h` was transitively included via other headers, but broke in `hash.c` where `asn.h` is included before `hash.h`/`sha512.h`.

**Fix**: Add the conditional include at `asn.h:86-88`, right after the existing hash header includes:

```c
#if defined(WOLFSSL_SHA384) || defined(WOLFSSL_SHA512)
    #include <wolfssl/wolfcrypt/sha512.h>
#endif
```

This is already applied in the working tree. The fix is correct — it mirrors the guard conditions used by `sha512.h` itself and by the `AsnHashes` struct members that reference these digest size constants. Would you like me to commit this?
