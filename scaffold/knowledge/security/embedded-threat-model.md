# Embedded Threat Model

> One-line summary: physical attacks (fault injection, entropy starvation) that bypass software-correct crypto on embedded targets where wolfSSL deploys.

**When to read**: Triaging security reports on embedded platforms, evaluating whether "requires physical access" dismisses a vulnerability, or reviewing secure boot implementations.

---

## Why Embedded Is Different

Server protections absent on most MCUs: no ASLR (fixed addresses — exploits
are deterministic), no DEP/NX on Cortex-M0/M0+ (no MPU), no OS entropy pool.
A buffer overflow that hits a guard page on Linux gives code execution on
bare-metal.

## Fault Injection Attacks

Physical attacks that disrupt device operation at a precise moment to cause
incorrect execution. Relevant to any embedded wolfSSL/wolfBoot deployment
where attacker has physical access.

| Technique | Method | Precision | Cost |
|-----------|--------|-----------|------|
| Voltage glitching | Momentary supply voltage drop/spike | Nanosecond | Sub-$100 (Pico Glitcher) |
| EMFI | Electromagnetic pulse at chip | Targeted circuits | ~$1K |
| Laser | Focused laser on decapped die | Individual transistors | ~$10K+ |
| Clock glitching | Brief overclock beyond rated speed | Instruction-level | Sub-$100 |

### Common crypto targets
- **Signature verification**: skip final comparison → any signature accepted
  (breaks wolfBoot firmware verification, TLS cert verification)
- **Key validity checks**: skip validation → malformed/weak key used
- **Loop counters**: alter iteration count → incorrect computation leaks key material

### Countermeasures in code
- **Redundant computation**: perform critical op twice, compare results
- **Flow verification**: set flag before check, verify after — glitch skips check but not flag
- **Randomized execution**: process elements in random order to defeat timing prediction
- **Error detection on keys**: store keys with integrity checks (CRC/MAC)

## Demonstrated Attacks on wolfSSL Platforms

### STM32 Voltage Glitching
STM32F4 RDP bypass: voltage glitch during boot skips the RDP branch, allowing
full flash dump including embedded keys and firmware. Reproducible with
sub-$100 hardware and public scripts. STM32L05 RDP downgrade similarly
vulnerable — glitch bypasses protection without erasing memory.

**Triage implication**: On STM32 with keys in flash protected by RDP,
"requires physical access" does NOT mean "not a real vulnerability."

### ESP32 Secure Boot Bypass
EMFI bypasses ESP32 Secure Boot RSA signature verification. EM glitch
redirects Program Counter to ROM Download Mode before signature check,
giving full flash access. wolfBoot or any secure boot chain on ESP32 can
be bypassed with physical access. ESP32-C3/C6 (RISC-V) also vulnerable.

## Entropy Starvation

### Boot-Time Entropy Hole
Device boots from deterministic state → DRBG needs 256 bits of entropy →
but the device just started. Crypto operations during this window use
predictable random values.

**Consequences**: factorable RSA keys (shared prime factors across devices),
ECDSA nonce reuse (private key recoverable from two signatures), predictable
TLS session keys.

### Unreliable MCU Entropy Sources

| Source | Problem |
|--------|---------|
| Timer jitter | Fixed crystal, deterministic timing → identical across boots |
| ADC noise | Varies by temperature, not crypto-quality |
| Uninitialized SRAM | Reproducible per-cell (basis of SRAM PUFs, not random) |
| `libc rand()` | 32-bit seed, LCG algorithm — trivially enumerable |
| Hardware TRNG | Best option when available — must be initialized, conditioned, health-tested |

## ARM Cortex-M Security Properties

| Core | MPU | Division | Notes |
|------|-----|----------|-------|
| M0/M0+ | None | Software (verify constant-time) | Thumb-only |
| M3/M4 | Optional (8 regions) | Hardware (non-constant-time!) | DSP useful but verify timing |
| M7 | Optional (16 regions) | Hardware | Cache introduces timing if unmanaged |
| M23/M33/M55 | TrustZone-M | Hardware | Secure/non-secure separation; transitions have measurable timing |

**TrustZone caveat**: protects against direct memory access but NOT timing
inference. Shared bus interconnect leaks access patterns (BUSted, 2024).
Code must still be constant-time inside the secure world.

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| Secure boot accepts bad firmware | Fault injection skips signature comparison | Add redundant verification + flow checks |
| Same RSA key across device fleet | Boot-time entropy hole, weak DRBG seed | Ensure TRNG initialized before key generation |
| ECDSA private key recovered | Nonce reuse from predictable RNG | Verify `wc_InitRng_ex` seeds from hardware TRNG |
| Flash dump despite RDP enabled | STM32 voltage glitch bypasses RDP | Consider additional key protection (TPM, secure element) |
| TLS traffic decryptable | Predictable client/server random | Audit entropy source at first TLS handshake after boot |

## What This File Does NOT Cover

- Side-channel patterns in wolfSSL code (see `crypto/side-channel-patterns.md`)
- Named TLS protocol attacks (see `security/attack-principles.md`)
- Hardware acceleration security tradeoffs (see `implementation/hw-acceleration.md`)
- Specific platform build details (see `platforms/` files)
