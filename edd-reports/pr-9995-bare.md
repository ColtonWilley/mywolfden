# Bare Claude Response — PR #9995

The fix is complete. Here's the summary:

## Bug Analysis

**Root cause**: In both `DoTls13HandShakeMsg()` (tls13.c) and `DoHandShakeMsg()` (internal.c), when a **fragmented** handshake message (assembled via `pendingMsg`) is being processed, the code that preserves `pendingMsg` for retry only checked for `WC_PENDING_E` under `WOLFSSL_ASYNC_CRYPT`. It did not handle `OCSP_WANT_READ` under `WOLFSSL_NONBLOCK_OCSP`.

**What happens without the fix**:
1. A certificate message arrives fragmented (common with large cert chains)
2. Fragments are assembled into `pendingMsg`
3. `DoTls13HandShakeMsgType` → `DoTls13Certificate` → `ProcessPeerCerts` → OCSP check returns `OCSP_WANT_READ`
4. Back in `DoTls13HandShakeMsg`, the `else` branch runs: `pendingMsg` is **freed**, `pendingMsgSz` set to 0
5. On retry, `pendingMsgSz == 0` so it tries to parse a new handshake header from the input buffer, which has already been consumed → **parse error / connection failure**

## Fix (2 files)

**`src/tls13.c:13456`** and **`src/internal.c:18815`**: Changed the compile guard from `#ifdef WOLFSSL_ASYNC_CRYPT` to `#if defined(WOLFSSL_ASYNC_CRYPT) || defined(WOLFSSL_NONBLOCK_OCSP)` and added `OCSP_WANT_READ` to the condition that preserves the pending message buffer for retry. This matches the pattern used throughout the rest of the codebase (e.g., `ProcessPeerCerts` at internal.c:17324).
