---
paths:
  - "**/dtls*.c"
  - "**/dtls*.h"
---

# DTLS (Datagram TLS) Patterns

## Overview
DTLS adapts TLS for unreliable datagram transport (UDP). wolfSSL supports DTLS 1.0, 1.2, and 1.3.
- Enable: `--enable-dtls` (DTLS 1.0/1.2), `--enable-dtls13` (DTLS 1.3)
- API: same as TLS but use `wolfDTLSv1_2_client_method()` etc.

## Common DTLS Issues

### Handshake Timeout / Retransmission
**Symptom**: Handshake takes very long or fails with timeout.
**Root cause**: DTLS retransmits handshake messages on timeout. If UDP packets are being dropped, retransmissions increase exponentially.
**Fix**: Check UDP connectivity, adjust timeout with `wolfSSL_dtls_set_timeout_init()`.
- Default initial timeout: 1 second, max: 64 seconds (doubles each retry)
- `wolfSSL_dtls_set_timeout_max()` to cap retransmission timeout

### MTU / Fragmentation
**Symptom**: Handshake fails with large certificates (RSA 4096, long cert chains).
**Root cause**: Certificate message exceeds UDP MTU → DTLS fragments, but fragments may be lost.
**Fix**:
- Set MTU: `wolfSSL_dtls_set_mtu()` (default ~1500)
- Use ECC certs (much smaller than RSA)
- Reduce cert chain length
- DTLS handles fragmentation internally but it's less reliable than TCP fragmentation

### Cookie Exchange (DoS Protection)
- DTLS uses HelloVerifyRequest with cookie for DoS protection
- Server: `wolfSSL_CTX_SetGenCookie()` to set cookie generation callback
- Client: must handle HelloVerifyRequest (automatic in wolfSSL)
- **Common issue**: Stateless server behind load balancer losing cookie context

### Connection ID (CID) — DTLS 1.2+
- Enable: `--enable-dtls-cid` or `#define WOLFSSL_DTLS_CID`
- Allows connections to survive IP/port changes (common in mobile/IoT)
- RFC 9146 (DTLS 1.2 CID), built into DTLS 1.3
- `wolfSSL_dtls_cid_use()` to enable on a connection

### Custom I/O Callbacks and Timeout Interaction
**Symptom**: `wolfSSL_dtls_set_timeout_init()` / `wolfSSL_dtls_set_timeout_max()` have no effect; retransmission timing doesn't match configured values. Receive callback may be called twice in quick succession before the first retransmit fires (DTLS 1.3).
**Root cause**: When custom I/O callbacks are registered (`WOLFSSL_USER_IO`), the application owns all I/O behavior including timing. The timeout APIs update `ssl->dtls_timeout` internally, but the built-in `EmbedReceiveFrom` is bypassed — if the custom callback uses its own wait logic, library timeout state is never consulted.
**Key APIs for custom callbacks**:
- `wolfSSL_dtls_get_current_timeout(ssl)` — returns current timeout in seconds (respects init/max/exponential backoff). Custom blocking callbacks should use this as their wait duration.
- `wolfSSL_dtls13_use_quick_timeout(ssl)` — DTLS 1.3 only. Returns true when the library wants a shorter wait (typically 1/4 of current timeout) before triggering retransmission. The built-in callback checks this; custom callbacks must check it too or they'll see an unexpected "double call" before the first retransmit.
- `wolfSSL_dtls13_set_send_more_acks(ssl, 1)` — disables the fast timeout optimization entirely. Use when the customer's callback already handles retransmission timing and the library's optimization competes with it.
- Blocking callbacks: return `WOLFSSL_CBIO_ERR_TIMEOUT` on timeout. Non-blocking: return `WOLFSSL_CBIO_ERR_WANT_READ` and call `wolfSSL_dtls_got_timeout(ssl)` externally.

## DTLS 1.3 Specifics
- Requires both `--enable-dtls` and `--enable-dtls13`
- ACK-based reliability (replaces DTLS 1.2 retransmission)
- Unified header format for smaller overhead
- Connection ID built-in (no separate extension)
- 0-RTT / early data support

## DTLS vs TLS Differences
| Aspect | TLS | DTLS |
|--------|-----|------|
| Transport | TCP (reliable) | UDP (unreliable) |
| Handshake | Sequential | Retransmission + fragmentation |
| Record ordering | Guaranteed | Sequence numbers, reorder handled |
| DoS protection | TCP backlog | Cookie exchange |
| Message size | Unlimited (TCP segmentation) | Limited by MTU |
| Connection migration | IP change = new connection | CID enables migration |

## Algorithm Dependencies

**DTLS 1.2 requires MD5 and SHA-1.** The TLS 1.2 PRF (pseudo-random function) uses a split construction: `P_MD5(secret, label+seed) XOR P_SHA-1(secret, label+seed)`. Even when using SHA-256-based cipher suites like `TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256`, the PRF itself still needs both MD5 and SHA-1 for the legacy P_MD5 and P_SHA-1 halves.

- `NO_MD5` will break DTLS 1.2 handshakes — the PRF computation will fail
- `NO_SHA` will break DTLS 1.2 and most certificate chain verification (SHA-1 signatures on intermediate CAs are still common)
- **General rule:** when enabling a protocol version (`WOLFSSL_DTLS`, `WOLFSSL_TLS13`), verify its mandatory algorithm dependencies are not disabled. TLS 1.3 uses HKDF (requires SHA-256 minimum), while TLS 1.2/DTLS 1.2 additionally require MD5 and SHA-1 for the PRF.

**DTLS 1.3** uses the TLS 1.3 key schedule (HKDF), which does NOT require MD5 — only SHA-256 or SHA-384. If MD5 is unacceptable, consider DTLS 1.3 (`--enable-dtls13`) instead of DTLS 1.2.

## Common DTLS Use Cases
- IoT/CoAP: `--enable-dtls` + `--enable-dtls-cid` for constrained devices
- VoIP/WebRTC: low-latency requirement makes DTLS preferred over TLS
- VPN: UDP-based VPN tunnels
