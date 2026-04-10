# FIPS Integration

> One-line summary: integrity test triage, CAST failure diagnosis, algorithm restrictions by FIPS version, and configure ordering requirements.

**When to read**: Debugging FIPS startup failures, checking algorithm availability under FIPS, or setting up a FIPS build.

---

## Integrity Test Triage

**Error**: `wolfCrypt FIPS integrity test failed` at startup.

The HMAC-SHA256 hash of the FIPS boundary code does not match the expected value in `fips.c`.

| Check | Detail |
|-------|--------|
| Code recompiled? | Hash must be regenerated after ANY code change within the FIPS boundary |
| Linker alignment | `wolfcrypt_first` and `wolfcrypt_last` must bracket FIPS code in contiguous memory |
| Linker script | FIPS code must be in a contiguous memory section |
| Strip/debug info | Can shift code addresses, invalidating hash |
| PIE/ASLR | Hash is computed on relocated code — check `verifyCore` logic in `fips.c` |

**Key file**: `fips.c` in the fips repo — contains expected hash and verification logic.

## CAST Failure Triage

**Error**: Specific algorithm returns failure on first use (Conditional Algorithm Self Test / Known Answer Test failed).

| Check | Detail |
|-------|--------|
| Hardware crypto interference | Disable HW accel temporarily to isolate |
| Memory corruption | Is the KAT reference data in `fips_test.c` intact? |
| Endianness | New platform may byte-swap KAT vectors |

**Key file**: `fips_test.c` — contains all KAT vectors.

## Algorithm Restrictions by FIPS Version

| Algorithm | FIPS v2 (140-2) | FIPS v5 (140-3) | FIPS v6 (140-3) |
|-----------|:---------------:|:---------------:|:---------------:|
| AES-CBC/GCM | Yes | Yes | Yes |
| RSA 2048 | Yes | Yes | Yes |
| RSA 1024 | Verify only | No | No |
| ECC P-256/P-384 | Yes | Yes | Yes |
| SHA-1 | Yes | Verify only | Verify only |
| SHA-256 | Yes | Yes | Yes |
| SHA-3 | No | Yes | Yes |
| HMAC | Yes | Yes | Yes |
| DRBG | Yes | Yes | Yes |
| EdDSA | No | No | Yes |
| ML-KEM/ML-DSA | No | No | Yes (v6+) |

## DRBG / Entropy Requirements

- FIPS requires NIST SP 800-90A DRBG (Hash_DRBG or HMAC_DRBG)
- `CUSTOM_RAND_GENERATE_SEED` must provide SP 800-90B compliant entropy
- Continuous Random Number Generator Test (CRNGT): identical consecutive outputs trigger FIPS failure
- `ForceZero()` must not be optimized away — key zeroization is a FIPS requirement

## Platform Pain Points

| Platform | Issue |
|----------|-------|
| ESP32 | Very tight memory; careful buffer management required |
| iOS | Fat binary (arm64 + simulator) requires separate hashes per architecture |
| Android | NDK + position-independent code complicates integrity test |
| Windows | DLL boundary issues; must control linking order |
| Linux kernel module | Different build system for in-kernel crypto module |

## Configure Ordering

The FIPS version flag must come early and determines which algorithms are available:

```bash
./configure --enable-fips=v5   # or v6
```

The FIPS repo must be checked out at the correct commit/tag matching the wolfSSL version. Integrity hash must be regenerated after any code change within the FIPS boundary.

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| Startup crash with "integrity test failed" | Code changed without regenerating FIPS hash | `fips.c` `verifyCore` |
| Algorithm returns error on first use | CAST/KAT failure — HW accel or endianness issue | `fips_test.c` |
| DRBG produces FIPS error after extended run | CRNGT detected identical consecutive outputs | DRBG in `random.c` |
| FIPS build links but hash never matches | `wolfcrypt_first`/`wolfcrypt_last` not bracketing correctly | Linker script |

## What This File Does NOT Cover

- FIPS certification process or paperwork
- General FIPS education (what FIPS 140-2/3 is)
- Detailed entropy source implementation guidance
- Non-wolfSSL FIPS modules
