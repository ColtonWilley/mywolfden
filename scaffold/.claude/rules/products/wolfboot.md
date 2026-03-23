---
paths:
  - "repos/wolfboot/**"
  - "**/wolfboot/**"
  - "**/wolfBoot/**"
---

# wolfBoot Patterns

## Overview
wolfBoot is a portable secure bootloader using wolfCrypt for firmware authentication. Supports ECC, RSA, and Ed25519 for image signing.

## Common Issues

### Image Signing
- Sign firmware images with `sign.py` or `wolfBoot/tools/keytools/sign`
- Key pair generated with `keygen` tool → public key compiled into bootloader
- **Common mistake**: Signing with wrong key → boot fails (image auth failure)
- Image format: wolfBoot header + signed firmware payload
- Header contains version, digest, signature, and partition info

### Partition Layout
- Two partitions: BOOT (active) and UPDATE (staging for new firmware)
- Swap-based update: BOOT ↔ UPDATE swap with rollback capability
- **Common issue**: Partition sizes don't match → update fails silently
- Flash sector alignment required for both partitions

### Update Process
1. New firmware written to UPDATE partition
2. Set UPDATE partition flag to `IMG_STATE_UPDATING`
3. Reboot → wolfBoot verifies UPDATE image signature
4. If valid: swap BOOT ↔ UPDATE
5. New firmware runs → must call `wolfBoot_success()` to confirm
6. If not confirmed: next reboot rolls back to previous firmware

### Hardware Abstraction
- Flash drivers: implement `hal_flash_write()`, `hal_flash_erase()`, `hal_flash_lock()/unlock()`
- Custom HAL per platform in `hal/` directory
- **Common issue**: Flash erase not working correctly → partition corruption

### Build
- `make TARGET=stm32f4` (or other target)
- Signing key: `make keygen`
- `SIGN=ECC256` or `SIGN=RSA2048` or `SIGN=ED25519`
- TPM support: `WOLFBOOT_TPM=1` for TPM-based key storage
