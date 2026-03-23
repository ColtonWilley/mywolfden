---
paths:
  - "repos/osp/**/net-snmp/**"
---

# Net-SNMP — External Platform Summary

## Current State
Net-SNMP is the standard open-source SNMP implementation providing `snmpd` (agent), `snmptrapd` (trap handler), and client tools. SNMPv3 supports TLS and DTLS transports (RFC 6353) for encrypted management traffic. Net-SNMP uses OpenSSL for these crypto operations.

## Architecture
- **TLS/DTLS transport**: `snmplib/transports/snmpTLSTCPDomain.c` and `snmpDTLSUDPDomain.c` implement TLS/DTLS transports using OpenSSL APIs.
- **OpenSSL usage**: `snmplib/openssl/` contains OpenSSL-specific helpers. `snmplib/snmp_openssl.c` wraps crypto operations for SNMPv3 USM (User-based Security Model).
- **Build system**: autoconf. `configure.ac` detects OpenSSL via `--with-openssl`.

## wolfSSL Integration Notes
- wolfSSL integrates via `--with-wolfssl` configure flag (requires OSP patches from `osp/net-snmp/`).
- wolfSSL must be built with: `--enable-opensslextra --enable-opensslall --enable-dtls --enable-des3 --enable-md5` (SNMPv3 USM uses legacy algorithms).
- DTLS is critical: SNMPv3 over UDP requires DTLS. Ensure `--enable-dtls` and `--enable-dtls13` for full support.
- USM authentication uses HMAC-MD5 and HMAC-SHA1 — these are legacy but required for SNMP compatibility. Enable with `--enable-md5 --enable-sha`.
- USM privacy uses DES and AES — enable `--enable-des3 --enable-aes`.
- Certificate-based authentication (RFC 6353): Uses X.509 certs for transport security. wolfSSL's cert handling works but verify chain validation with `wolfSSL_CTX_load_verify_locations()`.
- Common issue: Net-SNMP uses `EVP_*` APIs extensively for USM crypto. wolfSSL's `--enable-opensslall` is needed for complete EVP coverage.
- FIPS: SNMPv3 in government networks may require FIPS mode. Note that MD5 and DES are not FIPS-approved — only AES+SHA USM configurations work in FIPS mode.

## Key Files
- `snmplib/transports/snmpTLSTCPDomain.c` — TLS transport implementation
- `snmplib/transports/snmpDTLSUDPDomain.c` — DTLS transport implementation
- `snmplib/snmp_openssl.c` — OpenSSL crypto wrappers for USM
- `snmplib/openssl/` — OpenSSL-specific helper code
- `configure.ac` — Build configuration with SSL detection
