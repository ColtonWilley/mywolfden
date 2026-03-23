# Improvement Proposal: PR #9935, Iteration 1

**File:** `scaffold/.claude/rules/crypto/certificates.md`
**Action:** `append_section`
**Anchor:** `N/A`

## Reasoning
Any developer adding a new SAN type, verification parameter, or custom cert check will hit this fork. The pattern — native path in internal.c under #ifndef OPENSSL_EXTRA, compat path via ssl->param in ssl.c under #ifdef OPENSSL_EXTRA — is non-obvious and causes compile failures or double-verification if wrong. The error code note prevents reuse of the wrong constant, which would also compile cleanly but produce wrong user-visible errors.

## Proposed Content
```

## OPENSSL_EXTRA Dual-Path Architecture for Verification Features

When adding a certificate verification feature (hostname, IP, email SAN, custom checks), wolfSSL forks the implementation at `OPENSSL_EXTRA`:

- **`#ifdef OPENSSL_EXTRA` path (ssl.c)**: Route through `ssl->param` (X509_VERIFY_PARAM pipeline). Use `wolfSSL_X509_VERIFY_PARAM_set1_*()` to stage the value; the param pipeline handles verification during the handshake.
- **`#ifndef OPENSSL_EXTRA` path (internal.c)**: Call the internal `Check*` function directly. Guard with `#ifndef OPENSSL_EXTRA` — not `#ifdef WOLFSSL_<FEATURE>` — because when OPENSSL_EXTRA is active the param pipeline is already handling verification, and double-verification causes incorrect behavior.

The entry-point function in ssl.c calls one or the other branch; both must be implemented and both require their own test function gated by the appropriate `#ifdef`/`#ifndef`. Also note: wolfSSL uses distinct error codes per verification failure type (e.g., `DOMAIN_NAME_MISMATCH`, `IPADDR_MISMATCH`) — do not reuse the nearest similar error code; grep `error-ssl.h` for the type-specific constant.
```
