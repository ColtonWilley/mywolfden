# wolfDen Claude Response (iter1) — PR #10005

The fix makes `wc_AesCbcEncrypt` match `wc_AesCbcDecrypt`'s existing pattern (line 89-95): always reject non-block-aligned `sz`, returning `BAD_LENGTH_E` when `WOLFSSL_AES_CBC_LENGTH_CHECKS` is defined, `BAD_FUNC_ARG` otherwise.

**The bug:** Without `WOLFSSL_AES_CBC_LENGTH_CHECKS`, any `sz` value in `(0, WC_AES_BLOCK_SIZE)` passed the `sz == 0` early return and reached `out + sz - WC_AES_BLOCK_SIZE` on line 70 — an underflow computing a pointer before the `out` buffer, then reading 16 bytes from that invalid address into `aes->reg`.
