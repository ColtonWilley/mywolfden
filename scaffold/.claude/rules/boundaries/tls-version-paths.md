---
paths:
  - "**/tls.c"
  - "**/tls13.c"
  - "**/internal.c"
---

# TLS 1.2 / 1.3 Path Independence

## The Rule

TLS 1.2 (`DoHandShakeMsg` in `src/internal.c`) and TLS 1.3
(`DoTls13HandShakeMsg` in `src/tls13.c`) are **independent code paths**.

- A fix in one path does NOT imply the other has (or needs) the same fix
- The `#ifdef` guards, retry conditions, and fragmentation handling diverge
- Existing TLS 1.2 support for a feature does NOT mean any TLS 1.3
  infrastructure exists — they are separately implemented

## When Working on Handshake Code

1. Check BOTH paths — read `DoHandShakeMsg` AND `DoTls13HandShakeMsg`
2. Don't assume symmetry
3. When adding retriable error codes, verify `pendingMsg` buffer is
   preserved on that return path

## HRR State Preservation Pattern

HelloRetryRequest fixes require three coordinated changes in `tls13.c`:
1. **Save** cipher suite to dedicated fields at HRR send time
   (`SendTls13ServerHello`)
2. **Restore** from cookie data for stateless DTLS path
   (`RestartHandshakeHashWithCookie`)
3. **Validate** against CH2 after `MatchSuite` completes
   (`DoTls13ClientHello`)

Note: `MatchSuite()` overwrites `ssl->options.cipherSuite` during
negotiation — you cannot compare against it directly. Use dedicated
saved fields.
