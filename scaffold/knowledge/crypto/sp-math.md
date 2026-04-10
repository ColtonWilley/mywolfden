# SP Math Library

> One-line summary: SP math variants, configure flags, naming conventions with security properties, and platform/toolchain gotchas.

**When to read**: Debugging SP math build failures, investigating which SP variant compiled for a target, or triaging a side-channel report targeting SP math functions.

---

## SP Math Variants

| Define | Configure Flag | Behavior | Use When |
|--------|---------------|----------|----------|
| `WOLFSSL_SP_MATH` | `--enable-sp-math` | **Strict**: only SP-supported key sizes work; unsupported sizes fail | You control all key sizes; smallest code |
| `WOLFSSL_SP_MATH_ALL` | `--enable-sp-math-all` | **Fallback**: SP for supported sizes, generic `sp_int.c` for everything else | Default; handles any key size |
| (legacy) | `--disable-sp` | Use legacy `tfm.c` / `integer.c` | Avoid unless required for compatibility |

**Default since wolfSSL 5.0**: `WOLFSSL_SP_MATH_ALL` via `--enable-sp`.

## Supported Key Sizes (Dedicated Code Paths)

| Family | Sizes |
|--------|-------|
| RSA / DH | 2048, 3072, 4096 bit |
| ECC (NIST) | P-256, P-384, P-521 |
| Curve25519/448 | Ed25519/X25519, Ed448/X448 |

Unsupported sizes with `WOLFSSL_SP_MATH` will fail. With `WOLFSSL_SP_MATH_ALL`, they fall back to generic `sp_int.c`.

## Platform-Specific Files

All generated from `sp/sp.rb` via `./gen-sp.sh`.

| File | Platform | ISA Flag |
|------|----------|----------|
| `sp_c32.c` | Portable C, 32-bit words | (auto) |
| `sp_c64.c` | Portable C, 64-bit words | (auto) |
| `sp_x86_64.c` + `sp_x86_64_asm.S` | Intel/AMD x86_64 | `WOLFSSL_SP_X86_64` |
| `sp_arm64.c` | ARMv8/AArch64 | `WOLFSSL_SP_ARM64` |
| `sp_arm32.c` | ARMv7 | `WOLFSSL_SP_ARM32` |
| `sp_armthumb.c` | ARM Thumb (ARMv7-M) | `WOLFSSL_SP_ARM_THUMB` |
| `sp_cortexm.c` | Cortex-M (Thumb2, M4/M7/M33) | `WOLFSSL_SP_ARM_CORTEX_M_ASM` |
| `sp_riscv32.c` | RISC-V 32-bit (RV32IMC) | `WOLFSSL_SP_RISCV32` |
| `sp_riscv64.c` | RISC-V 64-bit (RV64GC) | `WOLFSSL_SP_RISCV64` |

## Configure Flags

| Flag | Define | Purpose |
|------|--------|---------|
| `--enable-sp` | (default) | Enable SP math |
| `--enable-sp-asm` | `WOLFSSL_SP_ASM` | Use platform-specific assembly |
| `--enable-harden` | (default=yes) | Routes to constant-time exponentiation |
| — | `WOLFSSL_SP_SMALL` | Smaller code, slower (constrained embedded) |
| — | `WOLFSSL_SP_NO_MALLOC` | Stack-only, no heap allocation |
| — | `SP_WORD_SIZE=32/64` | Override word size auto-detection |
| — | `WOLFSSL_HAVE_SP_RSA` | SP RSA operations |
| — | `WOLFSSL_HAVE_SP_DH` | SP DH operations |
| — | `WOLFSSL_HAVE_SP_ECC` | SP ECC operations |

## Function Naming Conventions

Function names encode key properties:

| Pattern | Meaning |
|---------|---------|
| `sp_256_mul_9` | P-256 multiply, 9 limbs (32-bit words, 29-bit digits) |
| `sp_256_mul_5` | P-256 multiply, 5 limbs (64-bit words, 52-bit digits) |
| `_nct` suffix | **Non-Constant Time** — intentionally for public exponent ops or when `WC_NO_HARDEN` |
| `_mont_ex` suffix | Montgomery exponentiation with constant-time hardening (powering ladder) |
| `_ct` suffix | Constant-time variant (e.g., `_sp_copy_2_ct`) |
| `_small` suffix | Size-optimized (`WOLFSSL_SP_SMALL`), not a security property |

**Exponentiation dispatch** (`sp_exptmod` / `mp_exptmod`):
- `WC_NO_HARDEN` NOT defined (default): routes to `_sp_exptmod_mont_ex` (constant-time)
- `WC_NO_HARDEN` defined: routes to `sp_exptmod_nct` (fast, non-constant-time)

`sp_exptmod_nct` / `mp_exptmod_nct` is directly callable and always non-constant-time. In RSA, it is called only for **public** exponent operations (blinding, public encrypt/decrypt), never for private key exponentiation under default config.

## Toolchain Triplet vs ISA: Which Variant Actually Compiled?

The `--host` triplet names the **toolchain**, not the ISA features. The actual SP variant depends on `-march`/`-mabi` flags.

**Investigation pattern:**
1. Check `--host` triplet -> what platform defines does `configure.ac` set?
2. Check `-march`/`-mabi` -> what is the compiler's actual target word size?
3. Check binary symbols -> `sp_256_mul_9` = sp_c32.c (9 limbs), `sp_256_mul_5` = sp_c64.c (5 limbs)
4. `SP_WORD_SIZE` auto-detection (`sp_int.h`) uses `__SIZEOF_LONG__`, `__SIZEOF_POINTER__` — the `--host` triplet does NOT override this

**Example**: `--host=riscv64-unknown-elf` with `-march=rv32imc -mabi=ilp32` sets `WOLFSSL_SP_RISCV64` (from triplet) but compiles `sp_c32.c` functions (from actual 32-bit target). The "64" in the triplet names the toolchain family, not the instruction set width.

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| "unsupported key size" at runtime | `WOLFSSL_SP_MATH` (strict) and key size not 2048/3072/4096 or P-256/P-384/P-521 | Switch to `WOLFSSL_SP_MATH_ALL` |
| Compilation errors in SP files | Wrong `SP_WORD_SIZE` for platform (e.g., 64-bit default on 32-bit target) | Set `SP_WORD_SIZE=32` explicitly |
| SP asm fails with non-GCC toolchain | SP asm uses GCC/Clang inline syntax | `--disable-sp-asm`, use C variant |
| RISC-V SP inner loops use `__muldi3` | RV32I target without M extension; software multiply is variable-time | Confirm via binary symbols; use `-march=rv32imc` for hardware multiply |
| Side-channel report targets `_nct` function | Function is explicitly non-constant-time by design | Trace whether the secret-key operation actually calls `_nct` or the hardened variant |

## What This File Does NOT Cover

- Performance benchmarks or comparisons between SP and legacy math
- Internal details of Montgomery multiplication algorithm
- How to modify `sp.rb` or regenerate SP files
- Legacy `tfm.c` / `integer.c` math libraries
