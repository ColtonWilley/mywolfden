# wolfDen Claude Response (baseline) — PR #10023

Here's the complete analysis of all bugs and their fixes from commit `ec958de64`:

## Investigation Summary

All fixes are already authored by Sean Parkinson and merged to `master` as `ec958de64`. The current checkout at `HEAD@3e820e591` is behind master and doesn't have them. A clean cherry-pick applies with zero conflicts across 22 files (+493, -467 lines).

### Functional Bug Fixes (security-relevant)

**1. x86_64 AES-XTS key-rounds selection (`aes_xts_asm.S`, `.asm`)**
- In the `AES_XTS_init` AVX1 path, a spurious `movl %edx, %eax` (line ~1444 in .S) clobbered `%eax` with the rounds count from `%edx`, then two subsequent comparisons used the now-stale `%eax` instead of `%edx` for the 11/13 round checks
- Fix: remove the `movl`, change `cmpl $11, %eax` → `cmpl $11, %edx` and `cmpl $13, %eax` → `cmpl $13, %edx`
- Windows .asm equivalent: remove `mov eax, r8d`, change `cmp eax, 11/13` → `cmp r8d, 11/13`
- **Impact**: Wrong AES round count selection could produce incorrect encryption for AES-192/256 XTS

**2. ARM32 SP register bugs (`sp_arm32.c`)**
- `r11 → r7`: In `sp_2048/3072/4096_mont_reduce_*()`, `lsl r7, r11, #16` and `lsr r7, r11, #16` used wrong source register `r11` instead of `r7`. Appears 6 times across 2048, 3072, and 4096-bit functions
- `r3 → r4`: `adcs r4, r3, #0` should be `adcs r4, r4, #0` — add-with-carry was reading from the wrong accumulator. Appears in same functions
- **Impact**: Incorrect multiply/accumulate results in modular reduction — could produce wrong RSA/DH results on ARM32

**3. x86_64 fe_x25519 (`fe_x25519_asm.S`)**
- Line 12372: `xor %rbx, %rbx` → `xorq %rbx, %rbx` (one instance only — the other 93 were already correct)
- Some assemblers may handle the unsuffixed form, but explicit 64-bit suffix is correct

### Non-functional Fixes (labels, comments, mnemonics)

**4. ARM32 SP label typos (`sp_arm32.c`, `sp_cortexm.c`)**
- `sub_in_pkace` → `sub_in_place` across 2048/3072/4096-bit functions (label defs + branch targets)
- Non-functional since label and branch match, but confusing

**5. ARM32 ChaCha (`armv8-32-chacha-asm.S/_c.c`, `thumb2-chacha-*`)**
- Label: `same_keyb_ytes` → `same_key_bytes`
- NEON mnemonic: `vrev32.i16` → `vrev32.16` (invalid type qualifier → correct form)

**6. ARM32 SHA3 (`armv8-32-sha3-asm.S/_c.c`)**
- Symbol: `L_sha3_arm2_neon_rt` → `L_sha3_arm32_neon_rt`, `L_sha3_arm2_rt` → `L_sha3_arm32_rt`

**7. ARM32 AES (`armv8-32-aes-asm_c.c/.S`, `thumb2-aes-asm_c.c/.S`)**
- `#endif` comment: `WOLFSSL_ARMASM_AES_BLOCK_INLINE` → `!WOLFSSL_ARMASM_AES_BLOCK_INLINE`

**8. ARM64 ChaCha (`armv8-chacha-asm_c.c/.S`)**
- Label: `arm64loop_lt_8` → `arm64_loop_lt_8`

**9. ARM32 ML-KEM (`armv8-32-mlkem-asm.S/_c.c`)**
- `#endif` comment: `WOLFSLS_ARM_ARCH` → `WOLFSSL_ARM_ARCH` (~184 changes per file)

**10. SHA-512 (`sha512_asm.S`)**
- AVX2 section msg_sched comments claimed 4 entries per block (0-3, 4-7) when only 2 are scheduled (0-1, 2-3). 96 lines of comment fixes.

**11. x86_64 SP (`sp_x86_64_asm.S/.asm`)**
- Also included in the commit — 10 lines changed in each (not mentioned in the description but present in the diff)

### How to Apply

Since the fix is already on `master` as `ec958de64`, cherry-pick it:
```bash
git cherry-pick ec958de64
```

Or if you just want to advance HEAD to master:
```bash
git merge master
```
