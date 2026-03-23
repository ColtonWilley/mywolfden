---
paths:
  - "repos/wolfclu/**"
  - "**/wolfclu/**"
  - "**/wolfClu/**"
---

# wolfCLU Patterns

## Overview
wolfCLU (wolfSSL Command Line Utility) is a command-line tool that provides OpenSSL CLI-compatible operations using wolfCrypt as the underlying crypto engine. The binary is invoked as `wolfssl` and supports key generation, certificate creation, encryption/decryption, hashing, benchmarking, TLS client/server testing, and PKCS operations. It is useful for customers who want to replace `openssl` CLI usage with a wolfSSL-backed equivalent.

## Build and Installation
- **Prerequisites**: autoconf, automake, libtool
- wolfSSL must be built and installed first with `--enable-wolfclu`
- Additional wolfSSL configure flags may be needed depending on the operations required (see Build Dependencies below)
- After wolfSSL is installed, build wolfCLU from its own source directory:
```
cd wolfclu
./autogen.sh
./configure
make
make check
sudo make install
sudo ldconfig
```
- Use `--with-wolfssl=/path/to/wolfssl` if wolfSSL is installed in a non-default location
- Windows: Visual Studio solution provided in `ide/winvs/`; copy `user_settings.h` from `wolfclu/ide/winvs/` to `wolfssl/IDE/WIN/` before building

## Supported Commands
The `wolfssl` binary accepts these subcommands (no dash prefix, OpenSSL-style):
- **genkey** — Generate RSA, ECC, Ed25519, ML-DSA (Dilithium), XMSS, XMSS^MT key pairs
- **req** — Create certificate signing requests (CSRs) and self-signed certificates
- **ca** — Sign CSRs with a CA key, create Chimera (dual-algorithm) certificates
- **x509** — Parse and display X.509 certificates
- **verify** — Verify certificates against a CA
- **enc** — Symmetric encryption/decryption (AES-CBC, AES-CTR, 3DES, Camellia)
- **dgst** — Digest signing and verification
- **hash/md5/sha256/sha384/sha512** — Compute hashes
- **bench** — Benchmark wolfCrypt algorithms
- **pkey** — Public key operations
- **pkcs7/pkcs8/pkcs12** — PKCS format operations
- **ecparam** — EC parameter generation
- **s_client/s_server** — TLS client and server testing
- **rand** — Random data generation
- **dhparam/dsaparam** — DH/DSA parameter generation
- **base64** — Base64 encode/decode
- **crl** — CRL verification

## Key Generation Examples
```
# RSA 2048-bit key pair (PEM)
wolfssl genkey rsa -size 2048 -out mykey -outform pem -output KEY

# ECC key pair (PEM)
wolfssl genkey ecc -out ecckey -output priv -outform PEM

# ECC with specific curve
wolfssl genkey ecc -name secp384r1 -out ecckey -output priv -outform PEM

# Ed25519 key pair
wolfssl genkey ed25519 -out edkey -outform der -output KEYPAIR

# ML-DSA (Dilithium) key pair — requires --enable-dilithium in wolfSSL
wolfssl genkey ml-dsa -level 3 -out mldsakey -output keypair -outform PEM
```

## Certificate Operations
```
# Self-signed certificate from an existing private key
wolfssl req -new -days 3650 -key mykey.priv -out server.cert -x509

# CSR with subject fields
wolfssl req -new -key ecckey.priv -subj O=MyOrg/C=US/ST=WA/L=Seattle/CN=example.com -out my.csr -outform PEM

# CA signing a CSR
wolfssl ca -in my.csr -keyfile ca.priv -cert ca.cert -out signed.cert

# Verify a certificate against a CA
wolfssl verify -CAfile ca.cert signed.cert
```

## Encryption and Decryption
```
# Encrypt a file with AES-256-CBC (password-based)
wolfssl enc -aes-256-cbc -in plaintext.txt -out encrypted.bin -k "password"

# Decrypt
wolfssl enc -d -aes-256-cbc -in encrypted.bin -out decrypted.txt -k "password"

# Base64-encoded output with PBKDF2 key derivation
wolfssl enc -base64 -pbkdf2 -aes-256-cbc -in data.bin -out data.enc -k "password"

# Password via -pass flag
wolfssl enc -base64 -d -aes-256-cbc -pass 'pass:my password' -in data.enc -out data.dec
```
- Supports both OpenSSL-style names (`-aes-256-cbc`) and legacy names (`-aes-cbc-256`)
- Encryption/decryption is interoperable with OpenSSL CLI when using compatible settings

## Signing and Verification
```
# Sign a file with SHA-256 digest
wolfssl dgst -sha256 -sign mykey.priv -out file.sig ./document.txt

# Verify the signature
wolfssl dgst -sha256 -verify mykey.pub -signature file.sig ./document.txt
```

## Benchmarking
```
wolfssl bench -aes-cbc -time 1
wolfssl bench -sha -time 1
```

## Common Issues

### Missing wolfSSL Configure Flags
wolfCLU requires `--enable-wolfclu` when building wolfSSL. Specific features need additional flags:
- Key generation: `--enable-keygen`
- Encryption tests: `--enable-pwdbased --enable-opensslextra`
- Camellia: `--enable-camellia`
- 3DES: `--enable-des3`
- ML-DSA/Dilithium: `--enable-dilithium --enable-experimental`
- Chimera certs: `--enable-dilithium --enable-dual-alg-certs --enable-experimental`
- XMSS: `--enable-xmss --enable-experimental`

### Library Not Found at Runtime
After installing wolfSSL, run `sudo ldconfig` to update the linker cache. Without this, wolfCLU will fail with shared library errors even though the build succeeded.

### Legacy Command Syntax
wolfCLU supports both dash-prefixed (`wolfssl -x509`) and bare subcommand (`wolfssl x509`) syntax for backward compatibility. The bare form (no dash) matches OpenSSL CLI conventions and is preferred.

### FIPS Mode
When linked against a FIPS-validated wolfSSL build, wolfCLU includes an integrity check callback. If the FIPS in-core hash fails, all crypto operations will error. The fix is to recompile wolfSSL with the correct integrity hash. Contact fips@wolfssl.com for persistent issues.

### FreeRTOS / Embedded Use
wolfCLU can be built for FreeRTOS targets. In that mode, `clu_entry()` replaces `main()` and parses commands received over UART. Filesystem support can be disabled with `--disable-filesystem` at configure time.
