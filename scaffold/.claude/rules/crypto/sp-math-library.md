---
paths:
  - "**/sp_*.c"
  - "**/sp.rb"
  - "**/sp_int.c"
---

# Single Precision (SP) Math Library

## What SP Math Is

The Single Precision (SP) math library provides fixed-size, key-size-specific implementations of public-key cryptographic operations (RSA, DH, ECC). Unlike generic multi-precision ("bignum") math that handles arbitrary sizes with loops and heap allocation, SP math generates dedicated code paths for each supported key size.

SP math has been the default in wolfSSL since version 5.0. It is dramatically faster than the legacy `integer.c` / `tfm.c` math libraries because:
- No dynamic memory allocation for math operations
- Loop counts are compile-time constants, enabling full unrolling
- Platform-specific assembly uses all available registers optimally for each key size
- Montgomery multiplication and modular exponentiation are specialized per key size

## SP Math Variants

The SP math system generates multiple output files for different platforms, all from `sp/sp.rb`:

**C implementations (portable):**
- `sp_c32.c` — C using 32-bit words (for 32-bit platforms or when 64-bit multiply is unavailable)
- `sp_c64.c` — C using 64-bit words (for 64-bit platforms with 128-bit multiply support)

**Assembly implementations (platform-specific):**
- `sp_x86_64.c` + `sp_x86_64_asm.S` — Intel/AMD x86_64 with inline and standalone assembly
- `sp_arm64.c` — ARMv8/AArch64 inline assembly
- `sp_arm32.c` — ARMv7 ARM32 inline assembly
- `sp_armthumb.c` — ARM Thumb inline assembly (ARMv7-M)
- `sp_cortexm.c` — ARM Cortex-M (Thumb2) inline assembly (optimized for M4/M7/M33)
- `sp_riscv32.c` — RISC-V 32-bit inline assembly (RV32IMC — ESP32-C3/C6, SiFive FE310, etc.)
- `sp_riscv64.c` — RISC-V 64-bit inline assembly (RV64GC — SiFive U74, StarFive JH7110, etc.)

**ISA-specific enable flags:** `WOLFSSL_SP_X86_64`, `WOLFSSL_SP_ARM64`, `WOLFSSL_SP_ARM32`, `WOLFSSL_SP_ARM_THUMB`, `WOLFSSL_SP_ARM_CORTEX_M_ASM`, `WOLFSSL_SP_RISCV32`, `WOLFSSL_SP_RISCV64`. Selecting the correct flag for the target ISA provides both performance optimization (2-5x) and constant-time side-channel resistance.

Generation command: `./gen-sp.sh [wolfssl_src_dir]`

## Supported Key Sizes

SP math generates dedicated code paths for specific key sizes. Operations with unsupported sizes either fall back to generic math or fail, depending on configuration.

**RSA / DH:**
- 2048-bit (most common, required for TLS)
- 3072-bit (128-bit security level)
- 4096-bit (high security)

**ECC (NIST curves):**
- P-256 (secp256r1) — most widely used
- P-384 (secp384r1) — required by some government standards
- P-521 (secp521r1) — highest security NIST curve

**Additional:**
- Ed25519 / X25519 (Curve25519-based)
- Ed448 / X448 (Curve448-based)
- SAKKE 1024-bit (enabled with `WOLFCRYPT_HAVE_SAKKE`)

## Configure Flags

**Enable/disable SP math:**
- `--enable-sp` — Enable SP math (default: on since wolfSSL 5.0)
- `--enable-sp-math` — Use SP math only (`WOLFSSL_SP_MATH`). Unsupported key sizes will fail.
- `--enable-sp-math-all` — Use SP math with generic fallback (`WOLFSSL_SP_MATH_ALL`). Unsupported sizes handled by `sp_int.c`.

**Enable assembly:**
- `--enable-sp-asm` — Use platform-specific SP assembly (`WOLFSSL_SP_ASM`)
- Platform-specific macros: `WOLFSSL_SP_X86_64_ASM`, `WOLFSSL_SP_ARM64_ASM`, `WOLFSSL_SP_ARM32_ASM`, `WOLFSSL_SP_ARM_THUMB_ASM`, `WOLFSSL_SP_ARM_CORTEX_M_ASM`

**Algorithm selection:**
- `WOLFSSL_HAVE_SP_RSA` — SP RSA operations (default with `--enable-sp`)
- `WOLFSSL_HAVE_SP_DH` — SP DH operations
- `WOLFSSL_HAVE_SP_ECC` — SP ECC operations

**Tuning:**
- `SP_WORD_SIZE` — Word size (32 or 64). Auto-detected but can be overridden.
- `WOLFSSL_SP_SMALL` — Use smaller code size at cost of speed (good for constrained embedded).
- `WOLFSSL_SP_NO_MALLOC` — Avoid all heap allocation in SP math (stack only).

## Common Issues

### "unsupported key size" or math operation fails
**Cause**: `WOLFSSL_SP_MATH` (strict mode) is enabled and the key size isn't one of the supported sizes (2048/3072/4096 for RSA, P-256/P-384/P-521 for ECC).
**Fix**: Switch to `WOLFSSL_SP_MATH_ALL` which falls back to generic `sp_int.c` math for unsupported sizes. Or ensure only supported key sizes are used.

### Wrong `SP_WORD_SIZE` for platform
**Cause**: Building on a 32-bit platform but `SP_WORD_SIZE` defaulted to 64, or vice versa.
**Symptoms**: Compilation errors in SP math files, incorrect results, or crashes.
**Fix**: Explicitly set `SP_WORD_SIZE=32` for 32-bit targets or `SP_WORD_SIZE=64` for 64-bit targets.

