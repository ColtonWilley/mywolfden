---
paths:
  - "**/configure.ac"
  - "**/configure"
---

# Configure Flag Dependencies

Cross-reference of `--enable-X` flags and their required companion flags.
Each integration expects certain wolfSSL features to be compiled in.

## Integration Flags

### --enable-curl
Requires: `--enable-opensslextra --enable-alpn --enable-sni --enable-ocsp`
Optional: `--enable-crl --enable-sessioncerts` (for verbose certificate info)
Note: curl also needs `--enable-ipv6` if building with IPv6 support.

### --enable-nginx
Requires: `--enable-opensslextra --enable-opensslall --enable-ocsp --enable-session-issue --enable-sni`
Optional: `--enable-alpn` (for HTTP/2), `--enable-certgen` (for dynamic certs)
Note: nginx >= 1.23 may need `--enable-ecccustcurves` for P-384/P-521.

### --enable-openvpn
Requires: `--enable-opensslextra --enable-des3 --enable-sha512 --enable-fortress`
Optional: `--enable-crl --enable-certgen`
Note: OpenVPN 2.6+ requires `--enable-ecccustcurves` for ECDH.

### --enable-haproxy
Requires: `--enable-opensslextra --enable-opensslall --enable-alpn --enable-sni --enable-ocsp`
Optional: `--enable-session-issue`

### --enable-stunnel
Requires: `--enable-opensslextra --enable-des3 --enable-fortress`
Optional: `--enable-crl`

### --enable-openssh
Requires: `--enable-opensslextra --enable-dsa --enable-aescfb`
Note: OpenSSH 9.x dropped DSA by default, but wolfSSL configure still needs it for key parsing compatibility.

### --enable-strongswan
Requires: `--enable-opensslextra --enable-des3 --enable-keygen --enable-sha512`
Optional: `--enable-rsapss` (for IKEv2 signature auth)

### --enable-lighty (lighttpd)
Requires: `--enable-opensslextra --enable-sni --enable-ocsp`

### --enable-bind (BIND/named)
Requires: `--enable-opensslextra --enable-sha512`

### --enable-apache-httpd
Requires: `--enable-opensslextra --enable-opensslall --enable-alpn --enable-sni --enable-ocsp --enable-session-issue`

### --enable-mosquitto
Requires: `--enable-opensslextra --enable-sni`

### --enable-mariadb
Requires: `--enable-opensslextra --enable-opensslall --enable-certgen`

## Platform Flags

### --enable-caam (NXP CAAM)
Requires: `WOLFSSL_IMX6_CAAM` or `WOLFSSL_IMX6UL_CAAM` define in `user_settings.h`
Note: Must also set `WOLFSSL_CAAM` and the correct `CAAM_*` module defines for the SoC variant.

### --enable-cryptocb (Crypto Callbacks)
Requires: No companion flags, but must register callbacks via `wc_CryptoCb_RegisterDevice()` before use.
Note: Used for hardware crypto offload (ATECC508A, ST33, TPM, etc.).

### --enable-armasm (ARM NEON/Crypto Extensions)
Requires: ARM compiler with NEON support. Cross-compile with `--host=aarch64-linux-gnu`.
Note: Mutually exclusive with `--enable-intelasm`.

### --enable-intelasm (Intel AES-NI / AVX)
Requires: x86_64 target with AES-NI support.
Note: Mutually exclusive with `--enable-armasm`.

### --enable-sp-asm (SP Math Assembly)
Requires: Correct `--host` for target architecture. Available for ARM, x86_64, ARM Thumb.
Note: SP math is the default since wolfSSL 5.0. Use `--enable-sp-math-all` for all key sizes.

## Common Flag Clusters

### Full OpenSSL Compatibility Layer
```
--enable-opensslextra --enable-opensslall --enable-certgen --enable-certreq
--enable-certext --enable-crl --enable-ocsp --enable-session-issue
--enable-sni --enable-alpn
```

### TLS 1.3 Only (Minimal)
```
--enable-tls13 --disable-oldtls --enable-hkdf --enable-ecccustcurves
```

### FIPS 140-2/140-3 Base
```
--enable-fips=v5 --enable-sha512 --enable-keygen --enable-rsapss --enable-aesccm
```
Note: FIPS modules have strict flag requirements. Always follow the FIPS User Guide.

### Embedded Minimal (No Filesystem)
```
--enable-singlethreaded --enable-smallstack --disable-filesystem
--enable-certgen --enable-certreq CFLAGS="-DNO_FILESYSTEM"
```

### DTLS (IoT / CoAP)
```
--enable-dtls --enable-dtls13 --enable-sessioncerts --enable-psk
```
