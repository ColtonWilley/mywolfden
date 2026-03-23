---
paths:
  - "repos/wolfssh/**"
  - "**/wolfssh/**"
---

# wolfSSH Patterns

## Overview
wolfSSH is an SSHv2 implementation built on wolfCrypt. Supports client and server modes, SFTP, SCP, and SSH agent forwarding.

## Common Issues

### Key Format
- wolfSSH uses its own key format for server host keys
- Convert OpenSSH keys: `ssh-keygen` → DER → load with wolfSSH
- Ed25519, RSA, and ECDSA host keys supported
- **Common mistake**: Loading OpenSSH format directly (need conversion)

### SFTP Transfers Failing
- Buffer sizing: default buffer may be too small for large files
- `wolfSSH_SFTP_SetMaxSendSize()` / `wolfSSH_SFTP_SetMaxRecvSize()` to adjust
- Non-blocking mode: must handle `WS_WANT_READ` / `WS_WANT_WRITE`

### Authentication
- Password auth: `wolfSSH_SetUserAuth()` callback
- Public key auth: `wolfSSH_SetUserAuthPublicKey()` callback
- Keyboard-interactive: `wolfSSH_SetUserAuthKeyboardInteractive()`
- **Common issue**: Auth callback returning wrong value → auth loops or failures

### Build Dependencies
- Requires wolfSSL built with: `--enable-keygen --enable-ssh`
- Or in user_settings.h: `#define WOLFSSL_KEY_GEN`, `#define WOLFSSH_*` defines
- wolfSSH `configure` uses `--with-wolfssl=/path/to/wolfssl` to find wolfSSL
