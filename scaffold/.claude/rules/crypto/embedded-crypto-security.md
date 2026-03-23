---
paths:
  - "**/user_settings.h"
  - "**/IDE/**"
---

# Embedded and IoT Cryptographic Security

## Why Embedded Is a Different Threat Model

When wolfSSL runs on a Linux server, it benefits from the operating system's security features: virtual memory prevents one process from reading another's memory, ASLR randomizes memory layout to make exploitation harder, DEP/NX prevents executing data as code, and the OS provides high-quality entropy from hardware and interrupt timing. On an embedded microcontroller running bare-metal or under an RTOS, most or all of these protections are absent.

This means vulnerabilities that would be minor on a server — a small buffer overflow that gets caught by a guard page, or a weak PRNG seed that gets supplemented by OS entropy — can be critical on an embedded target. The embedded threat model includes physical access attacks (fault injection, power analysis) that don't apply to remote servers, and excludes protections (ASLR, DEP) that servers rely on.

## Resource Constraint Security Implications

### Memory Limitations

Embedded devices often have kilobytes, not gigabytes, of RAM. This affects security in several ways:

**Small stack sizes**: RTOS tasks typically have 4KB-16KB stacks. Deep call chains in TLS handshake processing (especially certificate chain verification, which can recurse through chain depth) can overflow the stack. A stack overflow on a device without memory protection overwrites adjacent memory — potentially including return addresses (code execution) or cryptographic keys (key leakage). This is more severe than on a server where stack overflow hits a guard page and crashes cleanly.

**Fixed-size buffers**: To avoid dynamic allocation (which may not be available or may fragment limited heap), embedded code often uses fixed-size stack or global buffers. If a TLS message exceeds the expected size, the fixed buffer overflows. The developer chose the buffer size based on "typical" inputs, but the attacker sends atypical inputs. This is why wolfSSL's `MAX_*` constants (like `MAX_HANDSHAKE_SZ`, `MAX_CERTIFICATE_SZ`) are security-critical — they define the boundary between safe and overflow.

**No heap in some configurations**: When `WOLFSSL_NO_MALLOC` is defined, all memory comes from fixed buffers. This eliminates heap overflow/use-after-free classes but introduces fixed-size buffer overflow risk if the static buffers aren't sized correctly for all possible inputs.

### No Address Space Layout Randomization (ASLR)

On bare-metal and most RTOS configurations, code and data are at fixed, known addresses. An attacker who knows the firmware image (often available through firmware updates or JTAG extraction) knows exactly where every function and variable lives in memory. This makes buffer overflow exploitation much more reliable — there's no randomization to defeat.

### No Data Execution Prevention (DEP/NX)

Many microcontrollers (especially older ARM Cortex-M0/M0+ cores) don't have an MPU (Memory Protection Unit), or the MPU isn't configured to separate code and data. This means a buffer overflow can inject and execute arbitrary code directly. On Cortex-M3/M4/M7 with MPU, DEP is possible but must be explicitly configured — many embedded projects don't set it up.

### Limited Entropy Sources

Cryptographic security depends on unpredictable random numbers for key generation, nonces, and protocol values. Servers have access to hardware RNG, interrupt timing jitter, disk I/O timing, and other entropy sources. Embedded devices may have:

- **No hardware RNG**: Many low-cost MCUs lack a hardware random number generator. The DRBG must be seeded from whatever is available — timer values, ADC noise, uninitialized SRAM (unreliable and not guaranteed to be random across boots).
- **Low-resolution timers**: On a deterministic microcontroller with a fixed clock, timer values may have low entropy. If the system boots identically each time, the timer state at DRBG initialization may be predictable.
- **No OS entropy pool**: Without an OS, there's no `/dev/urandom` or equivalent that accumulates entropy over time.

A DRBG seeded with low entropy produces predictable output. If that output is used as a TLS session key or ECDSA nonce, the attacker can potentially predict or recover secrets. For ECDSA, a partially predictable nonce is sufficient — given enough signatures with biased nonces, lattice-based techniques can recover the private key.

