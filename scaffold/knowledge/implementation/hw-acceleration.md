# Hardware Crypto Acceleration

> One-line summary: CryptoDevCb lifecycle contracts and async crypto flow that hardware backends must honor to avoid silent corruption.

**When to read**: Implementing a CryptoDevCb backend, registering a hardware crypto device with wolfSSL, or debugging `WC_PENDING_E` async flows.

---

## CryptoDevCb Registration

| Function | Purpose |
|----------|---------|
| `wc_CryptoCb_RegisterDevice(devId, cb, ctx)` | Register a hardware callback for a device ID |
| `wolfSSL_CTX_SetDevId(ctx, devId)` | Assign device to all sessions from this context |
| `wolfSSL_SetDevId(ssl, devId)` | Assign device to a specific session |
| `wc_CryptoCb_UnRegisterDevice(devId)` | Unregister a device |

The `devId` is an application-chosen integer (not `INVALID_DEVID`). wolfSSL routes crypto operations to the registered callback when a key/context has a matching `devId`.

Requires `WOLF_CRYPTO_CB` to be defined in `user_settings.h`.

## Callback Signature

```c
int myCryptoCb(int devId, wc_CryptoInfo *info, void *ctx);
```

| Return value | Meaning |
|-------------|---------|
| `0` | Success, output is ready |
| `CRYPTOCB_UNAVAILABLE` | This device cannot handle this operation; fall back to software |
| `WC_PENDING_E` | Async: operation started, call again later |
| Other negative | Fatal error |

The `wc_CryptoInfo` struct contains a tagged union. Check `info->algo_type` to determine which operation is requested, then access the corresponding union member.

## Primitive Lifecycle and the Reuse-After-Final Contract

wolfCrypt primitives follow: **Init -> SetKey -> Update (0+) -> Final -> Free**.

Callers frequently reuse objects in tight loops **without** calling Init or Free between iterations:

- **TLS PRF / HKDF Expand**: HMAC Update -> Final repeatedly with same key
- **PBKDF2**: Iterative HMAC reuse across thousands of rounds
- **CBC-MAC / CMAC**: Reuses cipher objects across multiple messages

**Critical for hardware backends**: After Final, hardware state is consumed. The object must support the next Update/Final cycle immediately without re-calling SetKey. Two strategies: **eager** (re-run HW setup in Final) or **lazy** (detect and re-init at next Update).

Failure to honor this causes silent data corruption in TLS key derivation -- handshakes complete but produce wrong keys.

**Before implementing any primitive**: (1) read the full software SetKey/Update/Final to understand state flags, (2) grep `wolfcrypt/src/` and `src/` for loop callers, (3) match the software reuse contract exactly.

## Async Crypto Flow (WC_PENDING_E)

Requires `WOLFSSL_ASYNC_CRYPT`. Flow: CryptoDevCb starts hardware, returns `WC_PENDING_E` -> wolfSSL propagates to caller -> caller polls via `wolfSSL_AsyncPoll` -> wolfSSL re-invokes callback -> callback detects completion, returns `0`.

## Operations That Can Be Offloaded

| Category | Operations | `algo_type` values |
|----------|-----------|-------------------|
| Hashing | SHA-256, SHA-384, SHA-512, etc. | `WC_ALGO_TYPE_HASH` |
| HMAC | All hash variants | `WC_ALGO_TYPE_HMAC` |
| Symmetric | AES-CBC, AES-GCM, AES-CCM, etc. | `WC_ALGO_TYPE_CIPHER` |
| RSA | Sign, verify, encrypt, decrypt | `WC_ALGO_TYPE_PK`, `info->pk.type == WC_PK_TYPE_RSA` |
| ECC | Sign, verify, shared secret (ECDH) | `WC_ALGO_TYPE_PK`, `info->pk.type == WC_PK_TYPE_ECDSA` / `WC_PK_TYPE_ECDH` |
| RNG | Random number generation | `WC_ALGO_TYPE_RNG` |

Return `CRYPTOCB_UNAVAILABLE` for any operation your hardware does not support. wolfSSL falls back to software transparently.

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| TLS handshake completes but data is garbled | Reuse-after-Final contract violated; HMAC produces wrong output on 2nd+ iteration | Your CryptoDevCb's HMAC Final |
| Callback never invoked | `devId` mismatch or `WOLF_CRYPTO_CB` not defined | `user_settings.h`, `wolfSSL_SetDevId` |
| Software fallback always used | Callback returns `CRYPTOCB_UNAVAILABLE` for the operation (possibly wrong `algo_type` dispatch) | Your CryptoDevCb switch/case |
| Hang during async handshake | `WC_PENDING_E` returned but completion never signaled | Async polling logic |
| Crash in `wc_CryptoCb_*` | `info` union member accessed without checking `algo_type` first | Your CryptoDevCb |

## What This File Does NOT Cover

- Vendor-specific hardware setup (register configuration, clock enable, DMA) -- see `platforms/` files
- Intel QAT, PKCS#11, or TPM integration (separate wolfSSL modules with their own APIs)
- Software-only wolfCrypt API usage (see wolfSSL documentation)
- TLS-level session configuration (certificates, cipher suites)
