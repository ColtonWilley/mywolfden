# wolfDen Claude Response (iter1) — PR #9995

Now I see the full picture. The committed code has the bug. Here's the analysis and fix:

## Bug Analysis

**Location**: `src/tls13.c`, `DoTls13HandShakeMsg()`, line ~13456 (the fragmented message path)

**Root Cause**: When a TLS 1.3 handshake message is fragmented across multiple records and reassembled via `pendingMsg`, the code that handles retry on `OCSP_WANT_READ` is missing. The committed code only handles `WC_PENDING_E` (async crypto), guarded by `#ifdef WOLFSSL_ASYNC_CRYPT`:

```c
#ifdef WOLFSSL_ASYNC_CRYPT
    if (ret == WC_NO_ERR_TRACE(WC_PENDING_E)) {
        /* setup to process fragment again */
        ssl->arrays->pendingMsgOffset -= inputLength;
        *inOutIdx -= inputLength + ssl->keys.padSz;
    }
    else
#endif
    {
        XFREE(ssl->arrays->pendingMsg, ...);  // frees the reassembled message!
    }
```

**What goes wrong**: When `DoTls13HandShakeMsgType` returns `OCSP_WANT_READ` from this path:
1. The `else` branch executes — **freeing `pendingMsg`** and zeroing `pendingMsgSz`
2. `pendingMsgOffset` is not backed up
3. On re-entry, the reassembled handshake message data is gone
4. The handshake fails

This only manifests when:
- TLS 1.3 is used
- `WOLFSSL_NONBLOCK_OCSP` is enabled
- The Certificate message is large enough to be fragmented (e.g., low `max_fragment_length`)
- OCSP verification triggers a non-blocking I/O callback

The non-fragmented path (line 13178) was already fixed by an earlier commit (2e4b651b8). This is the fragmented path that was missed.

**Fix** (already applied locally, matches PR #9995):

```c
// Change guard from WOLFSSL_ASYNC_CRYPT to include WOLFSSL_NONBLOCK_OCSP
#if defined(WOLFSSL_ASYNC_CRYPT) || defined(WOLFSSL_NONBLOCK_OCSP)
    if (ret == WC_NO_ERR_TRACE(WC_PENDING_E) ||
        ret == WC_NO_ERR_TRACE(OCSP_WANT_READ)) {
```

The fix also needs:
1. **Test harness update** (`tests/api.c`): `test_ssl_memio_do_handshake` loops must treat `OCSP_WANT_READ` as a non-fatal/retriable error
2. **New test** (`tests/api/test_ocsp.c`): `test_tls13_nonblock_ocsp_low_mfl` — exercises TLS 1.3 + non-blocking OCSP + low max fragment length to force fragmentation
3. **CI coverage** (`.github/workflows/os-check.yml`): Add `CPPFLAGS="-DWOLFSSL_NONBLOCK_OCSP" --enable-maxfragment` to the OCSP test configuration

The local working tree already has the `src/tls13.c` fix applied. Want me to also apply the test harness and test changes?
