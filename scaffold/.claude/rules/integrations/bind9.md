---
paths:
  - "repos/osp/**/bind/**"
---

# ISC BIND9 — External Platform Summary

## Current State
BIND9 is the most widely deployed DNS server. Recent versions support DNS-over-TLS (DoT) and DNS-over-HTTPS (DoH), making the TLS library choice operationally significant. BIND9 uses OpenSSL APIs for both TLS transport and DNSSEC cryptographic operations.

## Architecture
- **TLS transport**: `lib/isc/tls.c` manages TLS contexts for DoT/DoH listeners and forwarders. Uses OpenSSL's `SSL_CTX` API.
- **DNSSEC crypto**: `lib/dns/openssl_link.c` initializes OpenSSL for DNSSEC signature verification. Individual algorithm implementations in `lib/dns/opensslrsa_link.c`, `lib/dns/opensslecdsa_link.c`, etc.
- **Build system**: `configure.ac` detects OpenSSL. wolfSSL plugs in via the OpenSSL compatibility layer.

## wolfSSL Integration Notes
- wolfSSL integrates via OSP (Open Source Project) patches maintained in the `osp` repo under `bind/`.
- wolfSSL must be built with: `--enable-bind --enable-opensslextra --enable-opensslall --enable-curve25519 --enable-curve448 --enable-ed25519 --enable-ed448`.
- DNSSEC requires broad algorithm support: RSA, ECDSA (P-256, P-384), EdDSA (Ed25519, Ed448). All must be enabled.
- BIND9 uses `EVP_DigestSign`/`EVP_DigestVerify` APIs — these require wolfSSL's `--enable-opensslall` for full EVP coverage.
- DoT/DoH uses session resumption and ALPN — both supported by wolfSSL but verify `--enable-alpn` is set.
- FIPS mode: BIND9 can run in FIPS mode. wolfSSL FIPS bundle supports this but requires the FIPS-validated build.
- Common issue: BIND9 checks OpenSSL version macros. wolfSSL's `OPENSSL_VERSION_NUMBER` may need to match expectations — OSP patches handle this.

## Key Files
- `lib/isc/tls.c` — TLS context management (DoT/DoH)
- `lib/dns/openssl_link.c` — OpenSSL initialization for DNSSEC
- `lib/dns/opensslrsa_link.c` — RSA DNSSEC operations
- `lib/dns/opensslecdsa_link.c` — ECDSA DNSSEC operations
- `configure.ac` — Build-time SSL detection
