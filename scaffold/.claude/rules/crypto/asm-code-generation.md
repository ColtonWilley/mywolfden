---
paths:
  - "**/*.S"
  - "**/sp.rb"
  - "**/gen-sp*"
---

# wolfSSL Assembly Code Generation

## The Scripts Repository

wolfSSL maintains a private repository (`wolfSSL/scripts`) containing Ruby scripts that generate hand-optimized assembly code for cryptographic operations. The generators are written and maintained by Sean Parkinson, wolfSSL's assembly optimization expert.

The key insight: rather than writing assembly by hand for each platform, wolfSSL uses Ruby as a domain-specific language (DSL) for code generation. Each algorithm has a Ruby script that understands the mathematical operations required and emits platform-specific optimized assembly. This approach allows:
- One algorithmic implementation to target multiple architectures
- Consistent application of side-channel countermeasures across platforms
- Systematic optimization (SIMD, instruction scheduling) via architecture-aware Ruby classes

The generated assembly files are **checked into the wolfSSL source tree** — they are not generated at build time. Users building wolfSSL never need the scripts repo or Ruby installed.

## Cross-Variant Bug Propagation

Because each Ruby generator emits the same algorithm for multiple platforms, a bug found in one output file (e.g., wrong source register in `sp_arm32.c` Montgomery reduction) likely exists in sibling outputs from the same generator. The SP math variants share algorithmic structure:

- `sp_arm32.c`, `sp_arm64.c`, `sp_cortexm.c`, `sp_armthumb.c` — all from `sp/sp.rb`
- `sp_x86_64_asm.S` / `sp_x86_64_asm.asm` — also from `sp/sp.rb` (x86_64 target)

**Investigation pattern:** When reviewing a fix in any generated file, identify which generator produced it (check `gen-*.sh` scripts), then check all other output files from the same generator for the analogous bug. Register-use bugs (wrong source/dest register, missing clobber) are algorithmic — they originate in the generator logic, not in platform-specific output formatting.

## Repository Structure

The scripts repo contains algorithm-specific directories, each with a Ruby generator:

- **`aes/aes.rb`** — AES-GCM, AES-XTS (all platforms)
- **`chacha/chacha.rb`** — ChaCha20 stream cipher
- **`poly1305/poly1305.rb`** — Poly1305 MAC
- **`sha2/sha256.rb`, `sha2/sha512.rb`** — SHA-256, SHA-512
- **`sha3/sha3.rb`** — SHA-3 / Keccak
- **`x25519/x25519.rb`** — X25519/Ed25519 field arithmetic
- **`kyber/kyber.rb`** — ML-KEM (Kyber) post-quantum KEM
- **`mldsa/mldsa.rb`** — ML-DSA (Dilithium) post-quantum signatures
- **`curve448/`** — Curve448/Ed448 field and group element generators
- **`sp/sp.rb`** — Single Precision math (RSA, DH, ECC — the largest generator suite)

## Architecture Framework

The `asm/` directory provides portable architecture abstractions:

- **`asm/x86_64/`** — x86-64: register management, AVX/AVX2 instruction encoding, ATT + MSVC output
- **`asm/arm64/`** — ARMv8/AArch64: NEON, Crypto Extensions, SHA extensions
- **`asm/arm32/`** — ARMv7: NEON, basic instruction set
- **`asm/thumb2/`** — ARM Thumb-2: 16/32-bit mixed encoding (Cortex-M4/M7)
- **`asm/ppc32/`** — PowerPC 32-bit

Each architecture module provides Ruby classes for registers, instructions, and output formatting. Algorithm generators use these abstractions to emit correct platform-specific code.

## Output Formats

Each generator can produce multiple output formats from the same algorithm logic:

- **ATT assembly** (`.S` files) — For GCC/Clang on Linux/macOS. Used by the autoconf build system.
- **MSVC assembly** (`.asm` files) — For Microsoft's assembler (MASM) on Windows.
- **C inline assembly** (`.c` files) — For platforms where standalone assembly isn't practical. Uses `__asm__` blocks within C functions.

The format is determined by the platform argument and the architecture's output module.

## Regeneration Workflow

Assembly is regenerated using orchestration shell scripts:

```
./gen-x64.sh     # Intel x86_64: AES, ChaCha, Poly1305, SHA-2/3, X25519, ML-KEM, ML-DSA
./gen-arm64.sh   # ARM64: AES, ChaCha, Poly1305, SHA-2/3, X25519, ML-KEM
./gen-arm32.sh   # ARM32: AES, ChaCha, Poly1305, SHA-2/3, X25519, ML-KEM
./gen-thumb2.sh  # Thumb2: AES, ChaCha, Poly1305, SHA-2/3, X25519, ML-KEM
./gen-x86.sh     # x86 32-bit: AES-GCM only
./gen-ppc32.sh   # PowerPC 32-bit
./gen-sp.sh      # SP math for all platforms (C32, C64, ARM32, ARM64, Thumb, Cortex-M, x86_64)
./gen-asm.sh     # Runs all of the above
```

Individual algorithms can be generated directly:
```
ruby ./aes/aes.rb x86_64 ../wolfssl/wolfcrypt/src/aes_
ruby ./sp/sp.rb 64 > ../wolfssl/wolfcrypt/src/sp_c64.c
ruby ./sp/sp.rb x86_64 ../wolfssl/wolfcrypt/src/sp_x86_64_asm > ../wolfssl/wolfcrypt/src/sp_x86_64.c
```

**Prerequisite**: Ruby must be installed. No gems or special dependencies required.

## Where Generated Code Lives in wolfSSL

Generated assembly files land in the wolfSSL source tree at:
- **`wolfcrypt/src/`** — x86_64 assembly (`.S`), SP math C files, inline assembly
- **`wolfcrypt/src/port/arm/`** — ARM64, ARM32, and Thumb2 assembly files

Key generated files include:
- `aes_gcm_asm.S`, `aes_xts_asm.S` — AES with AES-NI/AVX
- `chacha_asm.S`, `poly1305_asm.S` — ChaCha20-Poly1305 AEAD
- `sha256_asm.S`, `sha512_asm.S`, `sha3_asm.S` — Hash functions
- `sp_x86_64.c`, `sp_x86_64_asm.S` — SP math for x86_64
- `sp_arm64.c`, `sp_arm32.c`, `sp_cortexm.c` — SP math for ARM
- `wc_mlkem_asm.S`, `wc_mldsa_asm.S` — Post-quantum assembly

## Common Support Questions

**"Can I modify the assembly code directly?"**
Modifying the generated `.S` or `.c` files directly is possible but strongly discouraged. Changes will be overwritten the next time assembly is regenerated. The correct approach is to modify the Ruby generator script, then regenerate.

**"Do I need the scripts repo to build wolfSSL?"**
No. The generated assembly files are checked into the wolfSSL repository. The scripts repo is only needed if you are modifying or adding assembly optimizations.

**"Why Ruby and not Perl?"**
The generators were originally Perl but were rewritten in Ruby. Ruby's text generation capabilities and object-oriented features make it well-suited for the DSL pattern used by the generators.

**"How do I disable assembly and use C fallbacks?"**
Build without `--enable-intelasm`, `--enable-armasm`, or `--enable-sp-asm`. The C implementations are always available as fallbacks. For SP math, use `--enable-sp` without `--enable-sp-asm` to get optimized C.