## Fault Injection Attacks

Fault injection is a class of physical attack where the attacker disrupts the device's operation at a precise moment to cause incorrect execution. These attacks are uniquely relevant to embedded deployments where the attacker has physical access to the device.

### Voltage Glitching

The attacker momentarily drops or spikes the device's supply voltage during a critical operation. The voltage glitch causes the CPU to skip instructions, corrupt register values, or misread memory. A well-timed glitch during a signature verification can cause the comparison to pass regardless of the actual signature value.

**How it works in practice**: The attacker monitors the device's power consumption (or electromagnetic emissions) to identify when the target operation executes. They then use a programmable power supply or FPGA-controlled switch to introduce a precisely timed voltage dip. Modern glitch attack platforms can position glitches with nanosecond precision.

**Common targets in crypto code**:
- **Signature verification**: Skip the final comparison in `if (computed_sig == received_sig)`, causing any signature to be accepted. This breaks firmware update verification (wolfBoot), TLS certificate verification, and any authentication based on signatures.
- **Conditional branches in key validation**: Skip a key validity check, causing the system to use a malformed or weak key.
- **Loop counters**: Alter the iteration count of a loop in a cryptographic algorithm, causing incorrect computation that leaks key material when compared with correct output.

### Electromagnetic Fault Injection (EMFI)

An electromagnetic pulse directed at specific parts of the chip can cause local bit flips without affecting the rest of the system. EMFI is more targeted than voltage glitching — it can affect specific circuits while leaving others undisturbed. This makes it useful for attacking specific operations within a complex computation.

### Laser Fault Injection

A focused laser beam on a decapped chip can flip specific bits in registers or SRAM. This is the most precise fault injection technique — it can target individual transistors. Laser fault injection has been demonstrated against AES, RSA, and ECC implementations, typically requiring a chip where the package has been removed (decapped) to expose the die.

### Clock Glitching

Briefly increasing the clock frequency beyond the chip's rated speed causes timing violations in the CPU's logic. Instructions that should execute in one clock cycle don't complete in time, producing incorrect results. Clock glitching is simpler to implement than voltage glitching (just need a programmable clock source) but less precise.

### Rowhammer on Embedded

While Rowhammer is typically associated with DRAM in PCs and servers, some embedded systems use DRAM (e.g., application processors running Linux). The principle is the same — rapidly accessing one memory row causes bit flips in adjacent rows due to electrical interference. This has been demonstrated for ECDSA key recovery on ARM systems where the key material is stored in DRAM.

### Fault Attack Countermeasures in Code

**Redundant computation**: Perform the critical operation twice and compare results. If a fault corrupts one execution, the results won't match.

**Instruction flow verification**: Add checks that verify the expected code path was followed. For example, set a flag before a signature verification and check it after — a glitch that skips the verification won't set the flag.

**Randomized execution order**: Process elements in random order so the attacker can't predict which operation is executing at any given time.

**Error detection codes on keys**: Store keys with integrity checks (CRC, MAC) so that fault-corrupted keys are detected before use.

## Post-Quantum Cryptography Implementation Risks

PQC algorithms (ML-KEM/Kyber, ML-DSA/Dilithium, SLH-DSA/SPHINCS+) are newer and less battle-tested than RSA/ECC. Their implementations face unique security challenges, especially on embedded targets.

### Larger Data Sizes

PQC public keys and ciphertexts are significantly larger than ECC equivalents. ML-KEM-768 has 1,184-byte public keys (vs. 32 bytes for X25519) and 1,088-byte ciphertexts. ML-DSA-65 signatures are 3,309 bytes (vs. 64 bytes for Ed25519). These larger sizes stress buffer management on constrained devices — fixed-size buffers that were adequate for ECC may overflow with PQC data.

