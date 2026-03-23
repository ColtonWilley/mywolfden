# Bare Claude Response — PR #9998

All four changes are complete. Here's a summary:

### Changes made across 4 files:

1. **`linuxkm/lkcapi_sha_glue.c`** — Removed the incorrect `crypto_put_default_rng()` call in `get_crypto_default_rng()`. The function never calls `crypto_get_default_rng()` (can't — mutex forbidden in interrupt handlers), so the `crypto_put_default_rng()` on the error path would incorrectly decrement the refcount.

2. **`linuxkm/lkcapi_sha_glue.c`** — Added `wc_linux_kernel_rng_is_wolfcrypt()` function right after `get_crypto_default_rng()`, within the same `LINUXKM_LKCAPI_REGISTER_HASH_DRBG_DEFAULT && HAVE_HASHDRBG` guard block. It checks three conditions: `wc_linuxkm_drbg_default_instance_registered` is set, `crypto_default_rng` is non-NULL, and its `cra_init` matches `wc_linuxkm_drbg_init_tfm`.

3. **`linuxkm/linuxkm_wc_port.h`** — Declared `wc_linux_kernel_rng_is_wolfcrypt()` as an `extern` function, gated by the same `LINUXKM_LKCAPI_REGISTER_HASH_DRBG_DEFAULT && HAVE_HASHDRBG` conditions, placed near the other RNG-related `extern` declarations.

4. **`wolfcrypt/src/rng_bank.c` + `wolfssl/wolfcrypt/rng_bank.h`** — Added `!WC_NO_CONSTRUCTORS` to the existing `!WC_RNG_BANK_STATIC` guard around `wc_rng_new_bankref()`. This function uses `XMALLOC`/`XFREE`, so it must be excluded on platforms with no heap (where `WC_NO_CONSTRUCTORS` is defined).
