---
paths:
  - "**/sp_*.c"
  - "**/ecc.c"
  - "**/rsa.c"
---

# Side-Channel Attacks and Constant-Time Programming

## What Side-Channel Attacks Are

A side-channel attack extracts secret information not by breaking the mathematics of a cryptographic algorithm, but by observing physical effects of its execution — time, power consumption, electromagnetic radiation, cache behavior, or even sound. The algorithm itself may be mathematically perfect, but its implementation on real hardware leaks information through these physical channels.

This is critically important for a C crypto library: the C code you write determines how the CPU executes instructions, which in turn determines what physical signals are emitted. A single `if` statement branching on a secret bit can leak that bit through timing differences measurable across a network.

## Taxonomy of Side-Channel Attacks

### Timing Attacks

Timing attacks measure how long a cryptographic operation takes and correlate variations with secret values. They are the most relevant class for software crypto libraries because they can often be exploited remotely — an attacker on the network can measure response times with sufficient precision to extract keys.

The fundamental insight is that many operations take different amounts of time depending on their inputs. If those inputs are secret (like a private key), the timing reveals the secret. For example, RSA implementations that use simple modular exponentiation will multiply and square for a `1` bit but only square for a `0` bit — making each bit of the private key distinguishable by timing.

Timing attacks can work at nanosecond precision over local networks, and even across the internet with sufficient statistical sampling. The Lucky Thirteen attack against CBC-mode TLS recovered plaintext by measuring timing differences as small as tens of microseconds in MAC computation.

### Cache-Based Attacks

Modern CPUs use caches to speed up memory access. When a cryptographic operation accesses memory at addresses that depend on secret data (like S-box lookups indexed by key bits), the cache access pattern reveals those secrets.

**Prime+Probe**: The attacker fills cache sets with their own data, lets the victim execute, then measures which of their cache lines were evicted. Evicted lines indicate the victim accessed those cache sets — revealing which memory addresses (and thus which secret-dependent indices) were used.

**Flush+Reload**: When attacker and victim share memory (e.g., shared libraries), the attacker flushes specific cache lines, lets the victim execute, then reloads those lines. Fast reload means the victim accessed that address; slow reload means they didn't. This gives cache-line granularity (typically 64 bytes) on which code paths and data the victim accessed.

**Evict+Time**: The attacker evicts cache lines, then times the victim's entire operation. If it's slower, the evicted data was needed — revealing access patterns.

These attacks are particularly devastating for AES table-based implementations, where each round performs S-box lookups indexed by (state XOR key) bytes. The cache line accessed reveals 4 bits of the key byte per lookup.

### Power Analysis

**Simple Power Analysis (SPA)** directly observes the power trace of a device during a cryptographic operation. Different instructions consume different amounts of power, so you can literally see which instructions are executing. In RSA, a square-and-multiply implementation shows visually distinct power patterns for multiply (1-bit) vs. square-only (0-bit) operations.

**Differential Power Analysis (DPA)** is a statistical technique that correlates many power traces with hypothesized key values. Even when individual traces are noisy, averaging over thousands of traces can extract key bits. DPA is extremely powerful against hardware implementations and is the primary threat model for smartcards, HSMs, and embedded crypto on bare-metal targets.

Power analysis primarily threatens embedded/IoT deployments where an attacker has physical access to the device. It is less relevant for server-side crypto but critical for wolfSSL's embedded use cases.

### Electromagnetic (EM) Attacks

Similar to power analysis, but measures electromagnetic radiation emitted by the device. EM attacks can be more targeted — a focused EM probe can measure emanations from specific areas of a chip, potentially isolating individual functional units. This can give higher signal-to-noise than power analysis.

EM attacks can also work at a distance in some configurations, making them relevant even when the attacker doesn't have direct electrical contact with the device.

### Acoustic Attacks

Certain cryptographic operations produce audible or ultrasonic sound from electronic components (capacitors, inductors). RSA key extraction from laptop CPUs via acoustic emanations has been demonstrated. While exotic, this illustrates that any physical effect correlated with secret data is potentially exploitable.

## Constant-Time Programming: The Three Principles

Writing code that resists timing side channels requires ensuring that no observable behavior (timing, memory access pattern, code path) depends on secret values. Intel's guidance formalizes this into three principles:

### Principle 1: Secret-Independent Runtime (SIR)

Every instruction that operates on secret data must have execution time independent of that data's value. This seems straightforward but is surprisingly hard to achieve.

**Unsafe**: Hardware integer division (`DIV`, `IDIV` on x86) takes variable time depending on operand magnitude. The KyberSlash attack exploited this: ML-KEM's modular reduction used division, and the time variation leaked enough information to recover the secret key in ~10 minutes.

**Unsafe**: Floating-point operations (`FDIV`, `FSQRT`) have variable latency based on operand values (denormals, special values take different paths).

