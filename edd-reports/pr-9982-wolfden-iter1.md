# wolfDen Claude Response (iter1) — PR #9982

The changes look correct. Here's what was done:

**Problem:** In the TLS 1.3 client handshake, cert setup callbacks were split across two functions — `CertSetupCbWrapper` in `DoTls13CertificateRequest` and `CBClientCert` in `SendTls13Certificate`. The TLS 1.2 analog (`DoCertificateRequest` in `internal.c`) handles both in a single function.

**Fix in `tls13.c`:**

1. **Added `CBClientCert` logic to `DoTls13CertificateRequest`** (before `CertSetupCbWrapper`), matching the TLS 1.2 pattern:
   - Uses `wolfSSL_use_certificate`/`wolfSSL_use_PrivateKey` (SSL-level, correct) instead of the `wolfSSL_CTX_use_*` (CTX-level) that `SendTls13Certificate` had
   - Handles `ret < 0` → `WOLFSSL_ERROR_WANT_X509_LOOKUP` (was missing)
   - Returns `CLIENT_CERT_CB_ERROR` on load failure (was silently ignored)

2. **Removed the `CBClientCert` block and `x509`/`pkey` variables from `SendTls13Certificate`** — cert setup is no longer split across two functions.

All cert setup callbacks now run once in `DoTls13CertificateRequest`, before `PickHashSigAlgo` and the `sendVerify` decision.
