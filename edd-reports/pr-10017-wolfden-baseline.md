# wolfDen Claude Response (baseline) — PR #10017

The fix and test are already fully implemented. Here's what's in place:

**Fix in `src/sniffer.c:6719-6753`:**
- Uses `size_t totalLen` (line 6723) to safely accumulate `iov_len` values
- Checks `totalLen > (size_t)INT_MAX` on each iteration (line 6731), returning `WOLFSSL_SNIFFER_ERROR` if exceeded
- Only casts to `int` after validation (line 6736)
- Uses a dedicated `DYNAMIC_TYPE_SNIFFER_CHAIN_BUFFER` memory type (registered in `types.h:1375`)

**Test in `tests/api/test_sniffer.c:46-70`:**
- `test_sniffer_chain_input_overflow` creates a 2-element iovec chain with `iov_len = INT_MAX` + `iov_len = 1`
- Verifies `ssl_DecodePacketWithChain` returns `WOLFSSL_SNIFFER_ERROR`
- Properly guarded with `#if defined(WOLFSSL_SNIFFER) && defined(WOLFSSL_SNIFFER_CHAIN_INPUT)`

**Test registration:**
- Declared in `test_sniffer.h:27` with `TEST_DECL_GROUP` macro (line 30)
- Listed in `include.am:163` as `EXTRA_DIST`
- Expanded in `tests/api.c:34622` via `TEST_SNIFFER_DECLS`

Everything looks correct — the fix prevents the `size_t` → `int` truncation that would cause an undersized allocation and subsequent heap overflow. No additional changes needed.
