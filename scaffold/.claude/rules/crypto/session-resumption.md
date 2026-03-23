---
paths:
  - "**/ssl.c"
  - "**/session*"
---

# Session Resumption Patterns

## Session Cache (TLS 1.2)
- Enabled by default (server-side session cache)
- `wolfSSL_CTX_set_session_cache_size()` to configure
- `wolfSSL_get_session()` / `wolfSSL_set_session()` for client-side reuse
- `NO_SESSION_CACHE` to disable (saves ~2KB per context)

## Session Tickets (TLS 1.2 and 1.3)
- Enable: `--enable-session-ticket` or `#define HAVE_SESSION_TICKET`
- Server encrypts session state into ticket sent to client
- Client sends ticket on reconnect → server decrypts → resume
- No server-side state required (scalable)
- `wolfSSL_CTX_set_TicketEncCtx()` for custom ticket encryption key

## TLS 1.3 PSK Resumption
- TLS 1.3 uses PSK (Pre-Shared Key) for resumption, not session IDs
- NewSessionTicket message sent post-handshake
- `wolfSSL_SESSION_get_ticket()` to extract ticket
- Multiple tickets may be issued per connection
- `wolfSSL_CTX_set_psk_client_callback()` for external PSK (non-resumption)

## 0-RTT (Early Data)
- Enable: `--enable-earlydata` or `#define WOLFSSL_EARLY_DATA`
- Client sends data with ClientHello (no round-trip wait)
- **Security risk**: replay attacks possible — server must handle carefully
- `wolfSSL_write_early_data()` / `wolfSSL_read_early_data()`
- Server: `wolfSSL_CTX_set_max_early_data()` to set max early data size

## Common Issues
- **Session not resuming**: check ticket/session expiry, check both sides enable session tickets
- **Performance not improving**: resumption saves one round-trip in TLS 1.2, less benefit in TLS 1.3 (already 1-RTT)
- **Memory on embedded**: session cache uses memory per-entry; consider `NO_SESSION_CACHE` + tickets
- **Ticket key rotation**: server should rotate ticket encryption keys periodically for forward secrecy
