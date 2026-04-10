# STM32 / CubeMX Platform

> One-line summary: STM32 family hardware crypto availability, memory constraints, and HAL integration patterns for wolfSSL.

**When to read**: porting wolfSSL to any STM32 family, debugging HAL crypto integration, or sizing memory for a specific STM32 target.

---

## Hardware Crypto by Family

| Family | AES (CRYP) | SHA (HASH) | PKA (RSA/ECC) | RNG | TrustZone | Notes |
|--------|-----------|------------|---------------|-----|-----------|-------|
| STM32F0/L0 | -- | -- | -- | -- | -- | Too constrained for TLS; wolfCrypt only |
| STM32F1 | -- | -- | -- | -- | -- | ECC only, SMALL_STACK, lowresource |
| STM32F4 | Yes | Yes | -- | Yes | -- | Full TLS, prefer ECC over RSA |
| STM32F7 | Yes | Yes | -- | Yes | -- | Full TLS, RSA 4096 OK |
| STM32H7 | Yes | Yes | Yes | Yes | -- | Full TLS + PKA acceleration |
| STM32L4/L5 | Yes | Yes | Yes | Yes | L5 only | Full TLS with SMALL_STACK |
| STM32U5 | Yes | Yes | Yes | Yes | Yes | Full TLS + TrustZone |
| STM32WB | Yes | -- | -- | Yes | -- | BLE SoC; limited crypto HW |

## Memory Constraints

| Family | Typical RAM | Recommended Config |
|--------|-------------|-------------------|
| STM32F0/L0 | 8-32 KB | wolfCrypt only; no TLS |
| STM32F1 | 20-96 KB | ECC only, `WOLFSSL_SMALL_STACK`, `--enable-lowresource` |
| STM32F4 | 128-256 KB | Full TLS, prefer ECC (saves ~20 KB peak heap vs RSA) |
| STM32F7/H7 | 256 KB-1 MB | Full TLS, RSA 4096 supported |
| STM32L4/L5 | 64-256 KB | Full TLS with `WOLFSSL_SMALL_STACK` |

## Hardware Acceleration Defines

```c
#define WOLFSSL_STM32_CUBEMX   // Required: enable CubeMX HAL integration
#define STM32_HAL_V2           // For newer HAL versions (most current projects)
#define STM32_CRYPTO           // Use HW AES/SHA via CRYP/HASH peripherals
#define STM32_RNG              // Use HW RNG (TRNG)
#define WOLFSSL_STM32_PKA      // Use PKA for RSA/ECC (H7, L4, L5, U5 only)
```

All corresponding peripherals MUST be enabled in CubeMX -- otherwise you get linker errors for `HAL_RNG_GenerateRandomNumber`, `HAL_HASH_*`, `HAL_CRYP_*`, etc.

## RNG Setup

The STM32 TRNG is critical for key generation and DRBG seeding:

```c
#define STM32_RNG
#define WOLFSSL_STM32_CUBEMX
// OR for manual control:
#define CUSTOM_RAND_GENERATE_SEED my_rng_seed
```

Error `-199 (RNG_FAILURE_E)` means the RNG peripheral is not initialized or not enabled in CubeMX.

## Time Source

```c
#define USER_TICKS   // Use custom tick function
// OR implement time() using HAL_RTC_GetTime()
```

Without this, `time()` returns 0 and certificate date validation fails.

## Integration Methods

1. **X-CUBE-WOLFSSL pack**: official ST managed component via CubeMX GUI
2. **Manual**: copy wolfSSL source into project, add `user_settings.h`
3. **Templates**: `IDE/STM32Cube/` in wolfSSL repo

## IDE-Specific Gotchas

- **Keil MDK**: watch for optimization level affecting crypto correctness
- **IAR EWARM**: enable "Allow VLA" for some crypto operations
- **STM32CubeIDE (GCC)**: use `-ffunction-sections -fdata-sections` + `--gc-sections` to reduce binary size

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| Hard fault during TLS handshake | Default FreeRTOS task stack (4 KB) too small | Increase to 6144+ words (24 KB) for RSA, 4096+ (16 KB) for ECC |
| `-199 (RNG_FAILURE_E)` | RNG peripheral not enabled in CubeMX | Enable RNG in CubeMX, define `STM32_RNG` |
| Undefined refs to `HAL_RNG_*`, `HAL_HASH_*`, `HAL_CRYP_*` | HAL peripheral not enabled in CubeMX | Enable required peripherals: RNG, HASH, CRYP, PKA |
| `time()` returns 0, cert validation fails | No RTC or time implementation | Implement `time()` via HAL_RTC or define `USER_TICKS` |
| PKA operations fail silently | `WOLFSSL_STM32_PKA` on a family without PKA | PKA only on H7, L4, L5, U5 |

## What This File Does NOT Cover

CubeMX step-by-step project creation, generic ARM Cortex education, STSAFE secure element integration details (see wolfSSL examples-private). See `embedded-common.md` for cross-platform patterns.