The larger data sizes also affect TLS handshake message sizes. A TLS handshake with PQC key exchange may exceed the typical maximum fragment length, requiring fragmentation. If the fragmentation/reassembly code has buffer management issues, PQC's larger messages are more likely to trigger them.

### Side-Channel Leakage in Lattice Operations

Lattice-based algorithms (ML-KEM, ML-DSA) involve polynomial multiplication, number-theoretic transforms (NTT), and modular arithmetic. Each of these can leak through timing or power side channels if not implemented carefully.

**NTT butterfly operations** involve multiplications that can leak through power analysis. The structure of the NTT means specific coefficient values can be recovered from power traces.

**Modular reduction** after multiplication is a critical point. If reduction uses division (as in KyberSlash), the division's variable timing leaks the dividend value, which is derived from the secret key. Barrett or Montgomery reduction using only multiplication and shift is constant-time.

**Rejection sampling** in ML-DSA signature generation requires drawing random values and rejecting those outside a range. The number of rejections depends on the secret key. If the rejection loop's iteration count is observable (through timing or the number of calls to the RNG), it leaks information about the secret.

### Decapsulation Failure Oracles

ML-KEM uses an FO (Fujisaki-Okamoto) transform that re-encrypts during decapsulation to verify the ciphertext is valid. If the implementation reveals whether decapsulation succeeded or failed — through timing, error codes, or any other channel — this creates an oracle that can be used to recover the secret key. This is analogous to the Bleichenbacher/ROBOT attack on RSA PKCS#1 v1.5.

The correct implementation must handle decapsulation failure identically (in time and behavior) to success: compute a pseudorandom shared secret from the ciphertext hash instead of the decapsulated value, using constant-time selection.

### Keccak/SHAKE Implementation

Many PQC algorithms use Keccak (SHA-3/SHAKE) for hashing and expansion. On constrained devices, the 1600-bit Keccak state (200 bytes) is a significant memory allocation. Errors in Keccak expansion — processing a different number of blocks than expected, or corrupting the state between absorb and squeeze phases — can compromise the derived values. CVE-2026-3503 demonstrated this pattern with fault injection on Keccak expansion in ML-KEM/ML-DSA.

## Hardware Crypto Acceleration Security Considerations

Many embedded platforms include hardware acceleration for AES, SHA-256, RSA, or ECC. When wolfSSL uses hardware crypto (via `WOLFSSL_STM32_PKA`, `WOLFSSL_ESP32_CRYPT`, or similar), the security properties change.

### Different Attack Surface

Hardware crypto accelerators protect against software-based timing attacks — the CPU just fires off the operation and waits for completion, so software timing doesn't reveal the key. However, hardware implementations are vulnerable to power analysis (DPA/SPA) and electromagnetic attacks. The accelerator's power consumption or EM emissions during operation directly reveal information about the key.

Whether this is a concern depends on the threat model: if the attacker has physical access to measure power/EM, hardware crypto may be less secure than a carefully written software implementation with DPA countermeasures. If the attacker is remote, hardware crypto is typically more secure because it eliminates software timing leaks.

### Fallback Behavior

