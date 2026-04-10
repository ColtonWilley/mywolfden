# TLS/DTLS Error Triage

> One-line summary: error-code-to-root-cause mappings for TLS handshake failures, DTLS-specific gotchas, and session resumption failure modes.

**When to read**: Debugging a TLS or DTLS handshake failure, investigating session resumption issues, or triaging a connection error code.

---

## TLS Handshake Error Codes

### Error -308 (SOCKET_ERROR_E)
Socket-level error during handshake.

| Platform | Common Cause |
|----------|-------------|
| ESP32 | Wi-Fi stack drops connection during DH key exchange (memory pressure) |
| FreeRTOS | Task stack overflow during handshake (need 24KB+ for RSA 2048) |
| Windows | Winsock not initialized or firewall closed socket |
| Custom I/O | Callback returning wrong error code (must return `WOLFSSL_CBIO_ERR_*`) |

**Key path**: `wolfSSL_connect()` -> `SendClientHello()` -> `DoServerHello()` in `src/internal.c`

### Error -188 (MATCH_SUITE_ERROR)
No common cipher suite between client and server.

| Cause | Fix |
|-------|-----|
| Server requires TLS 1.3, wolfSSL built without `--enable-tls13` | Add flag |
| ECC suites selected but `--enable-ecc` missing | Add flag |
| FIPS build restricts available suites | Check FIPS algorithm table |
| `wolfSSL_CTX_set_cipher_list()` too restrictive | Widen cipher list |

**Key path**: `MatchSuite()` in `src/internal.c`

### Error -313 (ASN_NO_SIGNER_E)
Cannot verify peer certificate — no matching CA in trust store.

| Cause | Fix |
|-------|-----|
| `wolfSSL_CTX_load_verify_locations()` not called or wrong path | Load CA cert |
| Missing intermediate certificate (server sends leaf only) | Add intermediate |
| DER loaded as PEM or vice versa | Match format |

**Key path**: `ConfirmSignature()` in `wolfcrypt/src/asn.c`

### Error -397 (SOCKET_PEER_CLOSED_E)
Peer closed connection during handshake.

| Cause | Fix |
|-------|-----|
| Server requires SNI but not sent | Call `wolfSSL_UseSNI()` |
| Server requires client cert (mTLS) | Load client cert + key |
| TLS version mismatch | Align versions |

## TLS 1.2 / 1.3 Handshake Path Asymmetry

The TLS 1.2 handshake (`DoHandShakeMsg` in `src/internal.c`) and TLS 1.3 handshake (`DoTls13HandShakeMsg` in `src/tls13.c`) are **independent code paths**. A fix in one does NOT imply the other has (or needs) the same fix.

When working on handshake message processing:
1. **Check both paths** — read both `DoHandShakeMsg` AND `DoTls13HandShakeMsg`
2. **Don't assume symmetry** — `#ifdef` guards, retry conditions, and fragmentation handling diverge
3. **Retry conditions** — when adding a retriable error code (e.g., `OCSP_WANT_READ`), verify `pendingMsg` buffer is preserved on that return path

## DTLS-Specific Gotchas

### Retransmission Timing
- Default initial timeout: 1 second, doubles each retry, max 64 seconds
- `wolfSSL_dtls_set_timeout_init()` / `wolfSSL_dtls_set_timeout_max()` to tune
- Large certs (RSA 4096, long chains) exceed UDP MTU -> fragmented DTLS, unreliable

### Custom I/O Callback Timeout Interaction
When using `WOLFSSL_USER_IO`, the library timeout APIs update `ssl->dtls_timeout` but the built-in `EmbedReceiveFrom` is bypassed. Custom callbacks must:
- Call `wolfSSL_dtls_get_current_timeout(ssl)` for wait duration
- Check `wolfSSL_dtls13_use_quick_timeout(ssl)` (DTLS 1.3) or see double-call before first retransmit
- Return `WOLFSSL_CBIO_ERR_TIMEOUT` (blocking) or `WOLFSSL_CBIO_ERR_WANT_READ` (non-blocking) + call `wolfSSL_dtls_got_timeout(ssl)` externally

### Algorithm Dependencies
**DTLS 1.2 requires MD5 and SHA-1** for the TLS 1.2 PRF split construction, even when using SHA-256-based cipher suites. `NO_MD5` or `NO_SHA` will break DTLS 1.2 handshakes.

**DTLS 1.3** uses HKDF (SHA-256/SHA-384 only) — does NOT require MD5. If MD5 is unacceptable, use `--enable-dtls13`.

### Cookie Exchange
- DTLS uses `HelloVerifyRequest` for DoS protection
- Stateless server behind load balancer can lose cookie context
- `wolfSSL_CTX_SetGenCookie()` for custom cookie generation

### Connection ID (CID)
- Enable: `--enable-dtls-cid` or `WOLFSSL_DTLS_CID`
- Survives IP/port changes (mobile/IoT)
- Built into DTLS 1.3; RFC 9146 for DTLS 1.2

## Session Resumption Failure Modes

| Symptom | Root Cause | Fix |
|---------|------------|-----|
| Session not resuming (TLS 1.2) | Ticket/session expired; one side missing `--enable-session-ticket` | Check expiry, enable on both sides |
| Session not resuming (TLS 1.3) | PSK ticket not extracted via `wolfSSL_SESSION_get_ticket()` | Extract and store NewSessionTicket |
| Memory issues on embedded | Session cache uses memory per-entry | Use `NO_SESSION_CACHE` + tickets |
| Forward secrecy concern | Ticket encryption key not rotated | Rotate keys periodically via `wolfSSL_CTX_set_TicketEncCtx()` |
| 0-RTT rejected by server | Server doesn't support early data or max size exceeded | Check `wolfSSL_CTX_set_max_early_data()`, note replay risk |

## Debugging Checklist

1. Enable debug: `wolfSSL_Debugging_ON()` (compile with `--enable-debug`)
2. Get alert history: `wolfSSL_get_alert_history(ssl, &alert_history)`
3. Get error detail: `wolfSSL_get_error(ssl, ret)` -> `wolfSSL_ERR_error_string()`
4. Packet capture: compare with expected TLS flow

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| -308 on ESP32 during key exchange | Memory pressure drops Wi-Fi during DH | `src/internal.c` |
| -188 with correct cipher list | TLS version disagreement masquerading as suite mismatch | `MatchSuite()` |
| -313 with correct CA loaded | Cert format mismatch (DER vs PEM) | `wolfcrypt/src/asn.c` |
| DTLS handshake timeout with custom I/O | Callback ignores `wolfSSL_dtls_get_current_timeout()` | Custom callback code |
| DTLS 1.2 fails with `NO_MD5` | PRF requires MD5 even for SHA-256 cipher suites | `src/internal.c` PRF |

## What This File Does NOT Cover

- TLS protocol education (what a handshake is, message format descriptions)
- Feature lists for TLS 1.3 (0-RTT, post-handshake auth, key update)
- Certificate parsing or X.509 validation details
- Performance tuning for TLS connections
