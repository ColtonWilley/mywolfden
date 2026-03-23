# wolfDen Claude Response (iter1) — PR #9998

Now I have the complete picture. Here's a summary of the three changes in this working tree:

## Changes Summary

### 1. Remove incorrect `crypto_put_default_rng()` in `get_crypto_default_rng()` (`lkcapi_sha_glue.c:1152`)

**Original:** When `cra_init` doesn't match (wrong RNG registered), the error path called `crypto_put_default_rng()` before returning NULL.

**Problem:** `get_crypto_default_rng()` never calls `crypto_get_default_rng()` — the comment at line 1144 explicitly says it *can't* because that uses a mutex (not allowed in interrupt handlers). Instead it reads `crypto_default_rng` directly. Calling `crypto_put_default_rng()` without a matching `crypto_get_default_rng()` decrements the reference count incorrectly, which could cause the kernel to prematurely free the RNG. This is a ref-count underflow bug.

**Fix:** Remove the `crypto_put_default_rng()` call. Correct — you can't put a ref you never got.

### 2. Add `wc_linux_kernel_rng_is_wolfcrypt()` (`lkcapi_sha_glue.c:1158-1168`, `linuxkm_wc_port.h:218-221`)

New public function that checks whether the kernel's `crypto_default_rng` is a wolfCrypt DRBG. It's a lightweight, non-locking version of the same validation logic in `get_crypto_default_rng()`, suitable for external callers (like the `rng_bank` consumer in the `20260316-various-backports` branch) to query without needing access to linuxkm internals. Declared `extern` in the port header under the same `LINUXKM_LKCAPI_REGISTER_HASH_DRBG_DEFAULT && HAVE_HASHDRBG` guard.

### 3. Add `!WC_NO_CONSTRUCTORS` gate around `wc_rng_new_bankref()` (`rng_bank.c`, `rng_bank.h`)

**Original:** Guarded only by `#ifndef WC_RNG_BANK_STATIC`.

**Fix:** Added `&& !defined(WC_NO_CONSTRUCTORS)` to both the implementation and declaration. This is consistent with the existing pattern — `wc_rng_new_bankref()` dynamically allocates an `WC_RNG` via `XMALLOC`, which is a "constructor" function. When `WC_NO_CONSTRUCTORS` is defined (e.g., in static-only embedded builds or linuxkm contexts), these dynamic allocation constructors should be excluded.

---

All three changes look correct. The `crypto_put_default_rng()` removal fixes a real ref-count underflow bug. The new function and guard changes are clean and consistent with existing patterns. Is there something specific you'd like me to fix or investigate further, or would you like me to commit these changes?
