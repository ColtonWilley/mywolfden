# wolfDen Claude Response (baseline) — PR #9998

The fix snapshots `crypto_default_rng` into a local variable before checking and dereferencing it, matching the pattern used by `get_crypto_default_rng()` just above. This prevents a NULL dereference if `crypto_default_rng` is cleared between the two reads.

The other changes in the working tree look correct:
- **Removing `crypto_put_default_rng()` from `get_crypto_default_rng()`**: Correct — that function never calls `crypto_get_default_rng()` (it reads the global directly to avoid the kernel mutex in interrupt context), so there's no reference to release.
- **Adding `!WC_NO_CONSTRUCTORS` gate to `wc_rng_new_bankref()`**: Correct — the function uses `XMALLOC`, so it shouldn't be available in no-constructor/no-malloc environments. Both `.c` and `.h` are consistent.
