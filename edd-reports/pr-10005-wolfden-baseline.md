# wolfDen Claude Response (baseline) — PR #10005

The fix is clean. Here's what was changed:

**`wc_AesCbcEncrypt`** (encrypt):
- **Removed** the silent rounding `sz = sz - (sz % WC_AES_BLOCK_SIZE)` — this was non-standard and silently discarded trailing bytes, unlike every other AES-CBC implementation in wolfSSL
- **Moved** the `sz == 0` check to immediately after NULL checks (before any arithmetic), matching the canonical pattern
- **Added** `WOLFSSL_AES_CBC_LENGTH_CHECKS` support to return `BAD_LENGTH_E` for non-block-aligned input

**`wc_AesCbcDecrypt`** (decrypt):
- **Separated** the `sz == 0` check from the modulo check and moved it first — previously `sz == 0` was checked after `sz % WC_AES_BLOCK_SIZE != 0` (which passes for 0), but crucially the `XMEMCPY(aes->tmp, in + sz - WC_AES_BLOCK_SIZE, ...)` on the old line 84 would compute `in + 0 - 16` = `in - 16` (buffer underflow read) if the `sz == 0` early return were ever removed or reordered
- **Added** `WOLFSSL_AES_CBC_LENGTH_CHECKS` support with `BAD_LENGTH_E`, matching the canonical pattern

Both functions now follow the same guard ordering as the software AES-CBC implementation in `aes.c`: NULL check → sz==0 → length check → proceed.
