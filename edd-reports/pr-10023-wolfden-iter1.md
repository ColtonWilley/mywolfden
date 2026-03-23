# wolfDen Claude Response (iter1) — PR #10023

All `cmpl $16, %r11d` are now immediately followed by `jl` — no spurious `movl` clobbering in between. The decrypt functions didn't have the bug (they use a different pattern), which is correct.

## Summary

The working tree already had most of the described fixes pre-applied. I added the 4 remaining fixes per file (**8 total**) for the **spurious `movl %eax, %r11d` / `mov r11d, eax`** in the AES-XTS encrypt/encrypt_update functions (both AESNI and AVX1 paths).

**Complete fix inventory across all 20 files:**

| Bug | Files | Fix |
|-----|-------|-----|
| AES-XTS spurious mov clobbering r11d (remaining bytes) | `aes_xts_asm.S`, `.asm` | Removed 4 lines each (my fix) |
| AES-XTS key-rounds: spurious `movl %edx, %eax` + wrong comparisons | `aes_xts_asm.S`, `.asm` | Removed mov, fixed 2 cmpl each (pre-existing) |
| fe_x25519: `xor` → `xorq` | `fe_x25519_asm.S` | 1 fix (pre-existing) |
| SP ARM32: `sub_in_pkace` → `sub_in_place` | `sp_arm32.c`, `sp_cortexm.c` | Label fixes (pre-existing) |
| SP ARM32: `r11` → `r7` register fix | `sp_arm32.c` | 2 register fixes (pre-existing) |
| ChaCha ARM32: `same_keyb_ytes` → `same_key_bytes` | `armv8-32-chacha-asm.S/_c.c`, `thumb2-chacha-asm.S/_c.c` | Label fixes (pre-existing) |
| ChaCha ARM32: `vrev32.i16` → `vrev32.16` | `armv8-32-chacha-asm.S/_c.c` | NEON mnemonic fixes (pre-existing) |
| SHA3: `arm2` → `arm32` | `armv8-32-sha3-asm.S/_c.c` | Symbol name fixes (pre-existing) |
| AES ARM32: `#endif` comment missing `!` | `armv8-32-aes-asm.S/_c.c`, `thumb2-aes-asm.S/_c.c` | Comment fixes (pre-existing) |
| ChaCha ARM64: `arm64loop` → `arm64_loop` | `armv8-chacha-asm.S/_c.c` | Label fixes (pre-existing) |
| ML-KEM: `WOLFSLS` → `WOLFSSL` | `armv8-32-mlkem-asm.S/_c.c` | Comment typo fixes (pre-existing) |
| SHA-512: comment off-by-one | `sha512_asm.S` | Comment fixes (pre-existing) |
