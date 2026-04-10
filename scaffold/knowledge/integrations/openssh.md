# OpenSSH + wolfSSL Integration

> One-line summary: how OpenSSH's crypto abstraction layers map to wolfSSL, the ED25519 bypass issue, and FIPS algorithm restrictions.

**When to read**: Building OpenSSH with wolfSSL via OSP patches, debugging key/cipher failures, or restricting algorithms for FIPS compliance.

---

## Crypto Abstraction Layer Mapping

OpenSSH does not call OpenSSL directly throughout the codebase. It uses internal abstractions controlled by the `WITH_OPENSSL` preprocessor guard. wolfSSL integration targets the `WITH_OPENSSL` path.

| Layer | Key Files | What It Wraps |
|-------|-----------|---------------|
| Digest | `digest-openssl.c` / `digest-builtin.c` | SHA-1/256/512, MD5 via `EVP_MD_CTX` |
| Cipher | `cipher.c` | AES-CTR, AES-GCM, ChaCha20-Poly1305 |
| Key | `sshkey.c` | Key gen, serialization, signing, verification |
| MAC | `mac.c` | HMAC and ETM MAC computation |
| KEx | `kex*.c` (`kexecdh.c`, `kexdh.c`) | DH, ECDH, curve25519, post-quantum hybrid |

## The ED25519 Bypass Issue

**Critical**: ED25519 in OpenSSH uses `crypto_api.c` / `crypto_api.h` -- a bundled NaCl/ref10 implementation that is **completely independent of the OpenSSL/wolfSSL layer**. wolfSSL does not replace this code path by default.

- The OSP patch may redirect ED25519 through wolfSSL's EVP layer or `wc_*` APIs -- verify which approach the specific patch version uses.
- If routed through wolfSSL, ensure `--enable-ed25519` is set.
- For FIPS builds: ED25519 is **not FIPS-approved**. Connections using `ssh-ed25519` host/user keys will fail or must be disabled in FIPS mode.

## OSP Patch Approach

wolfSSL integration is delivered as a patch set applied on top of the OpenSSH source tree (from the `osp` repo):

- Patch modifies `configure.ac`, `Makefile.in`, and crypto source files
- `configure` invocation must point to wolfSSL's libcrypto compat: `./configure --with-ssl-dir=/path/to/wolfssl/openssl-compat`
- `WITH_OPENSSL` must be defined; the build must not fall back to built-in crypto
- For FIPS: wolfSSL must be built as a FIPS module (`--enable-fips`); OpenSSH itself has no FIPS configure flag -- enforcement is entirely within wolfSSL

## wolfSSL Build Flags for OpenSSH

| Flag | Purpose |
|------|---------|
| `--enable-openssh` | Activates `WOLFSSL_OPENSSH` define and required compat shims |
| `--enable-opensslextra` | Base OpenSSL API compat (`EVP_*`, `BN_*`) |
| `--enable-opensslall` | Extended compat surface (may be needed for some EVP functions) |
| `--enable-ecc` | ECDSA support (P-256, P-384, P-521) |
| `--enable-ed25519` | ED25519 if OSP patch routes through wolfSSL |
| `--enable-dsa` | Required for key parsing compat even though OpenSSH 9.x dropped DSA by default |
| `--enable-aescfb` | Required by `--enable-openssh` |
| `--enable-fips` | FIPS builds only |

## FIPS Algorithm Restrictions

These must be excluded from `sshd_config` / `ssh_config` in FIPS mode:

| Algorithm | Why |
|-----------|-----|
| `chacha20-poly1305@openssh.com` | ChaCha20 not FIPS-approved |
| `ssh-ed25519` | ED25519 not FIPS-approved |
| `hmac-md5` variants | MD5 not FIPS-approved for HMAC |
| `diffie-hellman-group1-sha1` | 1024-bit DH not FIPS-approved |

**FIPS-safe config example**:
```
Ciphers aes128-ctr,aes192-ctr,aes256-ctr,aes128-gcm@openssh.com,aes256-gcm@openssh.com
MACs hmac-sha2-256,hmac-sha2-512
KexAlgorithms ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group14-sha256
HostKeyAlgorithms ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,rsa-sha2-256,rsa-sha2-512
```

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| Link errors on `EVP_MD_CTX_*` / `EVP_CIPHER_CTX_*` | wolfSSL compat layer missing functions | Build wolfSSL with `--enable-opensslextra --enable-opensslall` |
| ED25519 key gen/auth fails | `crypto_api.c` not patched or wolfSSL ED25519 not enabled | Check OSP patch applies `crypto_api` redirect; `--enable-ed25519` |
| `chacha20-poly1305` negotiated in FIPS causes abort | wolfSSL FIPS rejects ChaCha20 | Remove from `Ciphers` in config |
| `BN_*` symbols undefined | Big number compat not compiled | `--enable-opensslextra` |
| ECDSA signature verification fails | Curve not enabled in wolfSSL | `--enable-ecc`; check curve bitsize support |
| `ssh-keygen` fails on RSA key gen | `RSA_generate_key_ex` not mapped | Confirm wolfSSL RSA keygen compat present |
| FIPS self-test failure at startup | FIPS module not correctly linked or integrity check fails | Verify FIPS object file hash and linker order per wolfSSL FIPS docs |
| P-521 ECDSA rejected in FIPS | Curve may need explicit enablement | Check FIPS boundary definition for P-521 |

## Key OpenSSH Source Files

| File | Role |
|------|------|
| `sshkey.c` | All key type handling; central for ED25519/ECDSA/RSA ops |
| `crypto_api.c` / `crypto_api.h` | Bundled ED25519 (NaCl-derived); **bypasses OpenSSL layer** |
| `digest-openssl.c` | Hash abstraction via `EVP_MD_CTX`; active when `WITH_OPENSSL` defined |
| `cipher.c` | Symmetric cipher abstraction over OpenSSL EVP |
| `openbsd-compat/openssl-compat.h` | Compat shims for OpenSSL API version differences |
| `sshd_config` / `ssh_config` | Runtime algorithm config (critical for FIPS restriction) |

## What This File Does NOT Cover

- OpenSSH installation or general SSH usage
- Non-wolfSSL crypto backends (LibreSSL, BoringSSL, AWS-LC)
- wolfssh (wolfSSL's own SSH implementation, a separate product)
- Detailed FIPS certification boundary documentation
