# Bare Claude Response — PR #10035

All three fixes are in place. Here's a summary:

### 1. `_wc_Hash_Grow` zero-length fix (`wolfcrypt/src/hash.c:1959-1962`)
Changed `inSz <= 0` to separate checks: `inSz < 0` returns `BAD_FUNC_ARG`, `inSz == 0` returns `0` (no-op). This allows zero-length input to pass through without error, which is semantically valid for hash update operations.

### 2. MAX32666 SHA Copy fix (`wolfcrypt/src/port/maxim/max3266x.c:818-826`)
Moved `srcBuf = *dstMsg` from **before** the free/XMEMCPY sequence to **after** `XMEMCPY(dst, src, ctxSz)`. The XMEMCPY copies the entire src struct into dst, so after it executes, `*dstMsg` holds the source's msg pointer — which is the buffer we need to deep-copy. The broken version saved `*dstMsg` before the free, capturing a dangling pointer to the old dst buffer.

### 3. CI config (`os-check.yml:101`)
Added `'--enable-all CPPFLAGS=-DWOLFSSL_HASH_KEEP'` to the `make_check` matrix to ensure `WOLFSSL_HASH_KEEP` is tested in CI going forward.
