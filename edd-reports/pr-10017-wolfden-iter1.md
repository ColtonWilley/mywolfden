# wolfDen Claude Response (iter1) — PR #10017

Fix applied. Here's the summary:

**Bug** (`sniffer.c:6729-6736`): The chain accumulation loop added `size_t` iov_len values without checking for unsigned wraparound. Two large `size_t` values (e.g., `SIZE_MAX - 10` + `20` = `9`) wrap to a small total that passes the `> INT_MAX` check, causing an undersized `XMALLOC` followed by a full-size `XMEMCPY` — heap overflow.

**Fix**: Added `size_t prevLen = totalLen` before the addition and `totalLen < prevLen` wraparound check in the guard condition. If the sum wraps (new total < previous total), the input is rejected before any allocation.

**Test**: Extended `test_sniffer_chain_input_overflow` with a second case using `SIZE_MAX - 10` + `20` to exercise the wraparound path specifically, in addition to the existing `INT_MAX + 1` case.