**Unsafe**: Variable-length multiplication on some architectures. While most modern x86 CPUs have constant-time multiplication, ARM9 and some other embedded cores have multipliers that take fewer cycles for smaller operands. The same C code `a * b` may be constant-time on x86 but leak on ARM.

**Safe**: Addition, subtraction, XOR, AND, OR, NOT, shift/rotate by constant, and (on most modern CPUs) fixed-width multiplication are constant-time.

### Principle 2: Secret-Independent Code Access (SIC)

The value of a secret must never determine which branch of code executes. Branch prediction state changes are measurable, and speculative execution (Spectre-class) can amplify the signal.

**Unsafe — branching on secret data:**
```c
// NEVER DO THIS — the branch leaks whether `secret_bit` is 0 or 1
if (secret_bit) {
    result = value_a;
} else {
    result = value_b;
}
```

**Safe — conditional move:**
```c
// Both paths execute; cmov selects the result without branching
result = value_b;
asm volatile("test %1, %1; cmovnz %2, %0"
             : "+r"(result) : "r"(secret_bit), "r"(value_a));
```

Or in portable C, using bitwise masking:
```c
mask = -(int)(secret_bit != 0);  // all-ones if true, all-zeros if false
result = (value_a & mask) | (value_b & ~mask);
```

**Unsafe — early-exit comparison:**
```c
// Standard memcmp returns at the first difference — leaks position of mismatch
int equals(const uint8_t *a, const uint8_t *b, size_t len) {
    for (size_t i = 0; i < len; i++) {
        if (a[i] != b[i]) return 0;  // TIMING LEAK
    }
    return 1;
}
```

**Safe — constant-time comparison:**
```c
int ct_equals(const uint8_t *a, const uint8_t *b, size_t len) {
    volatile uint8_t diff = 0;
    for (size_t i = 0; i < len; i++) {
        diff |= a[i] ^ b[i];  // accumulate ALL differences
    }
    return diff == 0;  // only check at the end
}
```

**Unsafe — short-circuit logical operators:**
```c
// && short-circuits: if first condition is false, second never evaluates
if (len > 0 && data[len-1] == expected) { ... }
```

**Safe — bitwise operators:**
```c
// & always evaluates both sides
if ((len > 0) & (data[len-1] == expected)) { ... }
```

### Principle 3: Secret-Independent Data Access (SID)

Memory access addresses must not depend on secret values. Cache-based attacks can observe which cache lines are accessed, revealing the secret-dependent index.

**Unsafe — table lookup with secret index:**
```c
// S-box lookup: cache line accessed reveals bits of `secret_index`
output = sbox[secret_index];
```

**Safe — scan entire table with masking:**
```c
// Access ALL table entries; use masking to select the right one
uint8_t result = 0;
for (int i = 0; i < 256; i++) {
    uint8_t mask = ct_eq(i, secret_index);  // 0xFF if match, 0x00 otherwise
    result |= sbox[i] & mask;
}
```

This is slower but accesses every cache line regardless of the secret index, preventing cache-based leakage.

**Alternative — bitsliced implementation:** Compute the S-box function using bitwise operations on registers instead of table lookups. This avoids memory access patterns entirely and is the preferred approach for high-performance constant-time AES.

## Prerequisite: Identifying What Data Is Secret

The three principles above define WHAT must be constant-time: operations on secret data. But applying them to a real vulnerability report requires answering the prior question: **is the data flowing through the allegedly vulnerable operation actually secret?** This is the most critical analytical step in side-channel triage. A variable-time operation on public data is not a side-channel vulnerability, regardless of how non-constant-time it is.

### Data Secrecy Classification by Algorithm Family

Each cryptographic algorithm defines which values are secret and which are public. This is determined by the algorithm specification — it is a technical fact derived from the algorithm's design, not a security judgment.

**Asymmetric Key Operations (RSA, ECC, DH/ECDHE)**:
- **Secret**: Private key (RSA: d, p, q, dP, dQ, qInv; ECC: scalar k), ECDSA nonce k, DH private exponent, blinding factors
- **Public**: Public key (RSA: n, e; ECC: public point Q), ciphertext, signature (r, s), curve parameters, DH group parameters
- **Derived-secret**: Shared secret (DH/ECDHE result), premaster secret — these are derived from secret material and must be treated as secret until consumed by a KDF

