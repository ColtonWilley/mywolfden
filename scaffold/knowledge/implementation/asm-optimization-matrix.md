# Assembly Optimization Matrix

> One-line summary: which algorithms have hand-optimized assembly per platform, configure flags, and runtime detection behavior.

**When to read**: Enabling assembly optimizations, checking platform coverage, or debugging why a platform falls back to C.

---

## Algorithm Coverage by Platform

```
Algorithm           x86_64   ARM64   ARM32   Thumb2   x86(32)
──────────────────  ──────   ─────   ─────   ──────   ───────
AES-GCM/XTS         Y        Y       Y       Y        Y (GCM)
ChaCha20            Y        Y       Y       Y        -
Poly1305            Y        Y       Y       Y        -
SHA-256             Y        Y       Y       Y        -
SHA-512             Y        Y       Y       Y        -
SHA-3               Y        Y       Y       Y        -
X25519/Ed25519      Y        Y       Y       Y        -
ML-KEM (Kyber)      Y        Y       Y       Y        -
ML-DSA (Dilithium)  Y        -       -       -        -
Curve448/Ed448      Y        -       -       -        -
SP Math (RSA/DH)    Y        Y       Y       Cortex-M -
SP Math (ECC)       Y        Y       Y       Cortex-M -
```

x86_64 has broadest coverage. ARM64/ARM32/Thumb2 lack ML-DSA and Curve448.
x86 32-bit only has AES-GCM. SP Math "Cortex-M" includes Thumb and Thumb2 variants.

## Configure Flags

**x86_64 (Intel/AMD):**
- `--enable-intelasm` — AES-NI, AVX/AVX2 for AES, ChaCha20, Poly1305, SHA, Curve25519
- `--enable-aesni` — AES-NI only (subset)
- `--enable-sp-asm` — SP math assembly (RSA/DH/ECC)
- Defines: `WOLFSSL_AESNI`, `HAVE_INTEL_AVX1`, `HAVE_INTEL_AVX2`

**ARM:**
- `--enable-armasm` — NEON + Crypto Extensions for AES, ChaCha20, Poly1305, SHA, Curve25519
- `--enable-sp-asm` — SP math for ARM64/ARM32/Cortex-M
- Defines: `WOLFSSL_ARMASM`, `WOLFSSL_ARMASM_CRYPTO_SHA512`, `WOLFSSL_ARMASM_CRYPTO_SHA3`

**Cross-platform:**
- `--enable-sp-asm` — auto-selects correct SP assembly for detected platform

## Runtime Feature Detection

- **x86_64**: CPUID detects AES-NI, AVX, AVX2, SHA extensions at runtime. Falls back to C automatically.
- **ARM64**: Linux reads `/proc/cpuinfo` or `getauxval()`. Apple Silicon always has Crypto Extensions.
- **ARM32/Thumb2**: features known at compile time — selected by configure flags, not runtime.

## FIPS Constraint

FIPS boundary includes assembly code. Do NOT regenerate assembly from the
scripts repo for FIPS builds — use exact files from the validated source bundle.

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| No speedup after `--enable-intelasm` | CPU lacks AES-NI/AVX2, using C fallback | Check `cpuid` output for feature flags |
| ARM assembly build fails | Crypto Extensions not available on target | Check `WOLFSSL_ARMASM` vs target capabilities |
| FIPS validation invalidated | Regenerated assembly differs from validated | Use exact FIPS bundle assembly files |
| SP math wrong results on Cortex-M | Wrong Thumb/Thumb2 variant selected | Verify `--enable-sp-asm` detects correct target |

## What This File Does NOT Cover

- Inline assembly correctness debugging (see `implementation/compiler-asm-debugging.md`)
- Ruby script generator internals (read `wolfssl/scripts` repo)
- Benchmark methodology or specific performance numbers
