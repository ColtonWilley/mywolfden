---
paths:
  - "repos/wolfprovider/**"
  - "**/wolfprovider/**"
  - "**/wolfProvider/**"
---

# wolfProvider / wolfEngine Patterns

## When to Use Which

wolfProvider and wolfEngine solve the same problem -- offloading OpenSSL's cryptography to wolfSSL's implementations -- but target different OpenSSL generations.

- **wolfProvider** is for OpenSSL 3.x. It uses the provider API introduced in OpenSSL 3.0. This is the actively developed product and should be recommended for all new integrations.
- **wolfEngine** is for OpenSSL 1.x (specifically 1.0.2 and 1.1.1). It uses the ENGINE API, which is deprecated in OpenSSL 3.0. wolfEngine is in maintenance mode; customers on OpenSSL 1.x who cannot upgrade should use it.

If a customer asks about "the wolfSSL OpenSSL engine" or "wolfSSL provider," determine their OpenSSL version first. OpenSSL 3.x users need wolfProvider. OpenSSL 1.x users need wolfEngine. Customers on OpenSSL 1.1.1 (EOL December 2023) should be encouraged to upgrade to 3.x with wolfProvider.

## Supported Algorithms

### wolfProvider (OpenSSL 3.x)

| Category | Algorithms |
|----------|------------|
| Digests | MD5, SHA-1, SHA-2 (224/256/384/512, 512/224, 512/256), SHA-3 (224/256/384/512), SHAKE-256 |
| Symmetric | AES-128/192/256 (ECB, CBC, CTR, CFB, CTS, GCM, CCM, Key Wrap), 3DES-CBC |
| MACs | HMAC, CMAC, GMAC |
| KDFs | HKDF, PBKDF2, PKCS12 KDF, TLS 1.3 KDF, TLS1 PRF, KBKDF, KRB5 KDF |
| Random | CTR-DRBG, Hash-DRBG |
| RSA | Sign/Verify (PKCS#1 v1.5, PSS), Encrypt/Decrypt, Keygen |
| DH | Key exchange, Keygen |
| ECC | ECDSA, ECDH, Keygen (P-192, P-224, P-256, P-384, P-521) |
| Curves | X25519, X448 (key exchange), Ed25519, Ed448 (signatures) |

### wolfEngine (OpenSSL 1.x)

wolfEngine supports a subset: SHA-1/2/3, AES (ECB/CBC/CTR/GCM/CCM), 3DES-CBC, RSA, DH, ECC (ECDSA/ECDH, P-192 through P-521), HMAC, CMAC, HKDF, PBKDF2, TLS PRF, DRBG. It does not support Curve25519/448, GMAC, KBKDF, KRB5 KDF, AES-CFB/CTS/Key Wrap, or SHAKE-256. SHA-3 requires OpenSSL 1.1.1+.

## Replace-Default Mode (wolfProvider Only)

Standard provider mode loads wolfProvider alongside OpenSSL's default provider. Applications can still fall back to OpenSSL's native crypto if wolfProvider does not implement an algorithm, or if the app explicitly requests the "default" provider. This means FIPS compliance is not guaranteed.

Replace-default mode patches OpenSSL so that wolfProvider intercepts all provider requests -- including requests for "default", "fips", and "wolfProvider" by name. This makes it impossible for an application to accidentally use non-wolfSSL crypto. It requires applying a patch to the OpenSSL source before building:

```bash
patch -p1 < /path/to/wolfProvider/patches/openssl3-replace-default.patch
```

Replace-default is strongly recommended for FIPS deployments.

## FIPS Integration

wolfProvider's FIPS workflow has two steps:

1. **FIPS Baseline Verification** -- Patch OpenSSL with the FIPS baseline script to disable non-approved algorithms. Run the application's test suite against this restricted OpenSSL to identify FIPS compatibility issues early, before involving the FIPS bundle at all.
2. **Production FIPS Build** -- Build wolfProvider with the actual wolfSSL FIPS bundle and replace-default mode enabled.

### FIPS Restrictions

| Restriction | Requirement |
|-------------|-------------|
| RSA Key Size | 2048 bits minimum |
| SHA-1 Signing | Blocked (verify and hashing still allowed) |
| ECDSA Curves | P-256, P-384, P-521 only (P-192, P-224 blocked) |
| PBKDF2 Password | 14 bytes minimum |
| DH Groups | FFDHE only (MODP blocked) |

### FIPS Bundle Build

The `--fips-check` flag value is derived from the bundle filename. For a bundle named `wolfssl-5.8.4-commercial-fips-linuxv5.7z`, use `--fips-check=linuxv5`. Other examples: `ready`, `v6.0.0`, `linuxv5.2.1`.

```bash
./scripts/build-wolfprovider.sh --distclean
./scripts/build-wolfprovider.sh --replace-default --fips-bundle=/path/to/bundle --fips-check=linuxv5
```

## Build Steps

### wolfProvider (Quick Start)

The build script fetches OpenSSL and wolfSSL automatically: `./scripts/build-wolfprovider.sh`. For manual builds: (1) build OpenSSL 3.x with shared libs, (2) build wolfSSL with `--enable-opensslcoexist`, (3) build wolfProvider with `./autogen.sh && ./configure --with-openssl=/path --with-wolfssl=/path && make`.

### wolfEngine (Quick Start)

Build wolfSSL with `--enable-engine=no-fips` (or `--enable-engine` for FIPS bundles), then build wolfEngine with `./autogen.sh && ./configure --with-openssl=/path --with-wolfssl=/path && make && make check`.

### Critical wolfSSL Configure Flags

`--enable-opensslcoexist` is mandatory for both products. It prevents symbol collisions between wolfSSL and OpenSSL (both define functions like `SHA256_Init`). Omitting it causes linker errors or silent wrong-implementation bugs. For FIPS builds, also required: `-DWOLFSSL_OLD_OID_SUM` (certificate compatibility) and `-DWOLFSSL_DH_EXTRA` (DH key operations).

## Common Issues

### Symbol Conflicts at Link Time

**Symptom:** Duplicate symbol errors mentioning SHA, AES, or RSA functions.
**Cause:** wolfSSL built without `--enable-opensslcoexist`.
**Fix:** Rebuild wolfSSL with `--enable-opensslcoexist`.

### Library Not Found at Runtime

**Symptom:** `error while loading shared libraries: libssl.so.3` or similar.
**Fix:** Set `LD_LIBRARY_PATH` to include the OpenSSL and wolfSSL lib directories, or configure the system linker (`ldconfig`).

### Tests Skipped in Replace-Default Mode

**Symptom:** `make test` reports all tests skipped or does nothing.
**Cause:** Replace-default mode intercepts the test harness's attempt to load OpenSSL's default provider for comparison.
**Fix:** For testing, build with `--enable-replace-default-testing`. This exports internal OpenSSL symbols so the test harness can bypass replace-default interception. Never use this in production.

### FIPS Algorithm Rejected

**Symptom:** `unsupported` or `operation not supported for this keytype` errors.
**Cause:** Application uses a non-FIPS-approved algorithm or parameter (RSA < 2048, P-192, SHA-1 signing, short PBKDF2 password, MODP DH).
**Fix:** Update the application to use FIPS-approved parameters. Run baseline testing first to catch all issues systematically.

### wolfEngine Not Loading

**Symptom:** `ENGINE_by_id("wolfSSL")` returns NULL.
**Cause:** Dynamic engine `.so` not in OpenSSL's engine search path, or wolfEngine built with `--disable-dynamic-engine`.
**Fix:** Verify the `.so` is in the engines directory (`openssl version -e` shows the path). Ensure wolfEngine was built with dynamic engine support (the default).

### Switching Build Configurations

Always run `--distclean` when switching between build modes (e.g., standard to replace-default, or between FIPS bundle versions). Stale build artifacts cause subtle failures.

```bash
./scripts/build-wolfprovider.sh --distclean
./scripts/build-wolfprovider.sh [new options]
```

## Debugging

wolfProvider: build with `--debug` flag (or `--debug --debug-log=/path/to/file` to log to file). Fine-grained log level and component filters can be set in `include/wolfprovider/wp_logging.h` before building.

wolfEngine: enable debug at runtime with `ENGINE_ctrl_cmd(e, "enable_debug", 1, NULL, NULL, 0)`.
