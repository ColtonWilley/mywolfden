# Bare Claude Response — PR #9981

Here's a summary of the Fenrir-class fixes across 4 files:

### Timing side-channel fixes (2)
- **`src/internal.c:5419`** — RSA PKCS#1 v1.5 signature verification: `XMEMCMP` → `ConstantCompare` to prevent timing leaks when comparing decoded signature against expected encoding
- **`src/pk_rsa.c:3408`** — `wolfSSL_RSA_verify_ex`: same class of fix for OpenSSL-compat RSA verify path

### Sensitive buffer clearing (4 locations in dilithium.c)
- **`dilithium_make_key`** — `ForceZero` the 32-byte random `seed` after key generation
- **`dilithium_expand_s_c`** — `ForceZero` the `seed` buffer containing private seed material
- **`dilithium_sign_with_seed_mu`** (both `#ifdef` paths) — `ForceZero` the `priv_rand_seed` buffer derived from the private key K

### Missing bounds check (1)
- **`wc_ecc_import_x963_ex2` KCAPI path** — Added `inLen <= sizeof(key->pubkey_raw)` guard before `XMEMCPY`, matching the existing check in the ATECC508A/608A path

No build tools are available in this environment to compile-test, but all changes follow existing patterns already used elsewhere in the codebase.
