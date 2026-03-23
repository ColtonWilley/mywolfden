---
paths:
  - "repos/wolftpm/**"
  - "**/wolftpm/**"
---

# wolfTPM Patterns

## Overview
wolfTPM is a portable TPM 2.0 library built on wolfCrypt. Supports SPI, I2C, and /dev/tpmrm0 (Linux TRM) interfaces.

## Common Issues

### Communication Interface
- Linux: `/dev/tpmrm0` (kernel TRM) — most common, requires `tpm` group membership
- Linux: `/dev/tpm0` (direct access) — single-user, no resource manager
- SPI: embedded platforms, requires SPI HAL implementation
- I2C: some embedded TPMs use I2C interface
- **Common error**: Permission denied on `/dev/tpmrm0` → add user to `tpm` group

### Key Operations
- Primary keys: created under storage hierarchy (SRK) or endorsement hierarchy (EK)
- `wolfTPM2_CreatePrimaryKey()` for hierarchy root keys
- `wolfTPM2_CreateKey()` for child keys under a primary
- Key persistence: `wolfTPM2_NVStoreKey()` to save key in NV RAM
- **Common mistake**: Not flushing transient objects → TPM runs out of handles

### TLS with TPM
- wolfTPM + wolfSSL integration: use TPM for TLS private key operations
- `wolfTPM2_SetCryptoDevCb()` to register TPM as crypto callback
- `wolfTPM2_ClearCryptoDevCb()` to unregister — must be called before re-registering or during cleanup
- Server cert key stored in TPM → `wolfSSL_CTX_use_PrivateKey_buffer()` with TPM key
- **Common issue**: Slow TLS handshake due to TPM RSA operations (~500ms for RSA 2048 on typical TPM)
- **Common issue**: Stale crypto callback state after retry/re-init can cause hard-to-trace errors

### Sealing / Unsealing
- Seal data to PCR state: `wolfTPM2_Seal()` / `wolfTPM2_Unseal()`
- Data only accessible when PCR values match (platform integrity)
- PCR extend: `wolfTPM2_PCRExtend()` — irreversible, accumulates measurements
- **Common issue**: PCR values change after firmware update → sealed data inaccessible

### Attestation
- Quote: `wolfTPM2_Quote()` — signed PCR values for remote attestation
- `wolfTPM2_VerifyQuote()` to verify on remote verifier
- AK (Attestation Key) creation under endorsement hierarchy

### Retry / Re-initialization Patterns
- Always call `wolfTPM2_ClearCryptoDevCb()` before re-registering the callback
- Unload transient key handles between retry attempts (`wolfTPM2_UnloadHandle()`)
- Zero out key and context structs before re-initialization
- On Windows TBS (`WOLFTPM_WINAPI`), full cleanup is especially critical — stale state surfaces as TBS errors that can be difficult to diagnose
- Pattern: `ClearCryptoDevCb` → `UnloadHandle` on all transient keys → zero structs → re-init → `SetCryptoDevCb`

### Build
- `./configure --enable-devtpm` for Linux kernel TRM
- `./configure --enable-swtpm` for software TPM (testing)
- Requires wolfSSL: `--with-wolfssl=/path/to/wolfssl`
- Embedded: implement `TPM2_IoCb()` for SPI/I2C communication
