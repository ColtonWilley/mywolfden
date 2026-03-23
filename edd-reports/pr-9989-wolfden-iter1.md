# wolfDen Claude Response (iter1) — PR #9989

Here's a summary of the changes:

### Fix: `wolfcrypt/src/ecc.c:9490-9493`

Added a sanity check in `wc_ecc_import_point_der_ex()` that validates the computed `keysize` matches `ecc_sets[curve_idx].size` before reading point data via `mp_read_unsigned_bin()`. Without this check, a mismatched input length would cause the function to read the wrong number of bytes for x/y coordinates — potentially reading out of bounds or importing a silently malformed point.

```c
/* sanity check: computed keysize must match the curve's expected size */
if (err == MP_OKAY && keysize != ecc_sets[curve_idx].size) {
    err = ECC_BAD_ARG_E;
}
```

The check is placed after keysize computation (line 9484-9488) and before the first `mp_read_unsigned_bin` call. It covers all input paths: uncompressed, compressed with `shortKeySize`, and compressed without.

Note: `wc_ecc_import_x963_ex2()` (the other ECC key import path) already validates keysize implicitly via `wc_ecc_set_curve()` at line 10757.

### Tests: `wolfcrypt/test/test.c`

Added 4 negative test cases in `ecc_point_test()` (inside the `HAVE_COMP_KEY` block):

1. **Compressed point, 1 byte** (`derComp0` with len=1) — keysize computes to 0, doesn't match P-256's 32 → `ECC_BAD_ARG_E`
2. **Compressed point, 1 byte** (`derComp1` with len=1) — same, odd parity variant
3. **Invalid prefix byte** (0x01 instead of 0x02/0x03/0x04) — `ASN_PARSE_E`
4. **Valid uncompressed prefix, wrong size** (49 bytes = 24+24 x/y, curve expects 32+32) — keysize 24 != 32 → `ECC_BAD_ARG_E`
