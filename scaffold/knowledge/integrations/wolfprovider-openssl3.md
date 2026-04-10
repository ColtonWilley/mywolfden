# wolfProvider / wolfEngine (OpenSSL Integration)

> One-line summary: wolfProvider (OpenSSL 3.x) vs wolfEngine (1.x), replace-default mode for FIPS, and the opensslcoexist flag that prevents silent wrong-implementation bugs.

**When to read**: Integrating wolfSSL crypto into an OpenSSL-based application, setting up FIPS via OpenSSL provider, or debugging symbol conflicts.

---

## Which Product

| OpenSSL Version | Product | Status |
|-----------------|---------|--------|
| 3.x | **wolfProvider** | Active development |
| 1.x (1.0.2, 1.1.1) | **wolfEngine** | Maintenance only |

OpenSSL 1.1.1 is EOL. New integrations should use wolfProvider + OpenSSL 3.x.

## Replace-Default Mode (wolfProvider)

Standard mode: wolfProvider loads alongside OpenSSL's default provider. Apps
can still accidentally use OpenSSL's native crypto — FIPS not guaranteed.

**Replace-default mode**: patches OpenSSL so wolfProvider intercepts ALL
provider requests ("default", "fips", "wolfProvider"). Impossible to
accidentally use non-wolfSSL crypto.

```bash
patch -p1 < wolfProvider/patches/openssl3-replace-default.patch
./scripts/build-wolfprovider.sh --replace-default
```

**Strongly recommended for FIPS deployments.**

## Critical Build Flag: --enable-opensslcoexist

**Mandatory** for both products. Prevents symbol collisions (both wolfSSL and
OpenSSL define `SHA256_Init`, etc.). Without it: linker errors or silent
wrong-implementation bugs.

## FIPS Restrictions

| Parameter | FIPS Requirement |
|-----------|-----------------|
| RSA key size | 2048 bits minimum |
| SHA-1 signing | Blocked (verify/hash still allowed) |
| ECDSA curves | P-256, P-384, P-521 only |
| PBKDF2 password | 14 bytes minimum |
| DH groups | FFDHE only (MODP blocked) |

FIPS bundle build: `--fips-bundle=/path/to/bundle --fips-check=<tag>` where
tag is derived from bundle filename (e.g., `linuxv5` from `wolfssl-5.8.4-commercial-fips-linuxv5.7z`).

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| Duplicate symbol errors (SHA, AES, RSA) | wolfSSL built without `--enable-opensslcoexist` | Rebuild with the flag |
| `libssl.so.3` not found at runtime | Library path not set | `LD_LIBRARY_PATH` or `ldconfig` |
| All tests skipped in replace-default | Test harness can't load default provider | Build with `--enable-replace-default-testing` (dev only) |
| `unsupported` / `operation not supported` | Non-FIPS algorithm or parameter | Check FIPS restriction table above |
| `ENGINE_by_id("wolfSSL")` returns NULL | wolfEngine `.so` not in engines dir | Check path via `openssl version -e` |
| Stale artifacts after config switch | Didn't distclean between builds | Always `--distclean` when switching modes |

## What This File Does NOT Cover

- OpenSSL compat layer in wolfSSL itself (see `crypto/openssl-compat-migration.md`)
- wolfSSL FIPS build without OpenSSL (see `crypto/fips-integration.md`)
- Algorithm-level API details
