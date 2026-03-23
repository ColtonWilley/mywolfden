---
paths:
  - "**/*.S"
  - "**/sp_*.c"
---

# Assembly-Optimized Algorithms by Platform

## Instruction Set Summary

wolfSSL's assembly generators target specific hardware instruction sets for maximum performance:

**x86_64 (Intel/AMD):**
- **AES-NI** — Hardware AES encryption/decryption in a single instruction. Available on most Intel (since Westmere 2010) and AMD (since Bulldozer 2011) processors.
- **AVX / AVX2** — 256-bit SIMD registers. AVX2 adds integer operations to 256-bit registers. Used for ChaCha20, Poly1305, SHA-256/512, SHA-3, and ML-KEM NTT operations.
- **SHA Extensions** — Hardware SHA-256 acceleration (Intel Goldmont+, AMD Zen).
- **PCLMULQDQ** — Carry-less multiplication for AES-GCM's GHASH computation.

**ARM64 (ARMv8/AArch64):**
- **NEON** — 128-bit SIMD, always available on ARMv8. Used for ChaCha20, Poly1305, and general-purpose vectorization.
- **Crypto Extensions** — Hardware AES, SHA-1, SHA-256. Optional ARMv8 feature, common on Cortex-A53+ and Apple Silicon.
- **SHA-512 / SHA-3 Extensions** — ARMv8.2 additions for hardware SHA-512 and SHA-3.

**ARM32 (ARMv7):**
- **NEON** — 128-bit SIMD on Cortex-A series (A7, A9, A15, etc.). Not available on Cortex-M.

**ARM NEON mnemonic syntax:** NEON instructions use a dot-suffix to specify element size: `.8`, `.16`, `.32`, `.64` (e.g., `vrev32.16` reverses 16-bit elements within 32-bit lanes). Suffixes like `.i16`, `.u16`, `.s16` are type qualifiers used in ARM intrinsics and some documentation but are **not valid in assembly syntax** for all instructions — strict assemblers (particularly newer GNU as versions) may reject `.i16` where only `.16` is valid. When reviewing NEON mnemonic fixes, check whether the suffix change is cosmetic or fixes an actual assembly failure depending on toolchain strictness.

**Thumb2 (ARMv7-M):**
- Optimized for Cortex-M4, M7, M33 using Thumb-2 instruction encoding. No NEON, but efficient use of 32-bit multiply and DSP instructions.

## Algorithm Coverage by Platform

This matrix is derived from the actual generation scripts in the wolfSSL/scripts repository. Each "Y" means hand-optimized assembly exists for that platform.

```
Algorithm          x86_64   ARM64   ARM32   Thumb2   x86(32)
─────────────────  ──────   ─────   ─────   ──────   ───────
AES-GCM/XTS        Y        Y       Y       Y        Y (GCM)
ChaCha20           Y        Y       Y       Y        -
Poly1305           Y        Y       Y       Y        -
SHA-256            Y        Y       Y       Y        -
SHA-512            Y        Y       Y       Y        -
SHA-3              Y        Y       Y       Y        -
X25519/Ed25519     Y        Y       Y       Y        -
ML-KEM (Kyber)     Y        Y       Y       Y        -
ML-DSA (Dilithium) Y        -       -       -        -
Curve448/Ed448     Y        -       -       -        -
SP Math (RSA/DH)   Y        Y       Y       Cortex-M -
SP Math (ECC)      Y        Y       Y       Cortex-M -
```

**Notes:**
- x86_64 has the broadest coverage — every algorithm has optimized assembly
- ARM64, ARM32, and Thumb2 have near-complete coverage (missing only ML-DSA and Curve448)
- x86 32-bit only has AES-GCM assembly; other algorithms use C fallbacks
- SP Math "Cortex-M" includes both Thumb and Thumb2 (Cortex-M4/M7) variants
- PowerPC 32-bit support exists via gen-ppc32.sh (not shown — limited algorithms)

## Configure Flags for Assembly

**Intel x86_64:**
- `--enable-intelasm` — Enables AES-NI, AVX, AVX2 assembly for AES, ChaCha20, Poly1305, SHA, Curve25519
- `--enable-aesni` — AES-NI specifically (subset of intelasm)
- `--enable-sp-asm` — SP math assembly (RSA/DH/ECC)
- Defines: `WOLFSSL_AESNI`, `HAVE_INTEL_AVX1`, `HAVE_INTEL_AVX2`

**ARM:**
- `--enable-armasm` — Enables NEON and Crypto Extension assembly for AES, ChaCha20, Poly1305, SHA, Curve25519
- `--enable-sp-asm` — SP math assembly for ARM64/ARM32/Cortex-M
- Defines: `WOLFSSL_ARMASM`, `WOLFSSL_ARMASM_CRYPTO_SHA512`, `WOLFSSL_ARMASM_CRYPTO_SHA3`

**Cross-platform:**
- `--enable-sp-asm` — Automatically selects the right SP assembly for the detected platform
- Assembly and C implementations coexist — if assembly is enabled but the hardware feature isn't present at runtime, the C fallback is used

## Runtime Feature Detection

**x86_64:** wolfSSL uses CPUID to detect AES-NI, AVX, AVX2, SHA extensions, and PCLMULQDQ at runtime. If a CPU lacks AVX2, the AVX1 or scalar path is used. If AES-NI is absent, the C AES implementation runs instead. This detection is automatic — no user configuration needed.

**ARM64:** Feature detection varies by OS. On Linux, wolfSSL reads `/proc/cpuinfo` or uses `getauxval()`. On Apple Silicon, Crypto Extensions are always present. On bare-metal embedded, features are typically known at compile time via defines.

**ARM32/Thumb2:** On Cortex-M microcontrollers, the target is known at compile time. The correct SP math variant (ARM32, Thumb, or Cortex-M) is selected by configure flags rather than runtime detection.

## Performance Impact

Typical speedup of assembly over C implementations (varies by CPU generation):

- **AES-GCM with AES-NI**: 10-50x over C table-lookup implementation
- **ChaCha20 with AVX2**: 5-8x over scalar C
- **Poly1305 with AVX2**: 5-10x over C
- **SHA-256 with SHA extensions**: 3-8x over C
- **SHA-256 with AVX2**: 2-4x over C (without SHA extensions)
- **RSA-2048 sign with SP x86_64 ASM**: 10-20x over legacy math
- **ECC P-256 sign with SP ASM**: 3-5x over SP C

These speedups compound in TLS: a full handshake involves RSA/ECC for key exchange, AES/ChaCha for bulk encryption, and SHA for hashing. Assembly optimization across all operations can reduce handshake time by an order of magnitude.

## Interaction with FIPS

FIPS 140-2/3 validated builds may require specific assembly configurations. The FIPS boundary includes the assembly code — modifications to generated assembly require re-validation. When building for FIPS, use the exact assembly files from the validated source bundle. Do not regenerate assembly from the scripts repo for FIPS builds.
