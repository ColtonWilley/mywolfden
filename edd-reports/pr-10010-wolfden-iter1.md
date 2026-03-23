# wolfDen Claude Response (iter1) — PR #10010

The fix is already applied in the working tree. It matches commit `a8247bfd6` exactly. Here's a summary of what the fix does:

## Changes

The verify-side API functions had `word32 ctxLen` while the sign-side already used `byte ctxLen`. The ML-DSA spec only allows context lengths of 0–255 bytes, so all context length parameters should be `byte` (unsigned char).

### Files changed:

**`wolfssl/wolfcrypt/dilithium.h`** — 2 declarations fixed:
- `wc_dilithium_verify_ctx_msg`: `word32 ctxLen` → `byte ctxLen`
- `wc_dilithium_verify_ctx_hash`: `word32 ctxLen` → `byte ctxLen`

**`wolfcrypt/src/dilithium.c`** — 6 changes:
- `dilithium_verify_ctx_msg` (static): `word32 ctxLen` → `byte ctxLen`
- Removed `(byte)ctxLen` cast (now unnecessary since param is already `byte`)
- `dilithium_verify_ctx_hash` (static): `word32 ctxLen` → `byte ctxLen`
- Removed `(byte)ctxLen` cast
- `wc_dilithium_verify_ctx_msg` (public): `word32 ctxLen` → `byte ctxLen`
- `wc_dilithium_verify_ctx_hash` (public): `word32 ctxLen` → `byte ctxLen`

**`wrapper/rust/wolfssl-wolfcrypt/src/dilithium.rs`** — 2 changes:
- `verify_ctx_msg`: `as u32` → `as u8`
- `verify_ctx_hash`: `as u32` → `as u8`

The fix is already applied in the working tree. Want me to build and test it with `--enable-mldsa`?
