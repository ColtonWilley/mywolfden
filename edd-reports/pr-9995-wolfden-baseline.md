# wolfDen Claude Response (baseline) — PR #9995

Now I have the complete picture. Here's my analysis:

## Bug Analysis — ZD21341

**Root cause:** In `DoTls13HandShakeMsg()` (`src/tls13.c:13456`), the fragment reassembly path only handled `WC_PENDING_E` under `WOLFSSL_ASYNC_CRYPT` when deciding whether to preserve the pending message buffer for retry. `OCSP_WANT_READ` was not recognized as a retriable condition.

**What happens:** When a TLS 1.3 certificate message is fragmented across multiple records (common with certificate chains or low MFL settings), the message is reassembled into `ssl->arrays->pendingMsg`. After reassembly, `DoTls13HandShakeMsgType` processes it. If OCSP verification returns `OCSP_WANT_READ` (non-blocking OCSP needs more data), the return value falls through to the `else` branch that **frees `pendingMsg`**. On retry, the message data is gone — causing a crash or parse error.

**The fix** (3 lines in `src/tls13.c`):

```c
// Before (HEAD):
#ifdef WOLFSSL_ASYNC_CRYPT
    if (ret == WC_NO_ERR_TRACE(WC_PENDING_E)) {

// After (fix):
#if defined(WOLFSSL_ASYNC_CRYPT) || defined(WOLFSSL_NONBLOCK_OCSP)
    if (ret == WC_NO_ERR_TRACE(WC_PENDING_E) ||
        ret == WC_NO_ERR_TRACE(OCSP_WANT_READ)) {
```

This matches the TLS 1.2 pattern in `DoHandShakeMsg()` (`internal.c:18815`), which already has `WOLFSSL_NONBLOCK_OCSP` in its guard.

**Current state:** The fix is already applied in the working tree (local modification). This matches upstream commit `064436945` by Juliusz Sosinowicz on `master`, which also includes:
- Test case `test_tls13_nonblock_ocsp_low_mfl` — uses a 2-cert chain with MFL=1024 to force fragmentation, with a simulated non-blocking OCSP callback
- CI update to test `WOLFSSL_NONBLOCK_OCSP` with `--enable-maxfragment` in `os-check.yml`
- `tests/api.c` updates to handle `OCSP_WANT_READ` in the test handshake loop (lines 4871, 4896)

The test and CI changes from `064436945` are **not** applied locally yet — only the `tls13.c` fix is present.