**ML-KEM / Kyber (Lattice-based KEM)**:
- **Secret**: Secret key polynomials (s, e), decapsulation key (dk), implicit rejection secret (z)
- **Public**: Public key (encryption key ek, containing the t vector and seed), ciphertext components (u vector, v scalar), encapsulated shared secret output (K)
- **Critical distinction — encapsulation vs decapsulation**:
  - During **encapsulation** (FIPS 203 Algorithm 20/K-PKE.Encrypt): The `u` vector is computed as `u = A^T * r + e1` where `r` and `e1` are ephemeral randomness, then `u` is **compressed** for inclusion in the ciphertext. The compression operation (`Compress_d_u(u)`) operates on data that is about to be transmitted as public ciphertext. Operations on `u` during compression are operations on **public data**.
  - During **decapsulation** (FIPS 203 Algorithm 21/K-PKE.Decrypt): The received ciphertext `u` is decompressed, then multiplied by the **secret key** `s` to recover the shared secret. Operations on `s` during this multiply are operations on **secret data**.
  - During the **Fujisaki-Okamoto re-encryption check** (FIPS 203 Algorithm 18): Decapsulation re-encrypts using the derived shared secret `K'` to produce a re-derived ciphertext, then compares it against the received ciphertext. The re-derived `u'` being compressed is a re-derivation of what the original encapsulator would have produced — it is compared against (and should be equal to) the received **public** ciphertext.
  - **The same compression function** called during encapsulation (public `u`) and during the FO re-encryption (re-derived `u'` for comparison against public ciphertext) processes public-equivalent data in both cases. The function itself does not determine data secrecy — the **call site** and **what data flows in** determine it.

**ML-DSA / Dilithium (Lattice-based Signatures)**:
- **Secret**: Signing key polynomials (s1, s2), nonce/mask vector (y), intermediate values during rejection sampling
- **Public**: Verification key (t1, seed), signature (z, c_tilde, h), challenge polynomial (c)
- **Note**: Rejection sampling retry count is secret-dependent — the number of iterations leaks information about the signing key

**Symmetric Operations (AES, ChaCha20, etc.)**:
- **Secret**: Key material, derived round keys
- **Public**: Plaintext (in standard encryption contexts), ciphertext, nonce/IV, associated data
- **Note**: For AES, the S-box lookup index is `state XOR key` — even though the state (plaintext) is public, the XOR with the secret key makes the index secret-dependent

**Hash / MAC / KDF Operations**:
- **Secret**: HMAC key, PRF secret, KDF input key material
- **Public**: Message being hashed (in non-keyed contexts), output digest, salt

### The Call-Context Principle

A function's constant-time requirement is NOT an intrinsic property of the function — it depends on what data flows through it at each call site. The same function may require constant-time behavior at one call site and not at another.

**Example**: A polynomial compression function like `mlkem_vec_compress_10(byte* r, sword16* v, unsigned int k)` takes a polynomial vector and compresses it. When called:
- From `mlkemkey_encapsulate()` to compress the `u` ciphertext vector → `v` contains **public** ciphertext data → no constant-time requirement for the compression arithmetic
- Hypothetically from a path processing secret key coefficients → `v` would contain **secret** data → constant-time requirement applies

When investigating a side-channel report, always trace the specific call site — do not assume a function must be constant-time just because it operates on "polynomial coefficients." The question is: are those coefficients secret key material, or are they public ciphertext components?

### Data Flow Tracing Methodology

When investigating a report claiming variable-time operations leak secret data, apply this procedure to determine data secrecy as a factual finding:

1. **Identify the operation**: What is the alleged variable-time operation? (hardware division, data-dependent branch, table lookup with secret index)

2. **Identify the operands**: What variable(s) flow into the operation as inputs? (e.g., "the dividend in `value / MLKEM_Q` is `v[i]`")

3. **Trace each operand to its origin**: Follow the variable backwards through assignments, function parameters, and callers. The origin is one of:
   - **Secret key material** (loaded from the key structure, derived from private key) → SECRET
   - **Public key / ciphertext / protocol message** (received from the network, loaded from public key structure) → PUBLIC
   - **Algorithmic constant** (MLKEM_Q = 3329, curve order, group generator) → PUBLIC
   - **Ephemeral randomness** (nonce, blinding factor — secret during use, but the values derived from it may become public when transmitted as ciphertext)
   - **Combination** — see derived-value rules below

4. **Identify the call context**: Trace the caller chain to determine which algorithm phase (encapsulation vs decapsulation, signing vs verification, encryption vs decryption) invokes this code path. The same function may process different data depending on the caller.

5. **State the origin chain as a factual finding**: "The operand `v` at [file:line] is received as parameter from [caller] at [file:line]. [Caller] computes `v` as [expression] where [component] is the [public ciphertext / secret key / ...] [file:line]."

6. **Trace the output forward**: After determining where the data COMES FROM (steps 1-5), determine where the result GOES. This completes the data flow picture:
   - Is the result **transmitted as protocol output** (written to a ciphertext buffer, included in a signature, sent in a protocol message)? Once transmitted, the value becomes public data regardless of its derivation history.
   - Is the result **compared against known or public data** (verification check, re-encryption comparison, MAC verification)? The comparison target and the outcome handling (accept/reject/implicit-reject with indistinguishable output) are relevant protocol context to surface.
   - Is the result **used in further secret-dependent computation** (fed into the next round, used as a key for a subsequent operation)? The result remains secret-carrying and timing on it is meaningful.
   - Is the result **discarded on certain code paths** (error handling, rejection, fallback to random value)? Whether the attacker can distinguish which code path was taken determines whether the timing variation is observable.

   State the forward path as a factual finding alongside the backward origin trace: "The output of [operation] at [file:line] is [written to ciphertext buffer at file:line / compared against received ciphertext at file:line / used as input to next round at file:line / ...]."

   The backward trace (steps 1-5) determines what data flows IN. The forward trace (step 6) determines what happens to the result. Both are needed for a complete data flow picture.

