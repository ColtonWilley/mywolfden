# Side-Channel Patterns in wolfSSL

> One-line summary: constant-time primitives, dangerous code patterns, and wolfSSL-specific failure modes for side-channel triage.

**When to read**: Investigating a side-channel report, reviewing crypto code for timing safety, or triaging a CVE related to constant-time behavior.

---

## Constant-Time Primitives

wolfSSL provides these primitives — always use them instead of rolling your own:

| Primitive | Purpose | Location |
|-----------|---------|----------|
| `ConstantCompare` | Compare two buffers in constant time (replaces `memcmp`) | `wolfcrypt/src/misc.c` |
| `ForceZero` | Zeroize memory without compiler elision | `wolfcrypt/src/misc.c` |
| `ctMaskGT` / `ctMaskLT` / `ctMaskEq` | Constant-time comparison masks (all-ones or all-zeros) | `wolfcrypt/src/misc.c` |
| `ctMaskSel` / `ctMaskCopy` | Constant-time conditional select/copy | `wolfcrypt/src/misc.c` |
| `ct_IsNonZero` | Returns mask based on whether value is nonzero | `wolfcrypt/src/misc.c` |
| `mp_exptmod` (default) | Routes to Montgomery ladder (`_sp_exptmod_mont_ex`) when `WC_NO_HARDEN` is not defined | `wolfcrypt/src/sp_int.c` |

## Dangerous Patterns to Avoid

**Branching on secrets:**
```c
// WRONG — branch leaks secret_bit via timing
if (secret_bit) { result = a; } else { result = b; }

// RIGHT — use bitwise mask
mask = -(int)(secret_bit != 0);
result = (a & mask) | (b & ~mask);
```

**Early-exit comparison:**
```c
// WRONG — standard memcmp returns at first difference
if (memcmp(mac_computed, mac_received, 32) != 0) ...

// RIGHT — use ConstantCompare
if (ConstantCompare(mac_computed, mac_received, 32) != 0) ...
```

**Short-circuit logical operators on secret data:**
```c
// WRONG — && short-circuits
if (len > 0 && data[len-1] == expected) ...
// RIGHT — & evaluates both
if ((len > 0) & (data[len-1] == expected)) ...
```

**Hardware division on secret-dependent values** — `DIV`/`IDIV` on x86 are NOT constant-time. Use Barrett or Montgomery reduction instead.

**Table lookups indexed by secret** — cache line accessed reveals index bits. Use full-table scan with masking or bitsliced implementations.

## Architecture-Specific Gotchas

| Architecture | Gotcha |
|-------------|--------|
| ARM9 / some Cortex-M | Variable-time hardware multiplier (fewer cycles for smaller operands) |
| RISC-V without M extension | Software multiply (`__muldi3`) is variable-time; all SP math inner loops become timing-leaky |
| x86 | `DIV`/`IDIV` variable-time; `IMUL` constant-time on Haswell+; `CMOVcc` always constant-time |
| RISC-V with `Zkt` extension | Explicitly guarantees data-independent timing for defined instruction set |

## Compiler Can Destroy Constant-Time Code

Compilers can silently replace `cmov` with branches, eliminate `ForceZero` as dead stores, or add early-exit optimizations. Source-level analysis is necessary but not sufficient.

Key mitigations in wolfSSL:
- Critical ct operations in separate compilation units (prevents inlining/optimization)
- `ForceZero` uses volatile semantics to prevent dead store elimination
- SP math assembly (`--enable-sp-asm`) bypasses compiler entirely for critical paths

**Clangover precedent**: Clang 15-18 replaced ML-KEM constant-time conditional moves with secret-dependent branches under `-Os`/`-O1`, enabling full key recovery in ~10 minutes.

## Data Secrecy Classification (Triage Essential)

A variable-time operation on **public** data is not a vulnerability. Always trace data flow:

| Algorithm | Secret | Public |
|-----------|--------|--------|
| RSA | d, p, q, dP, dQ, qInv, blinding factors | n, e, ciphertext, signature |
| ECC/ECDSA | private scalar k, ECDSA nonce | public point Q, signature (r,s), curve params |
| ML-KEM | secret key (s,e), decapsulation key (dk) | public key (ek), ciphertext (u,v) |
| ML-DSA | signing key (s1,s2), nonce vector (y) | verification key, signature (z,c_tilde,h) |
| AES | key, round keys | plaintext, ciphertext, IV |

**Call-context principle**: The same function may need ct behavior at one call site but not another. ML-KEM `Compress(u)` during encapsulation operates on public ciphertext; during decapsulation the secret key flows through different operations. Trace the call site, not just the function.

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| ECDSA private key recovered from ~1200 signatures | Scalar multiplication leaks nonce bit-length (Minerva CVE-2019-15809) | `ecc.c` scalar multiply |
| ML-KEM key recovery in minutes | Compiler replaced ct code with branches (Clangover) or division timing (KyberSlash) | `mlkem.c` / compiler output |
| RSA padding oracle (Bleichenbacher/ROBOT/Marvin) | Different timing for valid vs invalid PKCS#1 v1.5 padding | `rsa.c` decryption path |
| DH shared secret leaks leading zeros | Unpadded secret fed to KDF; shorter hash input = faster (Raccoon) | DH key derivation |
| `sp_exptmod_nct` called for private key op | `WC_NO_HARDEN` defined, disabling Montgomery ladder | `sp_int.c` dispatch |

## What This File Does NOT Cover

- General side-channel education (attack taxonomy, academic references)
- CVSS scoring methodology for side-channel CVEs
- Power/EM analysis attack details (primarily relevant to hardware, not software review)
- Verification tooling (ctgrind, dudect) usage instructions
