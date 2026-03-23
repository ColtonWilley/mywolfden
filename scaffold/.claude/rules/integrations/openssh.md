---
paths:
  - "repos/osp/**/openssh/**"
---

# OpenSSH — External Platform Summary

## Current State

- **Upstream project**: Portable OpenSSH (port of OpenBSD's OpenSSH to Linux, macOS, Cygwin, and other Unix-like systems)
- **Latest source reference**: `ssh.c` revision `1.628` (2026/03/05), `sshkey.c` revision `1.161` (2026/02/06) — actively maintained
- **Build system**: Autoconf/make; `configure` script generated via `autoreconf`
- **Crypto library support**: OpenSSH accepts `libcrypto` from LibreSSL, OpenSSL, AWS-LC, or BoringSSL as drop-in providers; wolfSSL integration is provided via the wolfSSL OSP patch set, which presents a wolfSSL-backed `libcrypto`-compatible interface
- **SSH protocol**: SSH-2 only; SSH-1 has been removed
- **Key types supported**: RSA, DSA (deprecated), ECDSA (P-256/P-384/P-521), ED25519, FIDO/SK variants, and certificate variants of each
- **Optional dependencies**: zlib (compression), libfido2 (FIDO2/U2F tokens), PAM, Kerberos/GSSAPI, SELinux, libedit

---

## Architecture

### Crypto Abstraction Layers

OpenSSH does not call OpenSSL APIs directly throughout the codebase. Instead, it uses internal abstraction layers that isolate crypto operations:

| Layer | Files | Purpose |
|---|---|---|
| Digest abstraction | `digest-openssl.c` / `digest-builtin.c` | Hash functions (SHA-1/256/512, MD5) |
| Cipher abstraction | `cipher.c` | Symmetric encryption (AES-CTR, AES-GCM, ChaCha20-Poly1305) |
| Key abstraction | `sshkey.c` | Key generation, serialization, signing, verification |
| MAC abstraction | `mac.c` | HMAC and ETM MAC computation |
| KEx abstraction | `kex*.c` | Key exchange (DH, ECDH, curve25519, MLKem/hybrid PQ) |

The `WITH_OPENSSL` preprocessor guard controls whether OpenSSL-backed or built-in implementations are compiled. wolfSSL integration targets the `WITH_OPENSSL` path.

### Key Type Handling in `sshkey.c`

- ED25519 is handled via `crypto_api.h` / `crypto_api.c` (a bundled, self-contained implementation derived from SUPERCOP), **not** through OpenSSL EVP. This means ED25519 operations bypass the OpenSSL abstraction layer entirely.
- ECDSA keys use `openssl/evp.h` and `openssl/bn.h` directly within `#ifdef WITH_OPENSSL` blocks.
- RSA and DSA keys similarly depend on OpenSSL BN/EVP APIs.
- Private key file format uses `bcrypt` KDF with `aes256-ctr` cipher and SHA-512 digest for key shielding (`SSHKEY_SHIELD_CIPHER`, `SSHKEY_SHIELD_PREKEY_HASH`).

### Connection and Protocol Flow

```
ssh.c / sshd.c
    └── packet.c          (SSH packet framing, encryption/MAC)
        └── cipher.c      (symmetric crypto)
        └── mac.c         (integrity)
    └── kex*.c            (key exchange, calls into sshkey.c and digest.c)
    └── sshkey.c          (host/user key operations)
        └── digest-openssl.c  (hashing via OpenSSL EVP_MD)
        └── openssl EVP/BN    (RSA, ECDSA)
        └── crypto_api.c      (ED25519, standalone)
```

---

## wolfSSL Integration Notes

### Build System

- wolfSSL OSP provides a patch set applied on top of the OpenSSH source tree
- wolfSSL must be built with `--enable-openssh` (or equivalent options) to expose the required OpenSSL-compatibility API surface
- The `configure` invocation for OpenSSH must point to the wolfSSL-provided `libcrypto` shim:
  ```
  ./configure --with-ssl-dir=/path/to/wolfssl/openssl-compat ...
  ```
- `WITH_OPENSSL` must be defined; the build must not fall back to the built-in crypto path
- For FIPS mode: wolfSSL must be built as a FIPS-validated module (`--enable-fips`); the OpenSSH build itself has no FIPS-specific configure flag — FIPS enforcement is entirely within wolfSSL

### ED25519 Key Support

- **Critical issue**: ED25519 in OpenSSH uses `crypto_api.c` (bundled NaCl/ref10 implementation), which is **independent of the OpenSSL/wolfSSL layer**. wolfSSL does not replace this code path by default.
- The OSP patch may redirect ED25519 operations through wolfSSL's EVP layer or wc_* APIs; verify which approach the specific patch version uses.
- If the patch routes ED25519 through wolfSSL, ensure wolfSSL is compiled with `--enable-ed25519` and, for FIPS builds, confirm ED25519 is within the FIPS boundary (ED25519 is **not** FIPS-approved; connections using `ssh-ed25519` host/user keys will fail or must be disabled in FIPS mode).

### ECDSA Key Support

- ECDSA uses OpenSSL EVP/EC APIs; wolfSSL's OpenSSL compatibility layer must implement `EVP_PKEY`, `EC_KEY`, `ECDSA_SIG`, and related BN functions
- Supported curves: P-256 (`nistp256`), P-384 (`nistp384`), P-521 (`nistp521`)
- Ensure wolfSSL is built with `--enable-ecc` and the required curve sizes (`--enable-eccsi` not needed; standard ECC suffices)
- In FIPS mode, P-521 may require explicit enablement depending on the FIPS boundary definition

### FIPS Mode Compatibility

- FIPS-incompatible algorithms that must be disabled or will fail at runtime:
  - `ssh-ed25519` / `ecdsa-sha2-nistp256` with SHA-1 (check specific FIPS boundary)
  - `arcfour` (RC4) — already removed from modern OpenSSH
  - `hmac-md5` variants
  - `diffie-hellman-group1-sha1` (1024-bit DH)
  - `chacha20-poly1305@openssh.com` — ChaCha20 is **not** FIPS-approved; this cipher must be excluded from `Ciphers` in `sshd_config`/`ssh_config`
- Restrict algorithms in configuration:
  ```
  Ciphers aes128-ctr,aes192-ctr,aes256-ctr,aes128-gcm@openssh.com,aes256-gcm@openssh.com
  MACs hmac-sha2-256,hmac-sha2-512
  KexAlgorithms ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group14-sha256
  HostKeyAlgorithms ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,rsa-sha2-256,rsa-sha2-512
  ```

### Common Integration Issues

| Issue | Cause | Resolution |
|---|---|---|
| Link errors on `EVP_MD_CTX_*` or `EVP_CIPHER_CTX_*` | wolfSSL compat layer missing functions | Ensure wolfSSL built with `--enable-opensslextra --enable-opensslall` |
| ED25519 key generation/auth fails | `crypto_api.c` path not patched or wolfSSL ED25519 not enabled | Check OSP patch applies `crypto_api` redirect; build wolfSSL with `--enable-ed25519` |
| `chacha20-poly1305` negotiated in FIPS mode causes abort | wolfSSL FIPS rejects ChaCha20 | Explicitly remove from `Ciphers` list in config |
| `BN_*` symbol undefined | BN (big number) compat not compiled | Add `--enable-opensslextra` to wolfSSL build |
| ECDSA signature verification fails | Curve not enabled in wolfSSL | Verify `--enable-ecc` and check curve bitsize support |
| `ssh-keygen` fails on RSA key generation | `RSA_generate_key_ex` not mapped | Confirm wolfSSL RSA keygen compat functions are present |
| FIPS self-test failure at startup | wolfSSL FIPS module not correctly linked or integrity check fails | Verify FIPS object file hash and linker order per wolfSSL FIPS documentation |

---

## Key Files

### OpenSSH Source Files

| File | Role |
|---|---|
| `configure.ac` | Autoconf build configuration; crypto library detection logic |
| `config.h` (generated) | Defines `WITH_OPENSSL`, `HAVE_EVP_*`, and other feature flags |
| `ssh.c` | SSH client entry point; includes `openssl/evp.h` under `WITH_OPENSSL` |
| `sshd.c` | SSH server entry point |
| `sshkey.c` | All key type handling; central file for ED25519/ECDSA/RSA key ops |
| `cipher.c` | Symmetric cipher abstraction over OpenSSL EVP |
| `digest-openssl.c` | Hash abstraction using `EVP_MD_CTX`; active when `WITH_OPENSSL` defined |
| `digest-builtin.c` | Fallback hash implementation when OpenSSL not present |
| `crypto_api.c` / `crypto_api.h` | Bundled ED25519 implementation (NaCl-derived); **bypasses OpenSSL layer** |
| `kex.c`, `kexecdh.c`, `kexdh.c` | Key exchange implementations |
| `mac.c` | HMAC/MAC abstraction |
| `openbsd-compat/openssl-compat.h` | Compatibility shims for OpenSSL API version differences |
| `ssh_config` / `sshd_config` | Runtime algorithm configuration (critical for FIPS restriction) |

### wolfSSL OSP Patch Files (typical)

| File | Role |
|---|---|
| `openssh-patches/openssh-*.patch` | Main OSP diff; modifies `configure.ac`, `Makefile.in`, and crypto files |
| wolfSSL `wolfssl/openssl/` headers | OpenSSL API compatibility headers consumed by OpenSSH |
| wolfSSL `src/ssl.c` | Implementation of OpenSSL-compat EVP, BN, ECDSA, RSA functions |

### Configuration Points

- **`sshd_config` / `ssh_config`**: `Ciphers`, `MACs`, `KexAlgorithms`, `HostKeyAlgorithms` — must be restricted for FIPS compliance
- **wolfSSL build flags**: `--enable-openssh`, `--enable-opensslextra`, `--enable-ecc`, `--enable-ed25519`, `--enable-fips` (FIPS builds)
- **`configure` flag**: `--with-ssl-dir` pointing to wolfSSL installation prefix
- **`WOLFSSL_USER_SETTINGS`** or `user_settings.h`: May be required to enable specific algorithm support when using wolfSSL in embedded/custom configurations
