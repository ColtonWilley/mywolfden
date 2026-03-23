# Bare Claude Response — PR #9982

The fix is clean. Here's what was wrong and what changed:

**Problem:** `CertSetupCbWrapper` was called twice in `DoTls13CertificateRequest`:
1. Line 5880 under `#ifdef WOLFSSL_CERT_SETUP_CB` — before `TLSX_Parse`
2. Line 5930 under `#ifdef OPENSSL_EXTRA` — after `TLSX_Parse`

Since `OPENSSL_EXTRA` auto-enables `WOLFSSL_CERT_SETUP_CB` in `settings.h` (line 4085-4086), both guards are true when `OPENSSL_EXTRA` is defined, causing the user's cert setup callback to fire twice.

**Fix:**
- Removed the early call (before extension parsing) — the callback should run after `TLSX_Parse` so it has access to parsed extension data
- Changed the remaining call's guard from `#ifdef OPENSSL_EXTRA` to `#ifdef WOLFSSL_CERT_SETUP_CB` — this is the correct guard since `CertSetupCbWrapper` is declared under `WOLFSSL_CERT_SETUP_CB` and should work with or without `OPENSSL_EXTRA`

This matches the TLS 1.2 analog in `internal.c:31975` where `CertSetupCbWrapper` is called once under `#ifdef WOLFSSL_CERT_SETUP_CB`, after processing the certificate request content.
