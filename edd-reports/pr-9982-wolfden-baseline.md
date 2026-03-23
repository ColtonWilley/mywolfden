# wolfDen Claude Response (baseline) — PR #9982

The fix removes the `|| ssl->ctx->certSetupCb != NULL` fallback from the condition in `DoTls13CertificateRequest`.

**Problem:** When `OPENSSL_EXTRA` and `WOLFSSL_CERT_SETUP_CB` are both defined (which they always are together per `settings.h`), `CertSetupCbWrapper` is called at line 5925, invoking `ssl->ctx->certSetupCb`. If the callback returns success (1) without loading a certificate, `CertSetupCbWrapper` returns 0. Then the condition at line 5929 would correctly fail (`ssl->buffers.certificate` is NULL) — except the `|| ssl->ctx->certSetupCb != NULL` clause on the old line 5936 forced entry into the cert-present branch anyway. This set `sendVerify = SEND_CERT` even though no cert was loaded, causing `SendTls13Certificate` to later fail with `NO_CERT_ERROR`.

**Fix:** Remove the redundant `certSetupCb != NULL` check. The callback was already invoked — the cert buffers reflect whether it loaded anything. This matches the TLS 1.2 analog in `DoCertificateRequest` (`internal.c:31981`) which only checks `ssl->buffers.certificate` after calling `CertSetupCbWrapper`.
