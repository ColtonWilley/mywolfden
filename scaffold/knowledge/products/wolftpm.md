# wolfTPM Integration Patterns

> One-line summary: TPM 2.0 retry/cleanup sequences and wolfSSL crypto callback wiring that cause silent failures if done wrong.

**When to read**: Working on wolfTPM + wolfSSL TLS integration, debugging TPM retry failures, or handling crypto device callbacks.

---

## TLS Integration via Crypto Callbacks

wolfTPM registers itself as a wolfSSL crypto device so the TPM handles private key operations during TLS handshakes.

| Step | API | Notes |
|------|-----|-------|
| Register callback | `wolfTPM2_SetCryptoDevCb()` | Links TPM to wolfSSL via `wolfSSL_SetDevId()` |
| Use in TLS | `wolfSSL_CTX_use_PrivateKey_buffer()` | Cert key lives in TPM, not in memory |
| Unregister | `wolfTPM2_ClearCryptoDevCb()` | **Must** call before re-registering or during cleanup |

RSA 2048 operations take ~500ms on typical TPMs. This is expected, not a bug.

## Key Handle Lifecycle

- Primary keys: `wolfTPM2_CreatePrimaryKey()` under storage (SRK) or endorsement (EK) hierarchy
- Child keys: `wolfTPM2_CreateKey()` under a primary
- Persist to NV: `wolfTPM2_NVStoreKey()`
- **Transient handles must be flushed** with `wolfTPM2_UnloadHandle()` or the TPM runs out of handle slots silently

## Retry / Re-initialization Pattern

The correct cleanup-and-retry sequence is strict. Skipping steps causes stale state errors that are hard to trace, especially on Windows TBS (`WOLFTPM_WINAPI`).

```
1. ClearCryptoDevCb()
2. UnloadHandle() on ALL transient keys
3. Zero out key and context structs
4. Re-initialize TPM context
5. SetCryptoDevCb()
```

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| Permission denied on `/dev/tpmrm0` | User not in `tpm` group | OS config, not code |
| TPM out of handles / resource errors | Transient objects not flushed | `wolfTPM2_UnloadHandle()` |
| Stale crypto callback after retry | `ClearCryptoDevCb()` not called before re-register | `wolfTPM2_SetCryptoDevCb()` |
| TBS errors on Windows retry | Incomplete cleanup on WOLFTPM_WINAPI | Full 5-step retry pattern above |
| Sealed data inaccessible after FW update | PCR values changed (extend is irreversible) | `wolfTPM2_PCRExtend()` |
| Hard-to-trace errors after re-init | Structs not zeroed between attempts | Zero all key/ctx structs |

## What This File Does NOT Cover

- TPM 2.0 specification education or architecture overview
- SPI/I2C HAL implementation details for embedded platforms
- wolfTPM build/install instructions (see wolfTPM README)
