# Bare Claude Response — PR #10005

The fix is clean. Here's what was wrong and what I changed:

**Bug:** When `sz == 0`, both `wc_AesCbcEncrypt` and `wc_AesCbcDecrypt` compute pointer offsets like `out + sz - WC_AES_BLOCK_SIZE` (or `in + sz - WC_AES_BLOCK_SIZE`), which underflows to `out - 16` / `in - 16` — reading/writing 16 bytes before the buffer start.

- **`wc_AesCbcEncrypt`** (line 63): `XMEMCPY(aes->reg, out + 0 - 16, 16)` — reads 16 bytes before `out`
- **`wc_AesCbcDecrypt`** (line 78): `XMEMCPY(aes->tmp, in + 0 - 16, 16)` — reads 16 bytes before `in`

**Fix:** Added an early `return 0` after the size is truncated to block alignment (encrypt) or validated (decrypt), before any pointer arithmetic occurs. Encrypting/decrypting zero bytes is a valid no-op.
