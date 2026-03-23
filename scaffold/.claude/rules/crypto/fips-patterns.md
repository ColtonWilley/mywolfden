---
paths:
  - "**/fips.c"
  - "**/fips_test.c"
  - "**/wolfcrypt_first*"
  - "**/wolfcrypt_last*"
  - "repos/fips/**"
---

# FIPS 140-2/3 Patterns (Beyond Prompt Section)

## Common FIPS Issues

### Integrity Test Failure
**Error**: "wolfCrypt FIPS integrity test failed" at startup.
**Root cause**: HMAC-SHA256 hash of FIPS boundary code doesn't match expected value.
**Triage path**:
1. Was the code recompiled? Hash must be regenerated after any code change
2. Linker alignment: `wolfcrypt_first` and `wolfcrypt_last` must bracket FIPS code
3. Check linker script: FIPS code must be in contiguous memory section
4. Strip/debug info can shift code addresses
5. PIE/ASLR: hash is computed on relocated code — check `verifyCore` logic
**Key file**: `fips.c` in the fips repo — contains the expected hash and verification logic

### CAST Failure (Conditional Algorithm Self Test)
**Error**: Specific algorithm returns failure on first use.
**Root cause**: Known Answer Test (KAT) for that algorithm failed.
**Triage path**:
1. Check if hardware crypto is interfering (disable HW accel temporarily)
2. Memory corruption: is the KAT reference data intact?
3. Endianness issues on new platforms
**Key file**: `fips_test.c` — contains all KAT vectors

### FIPS + Platform Combinations
**Common painful combos**:
- FIPS + ESP32: very tight memory, need careful buffer management
- FIPS + iOS: fat binary (arm64 + simulator) requires separate hashes per architecture
- FIPS + Android: NDK build with position-independent code complicates integrity test
- FIPS + Windows: DLL boundary issues, need to control linking order
- FIPS + Linux kernel module: in-kernel crypto module, different build system

### Algorithm Restrictions by FIPS Version

| Algorithm | FIPS v2 (140-2) | FIPS v5 (140-3) | FIPS v6 (140-3) |
|-----------|----------------|-----------------|-----------------|
| AES-CBC | Yes | Yes | Yes |
| AES-GCM | Yes | Yes | Yes |
| RSA 2048 | Yes | Yes | Yes |
| RSA 1024 | Verify only | No | No |
| ECC P-256 | Yes | Yes | Yes |
| ECC P-384 | Yes | Yes | Yes |
| SHA-1 | Yes | Verify only | Verify only |
| SHA-256 | Yes | Yes | Yes |
| SHA-3 | No | Yes | Yes |
| HMAC | Yes | Yes | Yes |
| DRBG | Yes | Yes | Yes |
| EdDSA | No | No | Yes |

### DRBG / Entropy Issues
- FIPS requires NIST SP 800-90A DRBG (Hash_DRBG or HMAC_DRBG)
- Entropy source must meet SP 800-90B requirements
- `CUSTOM_RAND_GENERATE_SEED` must provide sufficient entropy
- MemUse entropy: compile-time option for entropy from memory usage patterns
- Continuous Random Number Generator Test (CRNGT): same output twice → FIPS failure

## FIPS Build Checklist
1. Correct `--enable-fips=v5` or `v6` version
2. FIPS repo checked out at correct commit/tag
3. Linker script includes FIPS boundary markers
4. Integrity hash regenerated after any code change
5. Entropy source validated (hardware RNG or SP 800-90B compliant)
6. Algorithm self-tests passing (run wolfCrypt test program)
7. Key zeroization working (check `ForceZero()` not optimized away)
8. No non-approved algorithms called in FIPS mode
