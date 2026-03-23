---
paths:
  - "**/kyber*"
  - "**/dilithium*"
  - "**/*.S"
---

# Post-Quantum Cryptography Assembly Optimizations

## ML-KEM (Kyber) Implementation

ML-KEM (Module-Lattice-Based Key Encapsulation Mechanism), formerly known as CRYSTALS-Kyber, is standardized as FIPS 203. wolfSSL implements all three parameter sets:

- **ML-KEM-512** — NIST Security Level 1 (128-bit classical equivalent)
- **ML-KEM-768** — NIST Security Level 3 (192-bit classical equivalent)
- **ML-KEM-1024** — NIST Security Level 5 (256-bit classical equivalent)

wolfSSL has hand-optimized assembly for ML-KEM on **four platforms**: x86_64, ARM64, ARM32, and Thumb2. This is unusually broad — most PQC libraries only optimize for x86_64.

The x86_64 implementation uses AVX2 to process multiple polynomial coefficients in parallel using 256-bit SIMD registers. The ARM implementations use NEON or optimized scalar code appropriate to each architecture. The Thumb2 implementation targets Cortex-M microcontrollers for embedded PQC deployments.

The core performance-critical operations are:
- **NTT (Number Theoretic Transform)** — Converts polynomials to frequency domain for fast multiplication. This is the dominant cost in ML-KEM.
- **Inverse NTT** — Converts back to coefficient domain
- **Polynomial arithmetic** — Addition, subtraction, modular reduction
- **Compression/decompression** — Encoding polynomials for transmission

## ML-DSA (Dilithium) Implementation

ML-DSA (Module-Lattice-Based Digital Signature Algorithm), formerly CRYSTALS-Dilithium, is standardized as FIPS 204. wolfSSL implements all three parameter sets:

- **ML-DSA-44** — NIST Security Level 2
- **ML-DSA-65** — NIST Security Level 3
- **ML-DSA-87** — NIST Security Level 5

Assembly optimization for ML-DSA is currently **x86_64 only**. The implementation uses AVX2 for NTT and polynomial operations, with both ATT assembly (`.S`) and MSVC assembly (`.asm`) output formats. ARM platforms use the C reference implementation.

ML-DSA has additional operations beyond NTT that benefit from assembly:
- **Rejection sampling** — Generating random polynomials with specific distributions
- **Hint computation** — For signature compression
- **Modular reduction** — Barrett reduction replaces division for constant-time operation

## NTT Optimization Details

The Number Theoretic Transform is the performance bottleneck for both ML-KEM and ML-DSA. It is analogous to the FFT (Fast Fourier Transform) but operates over finite fields instead of complex numbers.

**Why NTT dominates performance:**
Each ML-KEM encapsulation/decapsulation requires multiple NTT and inverse NTT operations. For ML-KEM-768, this means operating on polynomials of degree 256 with 12-bit coefficients, performed multiple times per operation.

**How AVX2 helps:**
AVX2 provides 256-bit SIMD registers that can hold 16 x 16-bit coefficients. This allows processing 16 NTT butterfly operations in parallel versus 1 in scalar code. The butterfly operation (multiply, add, subtract, reduce) maps naturally to SIMD instructions.

**Constant-time guarantees:**
All assembly implementations use Barrett reduction (not division) and constant-time comparison. There are no secret-dependent branches or memory accesses. This prevents timing side-channel attacks.

## Platform Support Summary

```
Operation                 x86_64 (AVX2)   ARM64   ARM32   Thumb2   C fallback
─────────────────────     ─────────────   ─────   ─────   ──────   ──────────
ML-KEM keygen              Y               Y       Y       Y        Y (all)
ML-KEM encapsulate         Y               Y       Y       Y        Y (all)
ML-KEM decapsulate         Y               Y       Y       Y        Y (all)
ML-DSA sign                Y               -       -       -        Y (all)
ML-DSA verify              Y               -       -       -        Y (all)
ML-DSA keygen              Y               -       -       -        Y (all)
```

All platforms have a C reference implementation as fallback. The C implementation is fully functional and correct but slower than the assembly-optimized versions.

## Configure Flags

**ML-KEM (Kyber):**
- `--enable-kyber` — Enable ML-KEM support
- `WOLFSSL_WC_KYBER` — Use wolfCrypt's native implementation (not liboqs)
- `WOLFSSL_NO_KYBER512`, `WOLFSSL_NO_KYBER768`, `WOLFSSL_NO_KYBER1024` — Disable specific parameter sets to reduce code size
- `WOLFSSL_KYBER_NO_MAKE_KEY`, `WOLFSSL_KYBER_NO_ENCAPSULATE`, `WOLFSSL_KYBER_NO_DECAPSULATE` — Disable specific operations for constrained builds

**ML-DSA (Dilithium):**
- `--enable-dilithium` — Enable ML-DSA support
- `WOLFSSL_DILITHIUM_NO_SIGN`, `WOLFSSL_DILITHIUM_NO_VERIFY` — Disable specific operations
- `WOLFSSL_DILITHIUM_SMALL` — Smaller code size at cost of speed

**TLS integration:**
- ML-KEM is used for TLS 1.3 key exchange via hybrid key shares (e.g., X25519 + ML-KEM-768)
- ML-DSA is used for TLS 1.3 authentication via post-quantum certificate signatures

## Common Questions

**"Is PQC FIPS certified?"**
ML-KEM (FIPS 203) and ML-DSA (FIPS 204) are finalized NIST standards. wolfSSL's FIPS 140-3 validation for these algorithms is in progress. Check wolfSSL's FIPS status page for current certification state.

**"Can I use PQC on ARM/embedded?"**
Yes. ML-KEM has assembly-optimized implementations for ARM64, ARM32, and Thumb2 (Cortex-M). ML-DSA has C implementations for all platforms. For constrained devices, use the `NO_` and `SMALL` defines to reduce code/memory footprint.

**"How much slower is C vs assembly for PQC?"**
Approximately 3-5x for NTT-heavy operations. ML-KEM-768 keygen + encapsulate on x86_64 with AVX2 takes ~50-100 microseconds versus ~200-400 microseconds in C. On ARM64, the gap is smaller (2-3x) due to efficient NEON utilization.

**"Is the PQC code constant-time?"**
Yes. Both assembly and C implementations use Barrett reduction instead of division, constant-time comparison, and no secret-dependent branches. This applies across all platforms and parameter sets.

**"Can I use liboqs instead of wolfCrypt's native PQC?"**
wolfSSL supports both `WOLFSSL_WC_KYBER` (native, with assembly optimizations) and a liboqs backend. The native implementation is recommended for production as it benefits from wolfSSL's assembly optimizations and has been through wolfSSL's security review process.
