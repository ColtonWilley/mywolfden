# wolfBoot Secure Bootloader Patterns

> One-line summary: Firmware update lifecycle, partition layout gotchas, and the critical `wolfBoot_success()` confirmation requirement.

**When to read**: Working on wolfBoot integration, debugging firmware update failures, or implementing HAL flash drivers.

---

## Update Lifecycle

The swap-based update has a mandatory confirmation step. Missing it causes automatic rollback on the next reboot.

1. New firmware written to UPDATE partition
2. Set UPDATE flag to `IMG_STATE_UPDATING`
3. Reboot -- wolfBoot verifies UPDATE image signature
4. If valid: swap BOOT <-> UPDATE
5. New firmware **must** call `wolfBoot_success()` to confirm
6. If not confirmed: next reboot rolls back to previous firmware

## Partition Layout

| Partition | Purpose | Constraint |
|-----------|---------|------------|
| BOOT | Active firmware | Flash sector aligned |
| UPDATE | Staging for new image | **Must match BOOT size exactly** |

Mismatched partition sizes cause silent update failures.

## Image Signing

- Sign with `sign.py` or `wolfBoot/tools/keytools/sign`
- Public key compiled into bootloader at build time via `keygen`
- Image format: wolfBoot header (version, digest, signature, partition info) + signed payload
- Signing with the wrong key produces auth failure at boot -- no helpful error message

## HAL Flash Integration

Implement per-platform in `hal/` directory:
- `hal_flash_write()`, `hal_flash_erase()`, `hal_flash_lock()`/`hal_flash_unlock()`
- Incorrect erase implementation leads to partition corruption

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| Boot fails after update | Signed with wrong key | `sign.py` / `keygen` key mismatch |
| Update fails silently | BOOT and UPDATE partition size mismatch | Linker script / partition config |
| Automatic rollback on reboot | `wolfBoot_success()` not called by new firmware | Application init code |
| Partition corruption | HAL flash erase not implemented correctly | `hal/` platform driver |

## What This File Does NOT Cover

- wolfBoot build system or `make` targets (see wolfBoot README)
- Detailed signing algorithm selection (ECC256 vs RSA2048 vs ED25519)
- TPM-backed key storage for wolfBoot (`WOLFBOOT_TPM=1`)