When hardware acceleration is available, wolfSSL uses it. When it's not (hardware busy, unsupported algorithm, wrong key size), wolfSSL falls back to software. If the software fallback has a side-channel vulnerability that the hardware path doesn't, the attacker might be able to force the fallback (by triggering conditions where hardware can't be used) and then exploit the software path.

**What to look for**: When evaluating a side-channel report, check whether the claimed vulnerability is in the hardware-accelerated path, the software fallback path, or both. If it's only in the software path, is the software path reachable in the device's configuration?

### TPM Integration

wolfTPM provides TLS integration where the TPM performs private key operations. The TPM is designed to resist physical attacks (tamper-evident packaging, active shield mesh, DPA countermeasures). However, the communication between the CPU and the TPM (typically SPI or I2C) may leak information. The command structure, response timing, and even the fact that a TPM operation is occurring can reveal information to an attacker monitoring the bus.

## Platform-Specific Embedded Security Notes

### ARM Cortex-M
- Cortex-M0/M0+: No MPU, no hardware division (uses software divide — verify constant-time), Thumb-only instruction set.
- Cortex-M3/M4: Optional MPU (8 regions), hardware division (non-constant-time!), DSP instructions useful for crypto but verify timing.
- Cortex-M7: Optional MPU (16 regions), cache (introduces cache-based timing if not managed), dual-issue pipeline complicates timing analysis.
- Cortex-M23/M33/M55: TrustZone-M for secure/non-secure separation. Crypto can run in the secure world, protected from non-secure code. However, TrustZone transitions have measurable timing, and the secure monitor's behavior can leak through timing side channels.

### RISC-V Embedded
- Rapidly growing in embedded crypto applications.
- No standardized security extensions yet (PMP exists but is limited).
- Crypto extensions (Zkn for NIST algorithms, Zks for ShangMi) provide constant-time operations when available.
- Implementation-dependent timing behavior for multiplication and division — must verify per-core.

### RTOS Considerations
- Task preemption during crypto operations can affect timing measurements — both helping (adding noise) and hurting (creating deterministic patterns if the scheduler is predictable).
- Shared memory between tasks: no process isolation means a compromised task can read crypto state from another task's memory.
- Interrupt handlers during crypto: an interrupt during a key operation that saves registers to the stack exposes key material in the stack frame. If interrupts are not disabled during crypto, this is a potential leak path.

## Practical Fault Injection on wolfSSL Deployment Platforms

Understanding real-world fault injection capabilities on platforms where wolfSSL is deployed helps contextualize reports. These are not theoretical — they have been demonstrated with commercially available tools.

### STM32 Voltage Glitching

The STM32 family is one of the most common wolfSSL deployment targets. Practical attacks have been demonstrated on multiple variants:

**STM32F4**: Voltage glitching attacks using tools like the Pico Glitcher + findus Python library bypass Read-Out Protection (RDP). The attack targets the RDP check during boot — a precisely timed voltage dip causes the CPU to skip the branch instruction that gates memory readout, allowing the attacker to dump the entire flash contents. This includes any embedded keys, certificates, or firmware. The attack is reproducible with sub-$100 hardware and publicly available scripts.

**STM32L05**: The RDP downgrade routine is vulnerable — a glitch during the downgrade check bypasses the protection mechanism without erasing memory. The attacker gains read access to internal flash and SRAM, including any cryptographic keys stored in memory.

**Triage implication**: For embedded deployments on STM32, "requires physical access" does not mean "not a real vulnerability." If the device stores private keys in flash and relies on RDP for protection, and wolfSSL is used for TLS with those keys, a fault injection attack that extracts the keys compromises all TLS connections to that device.

### ESP32 Fault Injection

ESP32 is another major wolfSSL deployment platform, especially for IoT.

**Secure Boot bypass**: Electromagnetic fault injection has been demonstrated to bypass ESP32's Secure Boot RSA signature verification. The attack targets ROM code running on the CPU shortly before signature verification — an EM glitch redirects the Program Counter to the ROM's Download Mode, giving the attacker full access to flash without passing signature verification. This means wolfBoot or any secure boot chain using wolfSSL on ESP32 can be bypassed with physical access.

**ESP32-C3/C6**: Newer RISC-V-based ESP32 variants are also vulnerable to fault injection attacks, though the specific attack parameters differ.

**Triage implication**: Reports about secure boot or firmware verification vulnerabilities on ESP32/STM32 should consider fault injection as a realistic attack vector. The tools are publicly available, the techniques are well-documented, and the attacks take minutes to hours, not days.

## Deep Dive: Entropy Starvation in Embedded Systems

### The Boot-Time Entropy Hole

On a server, the OS accumulates entropy from many sources over time — hardware RNG, interrupt timing, disk I/O, network packet timing. When a process requests random numbers, the entropy pool is typically well-seeded. On an embedded device, the situation is fundamentally different:

1. The device boots from a deterministic state (flash image is identical across all units)
2. The first thing wolfSSL does is initialize the DRBG (Deterministic Random Bit Generator)
3. The DRBG needs a seed with at least 256 bits of entropy
4. But the device just booted — where does the entropy come from?

This is the "boot-time entropy hole" — the window between device startup and the point where sufficient entropy has been collected. Any cryptographic operations performed during this window (including TLS handshakes, key generation, ECDSA signatures) may use predictable random values.

### What Happens with Low Entropy

**Factorable RSA keys**: Bishop Fox research demonstrated that weak RNG in IoT devices produces RSA keys where the two prime factors are partially predictable. When the same weak seed produces the same prime factor across different devices, the keys share a common factor and can be trivially broken using GCD. This was found in production IoT devices at scale.

**ECDSA nonce reuse**: If two ECDSA signatures use the same nonce `k` (because the RNG repeated), the private key can be recovered with simple algebra from the two signatures. Even partially predictable nonces enable lattice-based key recovery (see Minerva/LadderLeak).

**Predictable TLS session keys**: If the client or server random in the TLS handshake is predictable, the derived session keys are predictable, and an eavesdropper can decrypt all traffic.

### Unreliable Entropy Sources on MCUs

**Timer jitter**: On a microcontroller with a fixed crystal oscillator and deterministic instruction timing, timer values at boot may be identical across boots and across devices. There is no jitter to measure.

**ADC noise**: Reading an analog-to-digital converter with a floating input produces noise, but the noise characteristics vary by hardware, temperature, and may not provide cryptographic-quality entropy.

**Uninitialized SRAM**: SRAM cells have manufacturing-dependent startup states, but these states are NOT random — they are determined by the physical properties of each cell and are largely reproducible across boots (this is the basis of SRAM PUFs). Using uninitialized SRAM as an entropy source is unreliable.

**`libc rand()`**: NEVER acceptable for cryptographic purposes. The seed is typically a 32-bit value (trivially enumerable), and the PRNG algorithm (LCG) has known weaknesses. An attacker can derive the seed from a few outputs using tools like untwister.

**Hardware RNG**: When available (many Cortex-M4+ MCUs have TRNG peripherals), this is the best option. But the TRNG must be properly initialized, its output should be conditioned, and health tests should verify it's producing actual random data (some TRNG designs can produce constant output under certain voltage/temperature conditions).

## ARM TrustZone-M Side Channels

ARM TrustZone-M provides hardware-enforced isolation between "secure world" and "non-secure world" code on Cortex-M23, M33, and M55 processors. wolfSSL running in the secure world is protected from non-secure code — TrustZone prevents direct memory access to secure-world data. However, side channels cross the security boundary.

### BUSted Attacks (2024)

Research demonstrated that the shared bus interconnect on TrustZone-M processors creates a timing side channel. When multiple bus masters (secure and non-secure) access the same bus slave simultaneously, the bus arbiter introduces timing variations. The non-secure world can observe these timing variations to infer the secure world's memory access patterns.

This is significant because it means a compromised non-secure application can extract information about cryptographic operations running in the secure world — even though TrustZone hardware isolation prevents direct memory access. The attack works on state-of-the-art Armv8-M MCUs running Trusted Firmware-M (TF-M).

### SCFARM Tool (2024)

SCFARM is the first side-channel detection tool tailored specifically for ARM TrustZone-M. It uses symbolic execution and static analysis to detect timing side channels in compiled secure-world programs. It analyzes the binary (not source code) and identifies instruction sequences whose execution time depends on secret data.

### Triage Implication

For wolfSSL deployments using TrustZone (where crypto runs in the secure world), reports about timing side channels cannot be dismissed with "but TrustZone protects the keys." TrustZone protects against *direct access* but not against *timing-based inference*. The code must still be constant-time even inside the secure world.
