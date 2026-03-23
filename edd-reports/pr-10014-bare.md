# Bare Claude Response — PR #10014

The fix is in place. Here's what was done:

**Problem:** `wolfssl/wolfcrypt/asn.h` uses `WC_SHA384_DIGEST_SIZE` (line 2670) and `WC_SHA512_DIGEST_SIZE` (line 2673) in the `AsnHashes` struct, but never included `wolfssl/wolfcrypt/sha512.h` where those constants are defined. It worked by accident when other headers pulled in `sha512.h` transitively, but broke when `asn.h` was parsed before that transitive include (e.g., in `hash.c` with SHA-384 enabled).

**Fix:** Added `#include <wolfssl/wolfcrypt/sha512.h>` guarded by `#if defined(WOLFSSL_SHA384) || defined(WOLFSSL_SHA512)` at line 86, following the same pattern as the existing conditional includes for `sha.h`, `md5.h`, `sha256.h`, and `sm3.h`. The guard covers both macros since `sha512.h` defines both `WC_SHA384_DIGEST_SIZE` (under `WOLFSSL_SHA384`) and `WC_SHA512_DIGEST_SIZE` (under `WOLFSSL_SHA512`).
