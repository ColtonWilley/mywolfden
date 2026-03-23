# Bare Claude Response — PR #10017

Good. Here's a summary of all changes:

## Fix: `ssl_DecodePacketInternal` chain length overflow (zd21388)

### Root Cause
In `src/sniffer.c:6728`, the chain accumulation loop summed `size_t` (64-bit) `iov_len` values into an `int` (32-bit) `length` variable. When chain segments totaled more than `INT_MAX` bytes, the `int` silently truncated, causing:
1. An undersized `XMALLOC` allocation
2. The copy loop then wrote the full data into the undersized buffer → **heap overflow**

### Fix (`src/sniffer.c`)
- Accumulate total length in a `size_t totalLen` variable instead of directly into `int length`
- Check `totalLen > INT_MAX` after each addition; return `WOLFSSL_SNIFFER_ERROR` if exceeded
- Only assign `length = (int)totalLen` after validation passes
- Cast individual `iov_len` additions in the copy loop to `(int)` since they're now guaranteed safe

### Test (`tests/api/test_sniffer.c` + `test_sniffer.h`)
- `test_sniffer_chain_input_overflow`: Creates a 2-entry iovec chain with `iov_len` values summing to `INT_MAX + 1`, verifies `ssl_DecodePacketWithChain` returns `WOLFSSL_SNIFFER_ERROR`
- Registered in `tests/api.c`, `tests/api/include.am`, and `CMakeLists.txt`

### Files changed
| File | Change |
|------|--------|
| `src/sniffer.c` | Overflow check in chain accumulation loop |
| `tests/api/test_sniffer.c` | New test file |
| `tests/api/test_sniffer.h` | New test header |
| `tests/api.c` | Include + DECLS registration |
| `tests/api/include.am` | Build system registration |
| `CMakeLists.txt` | CMake build registration |
