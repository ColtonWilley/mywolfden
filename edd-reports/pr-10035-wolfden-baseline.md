# wolfDen Claude Response (baseline) — PR #10035

All three changes are already applied in the working tree. Let me verify the fixes are correct by reviewing the final state:

**Fix 1: `_wc_Hash_Grow` zero-length input** — The working tree correctly separates `inSz <= 0` into `inSz < 0` → `BAD_FUNC_ARG` and `inSz == 0` → `return 0` (no-op). This is correct.

**Fix 2: `wc_MXC_TPU_SHA_Copy` deep-copy order** — The working tree moves `srcBuf = *dstMsg` to AFTER the `XMEMCPY(dst, src, ctxSz)`, which is the correct sequence:
1. Free dst's old msg buffer
2. Shallow copy src → dst (now `*dstMsg` points to src's msg buffer)
3. Save `srcBuf = *dstMsg` (src's pointer, via the shallow copy)
4. Allocate new buffer for dst and copy from srcBuf

The broken code (`30cb25e49`) captured `srcBuf = *dstMsg` BEFORE the free, meaning it held dst's old pointer. After `wc_MXC_TPU_SHA_Free` freed that buffer, `srcBuf` became a dangling pointer.

**Fix 3: CI** — Added `'--enable-all CPPFLAGS=-DWOLFSSL_HASH_KEEP'` to os-check.yml matrix to catch `HASH_KEEP` regressions.

All three fixes are already applied in the working tree and look correct. The changes are minimal and focused — they match exactly what the PR description states. Is there anything else you'd like me to do with these changes, such as verifying the fix compiles or creating a commit?
