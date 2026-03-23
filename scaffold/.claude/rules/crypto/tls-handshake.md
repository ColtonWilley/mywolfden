---
paths:
  - "**/tls13.c"
  - "**/tls.c"
  - "**/internal.c"
  - "**/ssl.c"
---

# TLS Handshake Failure Patterns

## Error -308 (SOCKET_ERROR_E)
**What it means**: Socket-level error during TLS handshake.
**Triage path**: Check if socket is alive before SSL_connect → check I/O callbacks → check MTU/fragmentation on embedded.
**Common root causes**:
- ESP32: Wi-Fi stack drops connection during DH key exchange (memory pressure)
- FreeRTOS: Task stack overflow during handshake (need 24KB+ for RSA 2048)
- Windows: Winsock not initialized or socket closed by firewall
- Custom I/O callbacks returning wrong error code (must return WOLFSSL_CBIO_ERR_*)
**Related errors**: -155 (peer cert), -308 chains to -397 on timeout
**Key code paths**: `wolfSSL_connect()` → `SendClientHello()` → `DoServerHello()` in `src/internal.c`

## Error -188 (MATCH_SUITE_ERROR)
**What it means**: No common cipher suite between client and server.
**Triage path**: Check enabled cipher suites on both sides → check TLS version agreement → check key exchange compatibility.
**Common root causes**:
- Server requires TLS 1.3 but wolfSSL compiled without `--enable-tls13`
- ECC cipher suites selected but `--enable-ecc` not enabled
- FIPS build restricts available cipher suites
- `wolfSSL_CTX_set_cipher_list()` too restrictive
**Key code path**: `MatchSuite()` in `src/internal.c`

## Error -313 (ASN_NO_SIGNER_E)
**What it means**: Cannot verify peer certificate — no matching CA in the trust store.
**Triage path**: Check CA loaded → check cert chain order → check intermediate certs → check if self-signed.
**Common root causes**:
- `wolfSSL_CTX_load_verify_locations()` not called or wrong path
- Missing intermediate certificate (server sends leaf only)
- Self-signed cert without `wolfSSL_CTX_set_verify(ctx, SSL_VERIFY_NONE, NULL)`
- Certificate format mismatch (DER loaded as PEM or vice versa)
**Key code path**: `ConfirmSignature()` in `wolfcrypt/src/asn.c`

## Error -397 (SOCKET_PEER_CLOSED_E)
**What it means**: Peer closed the connection during handshake.
**Triage path**: Check server logs → check if server requires client cert → check SNI → check TLS version.
**Common root causes**:
- Server requires SNI but wolfSSL not sending it (need `wolfSSL_UseSNI()`)
- Server requires client certificate (mutual TLS) but none provided
- TLS version mismatch (server only accepts TLS 1.3, client offering 1.2)
- Server firewall/IDS blocking the connection

## TLS 1.3 Specific Issues
- **HelloRetryRequest**: Server may request different key share group. wolfSSL handles automatically unless limited.
- **Pre-Shared Key (PSK)**: `wolfSSL_set_psk_client_callback()` must return key length > 0
- **0-RTT / Early Data**: Enable with `--enable-earlydata`. Server must support it.
- **Post-Handshake Auth**: Enable with `--enable-postauth`. Only TLS 1.3.
- **Key Update**: `wolfSSL_update_keys()` for rekeying after handshake.

## Handshake State Machine
```
ClientHello → ServerHello → [Certificate] → [CertificateVerify] → Finished
                                                                      ↓
                                                              Application Data
```
TLS 1.3 reduces round trips: 1-RTT (full), 0-RTT (resumption with early data).

## TLS 1.2 / 1.3 Handshake Path Asymmetry

The TLS 1.2 handshake (`DoHandShakeMsg` in `src/internal.c`) and TLS 1.3
handshake (`DoTls13HandShakeMsg` in `src/tls13.c`) are **independent code
paths** that evolve separately. A retry condition, error guard, or
`pendingMsg` preservation fix in one path does NOT imply the other path
has (or needs) the same fix. When working on handshake message processing:

1. **Check both paths** — read `DoHandShakeMsg` AND `DoTls13HandShakeMsg`
   to see if the bug exists in one or both
2. **Don't assume symmetry** — the `#ifdef` guards, retry conditions, and
   fragmentation handling diverge between paths
3. **Retry-condition changes** — when adding a new retriable error code
   (e.g., `OCSP_WANT_READ`, `WANT_WRITE`) to the handshake message
   handler, check whether the `pendingMsg` buffer is preserved on that
   return path so the fragmented message can be resumed

## Debugging Handshake Failures
1. Enable debug: `wolfSSL_Debugging_ON()` (compile with `--enable-debug`)
2. Check the last alert: `wolfSSL_get_alert_history(ssl, &alert_history)`
3. Get error detail: `wolfSSL_get_error(ssl, ret)` → `wolfSSL_ERR_error_string()`
4. Packet capture: compare with expected TLS flow
5. Check wolfSSL version: some issues fixed in later releases
