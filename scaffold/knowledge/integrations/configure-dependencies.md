# Configure Flag Dependencies

> One-line summary: which `--enable-X` flags require companion flags, and what breaks when you forget one.

**When to read**: Building wolfSSL for use with a specific integration (curl, nginx, OpenSSH, etc.) or diagnosing missing-symbol / feature-not-available errors after configure.

---

## Integration Flag Dependency Table

| Flag | Required Companions | Optional | Notes |
|------|-------------------|----------|-------|
| `--enable-curl` | `--enable-opensslextra --enable-alpn --enable-sni --enable-ocsp` | `--enable-crl --enable-sessioncerts` | Add `--enable-ipv6` if curl needs IPv6 |
| `--enable-nginx` | `--enable-opensslextra --enable-opensslall --enable-ocsp --enable-session-issue --enable-sni` | `--enable-alpn` (HTTP/2), `--enable-certgen` | nginx >= 1.23 may need `--enable-ecccustcurves` for P-384/P-521 |
| `--enable-openvpn` | `--enable-opensslextra --enable-des3 --enable-sha512 --enable-fortress` | `--enable-crl --enable-certgen` | OpenVPN 2.6+ needs `--enable-ecccustcurves` for ECDH |
| `--enable-haproxy` | `--enable-opensslextra --enable-opensslall --enable-alpn --enable-sni --enable-ocsp` | `--enable-session-issue` | |
| `--enable-stunnel` | `--enable-opensslextra --enable-des3 --enable-fortress` | `--enable-crl` | |
| `--enable-openssh` | `--enable-opensslextra --enable-dsa --enable-aescfb` | | OpenSSH 9.x dropped DSA by default, but wolfSSL configure still needs it for key parsing compat |
| `--enable-strongswan` | `--enable-opensslextra --enable-des3 --enable-keygen --enable-sha512` | `--enable-rsapss` (IKEv2 sig auth) | |
| `--enable-lighty` | `--enable-opensslextra --enable-sni --enable-ocsp` | | |
| `--enable-bind` | `--enable-opensslextra --enable-sha512` | | |
| `--enable-apache-httpd` | `--enable-opensslextra --enable-opensslall --enable-alpn --enable-sni --enable-ocsp --enable-session-issue` | | |
| `--enable-mosquitto` | `--enable-opensslextra --enable-sni` | | |
| `--enable-mariadb` | `--enable-opensslextra --enable-opensslall --enable-certgen` | | |

## Common Flag Clusters

| Purpose | Flags |
|---------|-------|
| Full OpenSSL compat layer | `--enable-opensslextra --enable-opensslall --enable-certgen --enable-certreq --enable-certext --enable-crl --enable-ocsp --enable-session-issue --enable-sni --enable-alpn` |
| TLS 1.3 only (minimal) | `--enable-tls13 --disable-oldtls --enable-hkdf --enable-ecccustcurves` |
| FIPS 140-2/140-3 base | `--enable-fips=v5 --enable-sha512 --enable-keygen --enable-rsapss --enable-aesccm` |
| Embedded / no filesystem | `--enable-singlethreaded --enable-smallstack --disable-filesystem --enable-certgen --enable-certreq CFLAGS="-DNO_FILESYSTEM"` |
| DTLS (IoT / CoAP) | `--enable-dtls --enable-dtls13 --enable-sessioncerts --enable-psk` |

## Platform Flags

| Flag | Constraint | Notes |
|------|-----------|-------|
| `--enable-armasm` | Requires ARM NEON; use `--host=aarch64-linux-gnu` | Mutually exclusive with `--enable-intelasm` |
| `--enable-intelasm` | Requires x86_64 with AES-NI | Mutually exclusive with `--enable-armasm` |
| `--enable-sp-asm` | Requires correct `--host` for target arch | SP math is default since wolfSSL 5.0 |
| `--enable-caam` | Requires `WOLFSSL_IMX6_CAAM` or `WOLFSSL_IMX6UL_CAAM` in `user_settings.h` | Must also set `WOLFSSL_CAAM` + correct `CAAM_*` SoC module defines |
| `--enable-cryptocb` | No companions, but must call `wc_CryptoCb_RegisterDevice()` before use | Used for HW offload (ATECC508A, ST33, TPM) |

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| Missing `EVP_*` symbols at link time | `--enable-opensslextra` omitted | `configure.ac` flag handling |
| ALPN not negotiated (HTTP/2 falls back to 1.1) | `--enable-alpn` omitted from wolfSSL build | `wolfssl/openssl/ssl.h` |
| P-384/P-521 curves rejected | `--enable-ecccustcurves` missing | ECC curve table in `wolfcrypt/src/ecc.c` |
| OpenSSH build errors on `BN_*` symbols | `--enable-opensslextra` missing | `wolfssl/openssl/bn.h` |
| FIPS self-test failure | Wrong flag combination with `--enable-fips` | Always follow the FIPS User Guide exactly |
| `--enable-armasm` + `--enable-intelasm` both set | Mutually exclusive; build will fail or produce wrong code | `configure.ac` platform detection |

## What This File Does NOT Cover

- Basic autotools usage or `./configure --help` output
- Runtime API usage or programming patterns
- FIPS certificate scope details (see FIPS User Guide)
- Per-integration build instructions for the external project itself
