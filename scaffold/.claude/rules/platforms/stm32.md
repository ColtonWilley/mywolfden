---
paths:
  - "**/IDE/STM32Cube/**"
  - "**/stm32*"
  - "**/STM32*"
---

# STM32 / CubeMX Platform Patterns

## Integration Methods
1. **STM32CubeMX X-CUBE-WOLFSSL pack**: official ST component, configured via CubeMX GUI
2. **Manual integration**: copy wolfSSL source into STM32 project, add `user_settings.h`
3. **Key directory**: `IDE/STM32Cube/` in wolfSSL repo for templates and examples

## Common STM32 Issues

### Stack Overflow in RTOS Task
**Symptom**: Hard fault during TLS handshake.
**Root cause**: Default FreeRTOS task stack (1024 words = 4KB) too small for TLS.
**Fix**:
- Increase task stack to 6144+ words (24KB) for RSA, 4096+ words (16KB) for ECC
- Define `WOLFSSL_SMALL_STACK` in user_settings.h
- Use `uxTaskGetStackHighWaterMark()` to check remaining stack

### Hardware RNG (TRNG)
**Required for**: All key generation, random nonces, DRBG seeding.
**Setup**: Enable RNG peripheral in CubeMX, then:
```c
#define CUSTOM_RAND_GENERATE_SEED my_rng_seed
// or
#define STM32_RNG
#define WOLFSSL_STM32_CUBEMX
```
**Common error**: `-199 (RNG_FAILURE_E)` if RNG not properly initialized.

### Hardware Crypto Acceleration
STM32 chips have varying hardware crypto support:
- **STM32F4/F7**: AES, SHA (HASH peripheral), RNG
- **STM32H7**: AES, SHA, PKA (RSA/ECC acceleration)
- **STM32L4/L5**: AES, SHA, PKA, TRNG
- **STM32U5**: AES, SHA, PKA, TRNG (TrustZone)

Enable in user_settings.h:
```c
#define WOLFSSL_STM32_CUBEMX
#define STM32_HAL_V2           // For newer HAL versions
#define STM32_CRYPTO           // Use HW AES/SHA
#define STM32_RNG              // Use HW RNG
// #define WOLFSSL_STM32_PKA   // Use PKA for RSA/ECC (H7, L4+)
```

### Linker Errors with HAL
**Symptom**: Undefined references to `HAL_RNG_GenerateRandomNumber`, etc.
**Root cause**: HAL peripheral not enabled in CubeMX project.
**Fix**: Enable required peripherals in CubeMX: RNG, HASH, CRYP (AES), PKA.

### Time Functions
**Symptom**: `time()` returns 0, cert date validation fails.
**Fix**: Implement `time()` using RTC or define `NO_ASN_TIME`.
```c
#define USER_TICKS              // Use custom tick function
// or provide time() implementation using HAL_RTC
```

## Memory Considerations by STM32 Family

| Family | Typical RAM | Recommended Config |
|--------|-------------|-------------------|
| STM32F0/L0 | 8-32KB | Too constrained for TLS. wolfCrypt only. |
| STM32F1 | 20-96KB | ECC only, SMALL_STACK, lowresource |
| STM32F4 | 128-256KB | Full TLS, prefer ECC over RSA |
| STM32F7/H7 | 256KB-1MB | Full TLS, RSA 4096 OK |
| STM32L4/L5 | 64-256KB | Full TLS with SMALL_STACK |

## IDE-Specific Notes
- **Keil MDK**: Use `IDE/MDK-ARM/` project files. Watch for optimization level affecting crypto.
- **IAR EWARM**: Use `IDE/IAR-EWARM/` project files. Enable "Allow VLA" for some crypto.
- **STM32CubeIDE (GCC)**: Standard GCC, use `-ffunction-sections -fdata-sections` + `--gc-sections` to reduce binary size.

## Additional Resources

### Vendor Documentation (Public)

**STSAFE-A110 (Public — GitHub BSD-3-Clause)**:
- STSELib host library: github.com/STMicroelectronics/STSELib — full host library for STSAFE-A secure elements
- Getting Started guide (PDF): st.com/resource/en/user_manual/um2646
- wolfSSL STSAFE examples: see wolfssl-examples/stsafe/ in the wolfSSL examples repository

**STM32 HAL Crypto (Public — GitHub)**:
- STM32CubeL4: github.com/STMicroelectronics/STM32CubeL4 — includes HAL crypto drivers
- STM32CubeH5: github.com/STMicroelectronics/STM32CubeH5 — includes HAL crypto drivers for newer families

**X-CUBE-SBSFU (Export Controlled)**:
- Secure Boot and Secure Firmware Update expansion package
- Documentation (UM2262) is publicly available: st.com/resource/en/user_manual/dm00414687
- Software download requires free ST registration + export control compliance declaration + up to 48hr approval

**Internal wolfSSL Integration Code**:
- examples-private contains ST integration code: CubeMX projects, STSAFE drivers/middleware, ST33 TPM integration, IoT Safe implementation, SFI (Secure Firmware Install)
- Includes UM_STSAFE-A110_AutV1_WolfSSL_DG.pdf — wolfSSL-specific STSAFE design guide