### SP assembly not compiling on unexpected toolchain
**Cause**: SP assembly files contain GCC/Clang inline assembly syntax that may not be compatible with all compilers.
**Fix**: Disable SP assembly (`--disable-sp-asm`) and use the C implementation instead. The C variants (`sp_c32.c` / `sp_c64.c`) work with any C compiler.

### `WOLFSSL_SP_MATH` vs `WOLFSSL_SP_MATH_ALL` confusion
- `WOLFSSL_SP_MATH` — **Strict mode**: Only SP-supported key sizes work. Smallest code size. Use when you control all key sizes.
- `WOLFSSL_SP_MATH_ALL` — **Fallback mode**: SP for supported sizes, generic `sp_int.c` for everything else. Larger code but handles any key size.
- For most users, `WOLFSSL_SP_MATH_ALL` (the default with `--enable-sp`) is the right choice.

### Toolchain Triplet vs ISA Feature Selection for SP Variant

A common investigation confusion: the `--host` triplet passed to `./configure` (e.g., `riscv64-unknown-elf`, `arm-none-eabi`) names the TOOLCHAIN, not the target ISA features. The triplet determines which platform-specific `#define`s configure.ac sets (e.g., `WOLFSSL_SP_RISCV64`), but the actual compiled SP variant depends on the compiler's target word size, which is controlled by `-march`/`-mabi` flags passed to the compiler.

**Investigation pattern — which SP C file actually compiled:**
1. Check the `--host` triplet → what platform defines does configure.ac set? (Grep for the triplet pattern in configure.ac)
2. Check the `-march`/`-mabi` flags → what is the compiler's actual target word size?
3. Check the binary symbols → do function names match `sp_c32.c` patterns (e.g., `sp_256_mul_9` — 9 limbs at 29 bits each) or `sp_c64.c` patterns (e.g., `sp_256_mul_5` — 5 limbs at 52 bits each)? The digit in the function name reflects how many words represent a field element at that word size.
4. `SP_WORD_SIZE` auto-detection (sp_int.h) uses compiler-defined macros (`__SIZEOF_LONG__`, `__SIZEOF_POINTER__`, etc.) to determine the word size. The `--host` triplet does NOT override this — the compiler's actual target does.

**Example:** `--host=riscv64-unknown-elf` with `-march=rv32imc -mabi=ilp32` will set `WOLFSSL_SP_RISCV64` in configure.ac (from the triplet), but the compiler targets a 32-bit ISA, so `SP_WORD_SIZE=32`, and `sp_c32.c` functions compile. The "64" in the triplet names the toolchain family, not the instruction set width. The binary's function names (`sp_256_mul_9` not `sp_256_mul_5`) confirm which variant was compiled.

**Why this matters for side-channel investigations:** The RISCV64 inline assembly macros in sp_int.c require `SP_WORD_SIZE == 64` and use instructions from the M extension (`mul`, `mulhu`). When the actual target is RV32I (no M extension), these macros are not active, and the code falls back to C-level 64-bit multiplication — which the compiler implements via software routines like `__muldi3`. Confirming which SP variant compiled (from binary symbols) resolves whether assembly or C fallback paths are in use.

### Function Naming Conventions — Security Properties

SP math function names encode security properties. These conventions are investigation evidence — when a security report targets a specific function, the name itself may reveal whether the function is designed to be constant-time.

**Key suffixes:**
- `_nct` = "Non-Constant Time" — intentionally non-constant-time for performance. Used for public exponent operations (where the exponent is not secret) and as the fast path when `WC_NO_HARDEN` is defined. The function docstring in sp_int.c explicitly states "Non-constant time implementation."
- `_mont_ex` = Montgomery exponentiation with constant-time hardening. Uses the Montgomery powering ladder (Joye/Yen 2002) which performs both square and multiply on every iteration regardless of the exponent bit value.
- `_ct` in function names = constant-time variant (e.g., `_sp_copy_2_ct` for constant-time conditional copy).
- `_small` suffix = size-optimized variant selected by `WOLFSSL_SP_SMALL`. Smaller code, slower execution. Not a security property, but affects which code path is compiled.

**Dispatch pattern for exponentiation:**
The public entry point `sp_exptmod` (aliased as `mp_exptmod`) dispatches based on `WC_NO_HARDEN`:
- `WC_NO_HARDEN` NOT defined (default, since `--enable-harden=yes`): routes to `_sp_exptmod_mont_ex` (constant-time)
- `WC_NO_HARDEN` defined: routes to `sp_exptmod_nct` (fast, non-constant-time)

The separate function `sp_exptmod_nct` (aliased as `mp_exptmod_nct`) is directly callable and always uses the non-constant-time implementation regardless of hardening settings. In the RSA code path, it is called only for public exponent operations (`rnd^e mod n` for blinding, public encrypt/decrypt) — never for private key exponentiation under default configuration.

**Investigation pattern:** When a security report targets a specific SP math function, check the function name for `_nct` — if present, the function is explicitly non-constant-time by design. Then trace whether the normal application API (`wc_Rsa*`, `wc_ecc_*`) actually calls that function for the secret-key operation, or whether it dispatches to the hardened variant.

## Performance

SP math provides dramatic performance improvements over legacy math:

**Relative performance (approximate, RSA-2048 sign):**
- SP x86_64 assembly: **fastest** (10-20x over legacy)
- SP ARM64 assembly: ~15x over legacy
- SP C 64-bit: ~5-8x over legacy
- SP C 32-bit: ~3-5x over legacy
- Legacy `tfm.c`: baseline
- Legacy `integer.c`: slowest

SP math matters most for RSA and DH operations where modular exponentiation dominates. For ECC, the improvement is significant but less dramatic (2-5x) because ECC operations are already faster. For symmetric crypto (AES, ChaCha), SP math is not involved — those have their own separate assembly optimizations.