### Derived-Value Classification Rules

When a value is computed from multiple inputs, its secrecy classification follows these rules:

- **Secret + Public → Secret**: Any value that incorporates secret key material inherits secrecy. Example: `state XOR round_key` in AES — the state alone is public, but XOR with the secret round key makes the result secret.
- **Secret → Public (via one-way function)**: A value published as output (ciphertext, signature, public key) is public by definition, even though it was derived from secret inputs. The algorithm's security relies on the one-way property preventing recovery of the secret from the public output.
- **Public + Public → Public**: Operations on purely public data produce public results. Example: compressing public ciphertext vector `u` for transmission — both input and output are public.
- **Ephemeral secret → Public (when transmitted)**: An ephemeral random value (like ML-KEM's `r` vector) is secret during computation but the ciphertext derived from it is public once transmitted. The compression of that ciphertext operates on public data.

### Why This Matters for Triage

A report that says "function X uses variable-time division" is incomplete without answering "on what data?" Two scenarios with identical code but different data flow:

- **Scenario A**: Variable-time division on secret key coefficients during decapsulation → timing leak of secret key → genuine side-channel vulnerability
- **Scenario B**: Variable-time division on public ciphertext coefficients during encapsulation → timing reveals information about public data that is already being transmitted in plaintext → not a side-channel vulnerability

The code-level observation (variable-time division exists) is identical in both scenarios. The data flow analysis (what data flows through the division) is what distinguishes them. This is a technical fact chain, not a security assessment — each step (function call site, parameter origin, data classification per algorithm spec) is independently verifiable from source code and algorithm specification.

Beyond data secrecy, a second analytical dimension is **oracle availability** — derived from Principle 1 (The Oracle Principle) in the attack fundamentals. A timing variation on secret-derived data is exploitable only if the attacker has a feedback mechanism: the ability to submit inputs, observe correlated timing, and repeat across multiple operations with the same key. Protocol properties that affect this are factual data points to surface alongside the data flow analysis:

- **Feedback**: Does the attacker learn anything from the protocol's response that correlates with the internal computation timing? Or does the protocol return an indistinguishable result regardless of the internal path taken (implicit rejection returning a pseudorandom value, constant-time error handling returning the same alert)?
- **Repeatability**: Can the attacker trigger the vulnerable operation many times against the same secret key? (A TLS server processes many handshakes with the same certificate key → high repeatability. A one-time key agreement → minimal repeatability.)
- **Input control**: Can the attacker choose the input to the timed operation? (Chosen ciphertext for decapsulation → high control. Randomly generated challenge → low control.)

These are factual properties of the protocol design, determinable from the algorithm specification and the application's usage pattern. Surface them in Code Context alongside the data flow analysis — the engineer uses both dimensions (data secrecy AND oracle availability) to evaluate the side-channel claim.

## Architecture-Specific Gotchas

### x86
- `CMOVcc` is constant-time on all current x86 processors. However, when the source operand is a memory location, the load always executes regardless of the condition — this is safe for timing but may trigger page faults or segfaults if the address is invalid.
- `DIV`/`IDIV` are NOT constant-time. Avoid for secret-dependent values.
- Multiplication (`IMUL`) is constant-time on modern x86 (since ~Haswell), but not guaranteed on all implementations.
- `PCLMULQDQ` (carry-less multiply, used in GCM) is constant-time on current implementations.

### ARM
- `CSEL` (conditional select, ARM's equivalent of `cmov`) behavior varies. On Cortex-A53 it is constant-time, but on some older cores this should be verified.
- ARM9 and some Cortex-M cores have variable-time multiplication — the multiplier takes fewer cycles when operands have leading zeros. This means the same C code that's constant-time on x86 may leak on ARM.
- The `BFI`/`UBFX` bit-field instructions can be useful for constant-time bit manipulation.
- Thumb mode vs. ARM mode can affect timing characteristics — instruction encoding differences change pipeline behavior.
- NEON SIMD operations are generally constant-time but verify for your specific core.

### RISC-V
- The M extension (`rv32im`, `rv64im`) provides hardware MUL/MULH/DIV instructions. Without M extension (`rv32i` base), the compiler emits software multiply/divide routines (typically `__muldi3`, `__divdi3` from libgcc or compiler builtins). These software routines are almost never constant-time — their execution time varies with operand values.
- **RV32I without M extension is particularly problematic for constant-time crypto code:** any SP math function compiled for RV32I will use variable-time software multiply for the inner loops of field element operations (e.g., `sp_256_mul_9`, `sp_256_sqr_9` in sp_c32.c perform `(sp_int64)a[i] * b[j]` which becomes a `__muldi3` call). The `-march` flag (not the `--host` triplet) determines whether M extension instructions are available — a toolchain named `riscv64-unknown-elf-gcc` can target `rv32i` via `-march=rv32i`.
- Even with M extension, MUL timing varies by RISC-V implementation. Some cores implement constant-time multiplication, others use early-termination multipliers that take fewer cycles for smaller operands.
- Branch prediction behavior varies widely across RISC-V implementations since the ISA doesn't mandate a specific microarchitecture.
- The crypto extensions (`Zkn`, `Zks`) are designed for constant-time operation but verify on your specific implementation. The `Zkt` extension explicitly guarantees data-independent timing for a defined set of instructions — its presence is a strong positive signal for constant-time safety.
- **Investigation pattern for RISC-V timing reports:** Check (a) the `-march` flag to determine which extensions are available (look for `m` in the march string), (b) whether the binary uses hardware MUL or software multiply routines (presence of `__muldi3` calls in hot paths), (c) whether the wolfSSL RISCV32/RISCV64 assembly macros in sp_int.c are active (they require M extension instructions like `mul`/`mulhu`). The presence of software multiply/divide in SP math inner loops on a core without M extension is a code-level fact, not a security assessment.

### Cross-Architecture Lesson
The same C source code can be constant-time on one architecture and leaking on another. You cannot verify constant-time properties at the source level — you must verify at the assembly/binary level for each target platform.

## Compiler Betrayal

One of the most insidious problems in constant-time programming is that compilers can silently destroy your constant-time guarantees. The compiler's optimizer sees your carefully written branchless code and "improves" it — sometimes reintroducing branches, sometimes using variable-time instructions, sometimes reordering operations in ways that create timing dependencies.

### The Clangover Attack
A landmark demonstration of this problem: researchers showed that Clang, under certain optimization levels, would compile ML-KEM's constant-time code into secret-dependent branches. The resulting binary leaked enough timing information to recover complete ML-KEM 512 secret keys in ~10 minutes on Intel processors.

The code was correct at the C level — every analysis of the source code would say "constant-time." But the compiler generated assembly that was not.

### Specific Compiler Pitfalls

**Dead store elimination**: You zero out a key buffer with `memset(key, 0, sizeof(key))`. The compiler sees that `key` is never read again and removes the memset entirely. The key stays in memory. Use `memset_s()` or `explicit_bzero()` or a volatile function pointer.

**Conditional move to branch conversion**: You write `result = condition ? a : b` expecting a `cmov`. The compiler decides a branch is faster (e.g., when one path is much more common) and generates `jnz`/`jz` instead.

**Loop optimization**: You write a fixed-iteration loop to scan a table. The compiler unrolls it and adds an early-exit condition because it determined the result can't change after a certain point.

**Strength reduction**: The compiler replaces multiplication by a constant with shifts and adds, which may have different timing characteristics than the original multiplication.

### Mitigations

**Volatile barrier**: Using `volatile` can prevent some optimizations, but it's only a hint — not a guarantee. Different compilers interpret `volatile` differently.

**Compiler-specific attributes**: GCC's `__attribute__((optimize("O0")))` can disable optimization for specific functions, but this is a blunt instrument.

**Assembly**: Writing critical operations in assembly is the only truly reliable approach. When you write assembly, you know exactly what instructions the CPU will execute. This is why many crypto libraries (including wolfSSL) use hand-written assembly for performance-critical and security-critical paths.

**Verification**: Regardless of approach, you must verify constant-time behavior by examining the actual compiled binary. Tools like `ctgrind` (a Valgrind-based tool that flags branches or memory accesses dependent on "secret" memory), `dudect` (statistical timing analysis), and `CT-Verif` (formal verification) can help, but each has limitations.

## Historical Side-Channel CVEs in Crypto Libraries

These are not wolfSSL-specific — they are patterns that have appeared across crypto libraries and represent the types of issues that vulnerability reporters commonly look for.

### Lucky Thirteen (CVE-2013-0169)
**What**: Timing attack on CBC-mode TLS MAC-then-encrypt.
**Root Cause**: When a TLS record has invalid padding, the MAC computation covers a different amount of data than when padding is valid. The time difference (about 2-3 hash compression function calls) is measurable.
**Code Pattern**: `if (padding_valid) { mac_data_len = record_len - padding_len; } else { mac_data_len = record_len; }` — the MAC computation then takes different time based on `mac_data_len`.
**Fix Pattern**: Always compute the MAC over the same amount of data, regardless of padding validity. Add dummy compression function calls to equalize timing.

### ROBOT / Bleichenbacher (CVE-2017-13099 and many others)
**What**: Padding oracle attack on RSA PKCS#1 v1.5 encryption.
**Root Cause**: The server's error handling differs (in timing, error message, or alert type) between valid and invalid PKCS#1 v1.5 padding after RSA decryption. This difference lets the attacker iteratively decrypt ciphertexts.
**Code Pattern**: `if (decrypted[0] != 0x00 || decrypted[1] != 0x02) { return PADDING_ERROR; }` followed by different processing paths for valid vs. invalid padding. Even if you return the same error code, differences in which code path executes (and thus timing) can leak the padding validity.
**Fix Pattern**: Continue processing as if padding were valid regardless of actual validity, only checking at the very end. Generate a random premaster secret and use it if padding was invalid, taking the same time as using the real one.
**Why It Keeps Coming Back**: The fix is counterintuitive — you must process garbage data as if it were valid, doing the same work either way. Any implementation that adds an early-exit on invalid padding reintroduces the vulnerability.

### Raccoon (CVE-2020-1968)
**What**: Timing attack on DH key exchange premaster secret.
**Root Cause**: The DH shared secret can have leading zero bytes. When these are stripped before being fed to the key derivation function, the resulting hash input is shorter, and the hash computation is faster. The timing difference leaks information about the shared secret's leading bytes.
**Code Pattern**: Computing the DH shared secret, then passing it to the KDF without constant-length padding. The hash function processes fewer blocks for shorter secrets.
**Fix Pattern**: Pad the DH shared secret to the full length of the DH prime before hashing, so the KDF always processes the same amount of data.

### KyberSlash (CVE-2023-XXXX)
**What**: Timing attack on ML-KEM (Kyber) lattice-based post-quantum KEM.
**Root Cause**: The modular reduction step used integer division, which takes variable time on most CPUs. The time variation is correlated with the secret key coefficients.
**Code Pattern**: `result = (value * constant) / KYBER_Q;` — the division instruction's execution time depends on the magnitude of `value`, which is derived from the secret key.
**Fix Pattern**: Replace division with constant-time Barrett or Montgomery reduction using only multiplication and shift operations.

### Minerva (CVE-2019-15809)
**What**: Timing attack on ECDSA nonce generation.
**Root Cause**: The scalar multiplication used in ECDSA signing had timing dependent on the bit-length of the nonce `k`. Shorter nonces (with leading zero bits) caused faster multiplication, leaking partial nonce information. With enough signatures, the full private key could be recovered via lattice techniques.
**Code Pattern**: Scalar multiplication that skips leading zero bits of the scalar. Any `while (top_bit == 0) { shift; skip; }` pattern on the nonce.
**Fix Pattern**: Always process all bits of the scalar, even leading zeros. Use fixed-window or Montgomery ladder scalar multiplication that processes a constant number of bits.

## Verification Tools and Their Limitations

### ctgrind / MemSan-based
Uses Valgrind's memory checking infrastructure, treating "secret" memory as "uninitialized." Any branch or memory access dependent on uninitialized (= secret) data is flagged. Effective for detecting branches and data-dependent memory accesses in C code, but only tests the specific binary that was compiled — a different optimization level or compiler version might produce different results.

### dudect
Statistical timing analysis tool. Runs the function many times with different inputs and uses statistical tests (Welch's t-test) to detect timing variations. Works on the actual binary as-executed, which catches compiler-introduced leaks. However, it's probabilistic — it may miss subtle leaks that require more samples, and it can produce false negatives for leaks that only manifest under specific input distributions.

### CT-Verif / Jasmin / Vale
Formal verification approaches that prove constant-time properties at the assembly level. The strongest guarantee, but requires significant effort to annotate and verify code. Jasmin and Vale are domain-specific languages that compile to verified assembly.

### Practical Reality
Only about 4 out of 15 major crypto libraries include constant-time verification in their CI pipeline. This means most libraries rely on manual review and ad-hoc testing — which is why timing vulnerabilities keep being discovered. Any report claiming a timing vulnerability should be taken seriously because systematic verification is rare.

## Deep Dive: AES T-Table Cache Attacks (Bernstein 2005)

AES implementations optimized for speed combine the SubBytes, ShiftRows, and MixColumns operations into four precomputed lookup tables (T0, T1, T2, T3), each mapping one byte of input to four bytes of output. In each AES round, the implementation performs lookups like `T0[state[0] ^ key[0]]`, where the index depends on the state XOR'd with the key.

This is where the attack works: cache lines are typically 64 bytes, and each T-table has 256 entries of 4 bytes (1024 bytes = 16 cache lines). When the implementation accesses `T0[state[0] ^ key[0]]`, the cache line accessed reveals 4 bits of `state[0] ^ key[0]` (since each cache line covers 16 entries). Since the attacker knows `state[0]` (it's the plaintext, which the attacker chose), learning which cache line was accessed reveals 4 bits of `key[0]`.

Bernstein demonstrated complete AES-128 key recovery from OpenSSL on a Pentium III using only timing measurements — crucially, timing of a *separate process sharing the cache*, not timing of the AES operation itself. Full key recovery required only 2^13 timing samples in later refined attacks.

This is why constant-time AES implementations use bitslicing (computing the AES S-box using bitwise operations on registers instead of table lookups) or hardware AES-NI instructions. Any software AES implementation using T-tables is vulnerable to cache-based attacks in shared-memory environments.

## Deep Dive: The Marvin Attack (2023) — Bleichenbacher's Return After 25 Years

The Marvin Attack (published by Red Hat's Hubert Kario) demonstrated that RSA PKCS#1 v1.5 timing oracles persist across major implementations even after 25 years of attempted fixes. Affected libraries included OpenSSL, GnuTLS, Mozilla NSS, pyca/cryptography, M2Crypto, and OpenSSL-ibmca.

The key insight is that implementations keep reintroducing the oracle through subtle mechanisms: different code paths for valid vs invalid padding (even if they "do the same thing," the CPU executes different instructions), differences in memory allocation patterns, or even differences in how error codes are generated. Even libraries that had been "fixed" against ROBOT in 2017 were found to still leak through previously unconsidered channels.

The general recommendation from the Marvin Attack research is to stop using RSAES-PKCS1-v1_5 entirely — the protocol construction is inherently difficult to implement without creating a timing oracle. TLS 1.3 took this advice and removed RSA key exchange completely.

For investigation context: any report about timing differences in RSA PKCS#1 v1.5 decryption should be taken seriously. History shows that every attempted fix for this vulnerability class has eventually been found insufficient. The only reliable defense is to not use PKCS#1 v1.5 for encryption.

## Deep Dive: ECDSA Nonce Leakage (Minerva and LadderLeak)

ECDSA signing requires a random nonce `k` for each signature. The mathematical structure of ECDSA means that if an attacker learns even partial information about `k` from multiple signatures, they can recover the private key using lattice reduction techniques (specifically, the Hidden Number Problem solved via CVP/BKZ).

**Minerva** demonstrated this against wolfSSL directly (CVE-2019-15809): the scalar multiplication implementation leaked the bit-length of the nonce through timing. Nonces with leading zero bits caused faster multiplication (fewer iterations in the main loop). With ~1200 signatures from real library data, the full private key was recoverable.

**LadderLeak** showed the attack works even against Montgomery ladder implementations (considered "naturally regular" and constant-time). The leak was in auxiliary operations — specifically, the conversion from projective coordinates back to affine coordinates, which had data-dependent timing. Even leaking just 1 bit per signature was sufficient for key recovery given several thousand signatures.

The lattice technique works as follows: each signature produces a nonce `k_i` and reveals `r_i = (k_i * G).x` and `s_i = k_i^(-1) * (hash + r_i * privkey)`. Partial knowledge of `k_i` (even just its bit-length) provides a linear approximation that constrains `privkey`. With enough such constraints (from enough signatures), lattice reduction finds the unique solution.

**Triage implications**: Reports about ECDSA timing don't need the attacker to observe individual nonce bits. Any consistent statistical bias in nonce bit-lengths across many signatures is sufficient. The attacker needs: (a) many signatures from the same key, (b) knowledge of the signed messages, and (c) a timing measurement per signature. For TLS, conditions (a) and (b) are naturally satisfied.

## CVSS Scoring Patterns for Side-Channel Attack Classes

Side-channel attacks have distinctive CVSS scoring patterns that differ from memory corruption or protocol vulnerabilities. Understanding these patterns helps calibrate Attack Surface data points against historical precedent.

**Attack Vector (AV) — the critical distinction:**
- **AV:Network** — The attacker measures timing remotely over the network. Historically applied to: Lucky Thirteen (CVE-2013-0169), ROBOT/Bleichenbacher (CVE-2017-13099), Raccoon (CVE-2020-1968). These attacks measure TLS handshake or record processing timing from a network position, where the timing differences are large enough (milliseconds to tens of microseconds) to survive network jitter.
- **AV:Local** — The attacker measures timing, power, EM, or cache behavior from a local position (same machine, physical probe, shared VM). Historically applied to: Minerva/ECDSA nonce timing (CVE-2019-15809), most cache-based AES attacks (Bernstein 2005), compiler-induced constant-time violations (CVE-2025-13912, wolfSSL LLVM side-channel). The key distinction: the attacker needs high-precision measurements (cycle-level or instruction-level) that are not reliably obtainable over a network — they need co-location, physical access, or a shared-resource position.
- **AV:Physical** — The attacker needs direct physical contact with the device. Applied to: fault injection (voltage glitching, clock glitching), direct EM probing, power analysis on bare-metal embedded devices. Most DPA/SPA attacks on smartcards and HSMs fall here.

**Investigation pattern for Attack Vector determination:**
1. What measurement does the attack require? Network round-trip timing (millisecond precision) → potentially AV:N. CPU cycle counting, cache probing, or instruction-level timing (nanosecond precision) → AV:L. Physical probe or power trace → AV:P.
2. Check precedent: use cve_lookup to find CVEs for the same algorithm + same attack class. Their AV values establish how this attack class has been scored historically.
3. Present both the technical measurement requirement AND the precedent CVE AV values. The engineer uses both to determine appropriate scoring.

**Common pattern — compiler-induced constant-time violations:** CVE-2025-13912 (wolfSSL LLVM side-channel) was scored AV:Local, AC:High, PR:High, CVSS 4.0: 1.0 (LOW). The rationale: exploiting compiler-introduced branches requires the attacker to have precise knowledge of the target binary (specific compiler, version, optimization level, target architecture) and high-precision local timing measurements. Network-based exploitation of branch-vs-cmov differences is generally impractical due to the small timing delta (individual instruction differences, not algorithmic differences).

**Common pattern — ECDSA nonce timing:** Predominantly scored AV:Local because exploiting them requires either (a) co-location for cache-based measurement, or (b) high-precision local timing to distinguish nonce bit-lengths. Network-based ECDSA timing attacks exist in theory but require impractically many measurements due to network jitter. Historical precedent: CVE-2019-15809 (Minerva) was AV:Local.

**Common pattern — software multiply/divide timing (e.g., `__muldi3` on RV32I):** The timing differences per operation are small (cycles, not milliseconds) and require statistical analysis across many operations with high-precision timing — conditions typically requiring local access or co-residency.

## Deep Dive: Clangover — When the Compiler Is the Adversary

The Clangover attack (2024) is the most concrete demonstration of compiler-introduced timing leaks. The specific vulnerability:

- **Target function**: `poly_frommsg` in the ML-KEM (Kyber) reference implementation
- **What the C code does**: Performs a conditional move (constant-time selection) based on message bits
- **What Clang 15-18 do**: Under `-Os`, `-O1`, and other optimization flags, the compiler recognizes that the code is essentially performing a bit test and replaces the constant-time conditional move with a secret-dependent branch instruction
- **Result**: Full ML-KEM 512 secret key recovery in 5-10 minutes on an Intel Core i7-13700H, using end-to-end decapsulation timing measurements

The fix was elegant but revealing: the conditional move was moved to a separate compilation unit (a different `.c` file compiled independently). This prevents the compiler from "seeing through" the abstraction and recognizing the bit-test pattern. But it's fragile — link-time optimization (LTO) could re-enable the optimization by inlining across compilation units.

**Triage implications**: When evaluating a side-channel report, the question "is this code constant-time?" cannot be answered by reading the C source. The correct question is "is this code constant-time when compiled with [specific compiler] at [specific optimization level] for [specific target architecture]?" Source-level analysis is necessary but not sufficient.

## Deep Dive: PQC Side-Channel Attacks (ML-KEM and ML-DSA)

Post-quantum algorithms have unique side-channel attack surfaces beyond the KyberSlash division timing:

**ML-DSA rejection sampling**: Dilithium's signing algorithm uses rejection sampling — it generates a candidate signature, checks if it meets a norm bound, and retries if not. The number of retries depends on the secret key. If the retry count is observable (through timing, through the number of RNG calls, through power trace length), it leaks information about the secret key. Deep-learning-assisted power analysis has demonstrated key recovery from just 16 power traces by learning the relationship between trace patterns and secret key coefficients.

**ML-KEM decapsulation oracle**: ML-KEM's IND-CCA security relies on the Fujisaki-Okamoto transform, which re-encrypts during decapsulation to verify ciphertext validity. If decapsulation failure is distinguishable from success (through timing, error codes, or any other channel), the attacker has a plaintext-checking oracle that can recover the secret key. This is structurally analogous to Bleichenbacher's RSA padding oracle — the same fundamental principle (Principle 1: The Oracle Principle) applied to a different algorithm.

**NTT butterfly operations**: The Number Theoretic Transform (used in both ML-KEM and ML-DSA for polynomial multiplication) involves "butterfly" operations — multiply-and-add/subtract pairs that process coefficients. Power analysis can extract individual coefficient values from the power consumption during butterfly operations, especially when masking countermeasures are insufficient.

**Montgomery ladder for scalar multiplication**: The CSwap (conditional swap) pattern used in Montgomery ladder implementations must be implemented via XOR masking — never via branching. The ladder itself processes every scalar bit identically (one doubling + one differential addition), making it naturally regular. Curve25519's design leverages this. However, as LadderLeak showed, even "naturally regular" algorithms can leak through auxiliary operations like coordinate conversion.
