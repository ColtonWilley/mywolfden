# wolfHSM Integration Patterns

> One-line summary: client-server HSM architecture, crypto offload via devId, key management lifecycle, and RNG dispatch chain that silently fails if wc_InitRng_ex is skipped.

**When to read**: Integrating wolfHSM, debugging crypto offload failures, working with HSM key caching/NVM, or troubleshooting RNG issues on HSM ports.

---

## Architecture

Client-server model. Server runs on HSM coprocessor, processes one request at
a time. Client library links into user apps. Transport is pluggable (shared
memory, TCP, custom). Each `whClientContext` is a 1:1 connection to a server.

## Crypto Offload via devId

Pass `WOLFHSM_DEV_ID` to any wolfCrypt API → operation executes on HSM server.
Pass `INVALID_DEVID` → runs locally. Uses wolfCrypt's `WOLF_CRYPTO_CB` framework.

```c
wc_AesInit(&aes, NULL, WOLFHSM_DEV_ID);   /* Remote on HSM */
wc_AesInit(&aes, NULL, INVALID_DEVID);     /* Local */
```

If server doesn't support an algorithm, returns `CRYPTOCB_UNAVAILABLE`.

## Key Management

| Function | Purpose |
|----------|---------|
| `wh_Client_KeyCache(keyId, ...)` | Store key in RAM cache (limited by `WOLFHSM_NUM_RAMKEYS`) |
| `wh_Client_KeyCommit(keyId)` | Persist cached key to NVM |
| `wh_Client_KeyEvict(keyId)` | Remove from cache, keep NVM copy |
| `wh_Client_KeyExport(keyId, ...)` | Read key data back to client |
| `wh_Client_KeyErase(keyId)` | Remove from cache AND NVM |
| `wh_Client_KeyRevoke(keyId)` | Clear usage flags, set `NONMODIFIABLE` — key returns `WH_ERROR_USAGE` |

Use `wh_Client_SetKeyAes(&aes, keyId)` to bind cached key to wolfCrypt object.
**IV must be set separately** with `wc_AesSetIV()` — `wc_AesSetKey()` is not called for HSM keys.

## NVM Key Policy Flags

| Flag | Effect |
|------|--------|
| `WH_NVM_FLAGS_NONEXPORTABLE` | Cannot read/export |
| `WH_NVM_FLAGS_NONMODIFIABLE` | Cannot modify or destroy |
| `WH_NVM_FLAGS_NONDESTROYABLE` | Cannot destroy |
| `WH_NVM_FLAGS_USAGE_*` | Restrict to specific ops (encrypt, sign, wrap, derive) |
| `WH_NVM_FLAGS_NONE` | **Not permitted for any crypto use** (common misconfiguration) |

## RNG Dispatch Chain (Critical)

`wc_InitRng_ex(rng, heap, devId)` is **mandatory** — it assigns `rng->devId`.
Without it, `wc_RNG_GenerateBlock` never dispatches to the crypto callback.

Two distinct callback algo types:
- `WC_ALGO_TYPE_SEED` — called during `wc_InitRng_ex` to seed Hash DRBG (recommended pattern)
- `WC_ALGO_TYPE_RNG` — called during `wc_RNG_GenerateBlock` when `WC_NO_HASHDRBG` is defined

**Common pitfall when switching TRNG patterns**: if switching from TRNG-seeds-DRBG
to TRNG-replaces-DRBG (`WC_NO_HASHDRBG`), the platform callback's `WC_ALGO_TYPE_RNG`
case may be gated on `#ifndef CUSTOM_RAND_GENERATE_SEED`, silently falling through
to `RNG_FAILURE_E`.

## Platform Ports

| Port | Status | Notes |
|------|--------|-------|
| POSIX | Public | Shared memory/TCP/Unix + RAM/file NVM. Use for dev/eval |
| Infineon Aurix TC3xx | NDA | ARM Cortex-M3 HSM core, HW TRNG/AES128/ECDSA |
| ST Micro SPC58N | NDA | PowerPC HSM core, HW TRNG/AES128 |

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| Crypto runs locally instead of HSM | `INVALID_DEVID` passed instead of `WOLFHSM_DEV_ID` | Check `devId` on all wolfCrypt init calls |
| `RNG_FAILURE_E` (-199) | `wc_InitRng_ex` not called — `rng->devId` stays `INVALID_DEVID` | Always call `wc_InitRng_ex(rng, heap, WOLFHSM_DEV_ID)` |
| `WH_ERROR_NOSPACE` from KeyCache | All `WOLFHSM_NUM_RAMKEYS` slots full | Commit keys to NVM, then evict from cache |
| Zero IV in AES encryption | IV not set after `wh_Client_SetKeyAes` | Call `wc_AesSetIV()` separately |
| Key unusable despite being cached | `WH_NVM_FLAGS_NONE` set (no usage flags) | Set `WH_NVM_FLAGS_USAGE_ANY` or specific flags |
| CMAC fails with cached key | Standard `wc_AesCmacGenerate_ex` requires client key | Use `wh_Client_AesCmacGenerate` for HSM keys |

## What This File Does NOT Cover

- wolfTPM integration (see `products/wolftpm.md`)
- General CryptoDevCb patterns (see `implementation/hw-acceleration.md`)
- NDA-specific port details (contact support@wolfssl.com)
