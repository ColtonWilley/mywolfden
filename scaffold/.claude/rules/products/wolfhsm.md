---
paths:
  - "repos/wolfhsm/**"
  - "**/wolfhsm/**"
  - "**/wolfHSM/**"
---

# wolfHSM Patterns

## What wolfHSM Is

wolfHSM is a portable, open-source client-server framework for hardware security modules. The server runs in a trusted environment (typically an HSM coprocessor) and handles cryptographic operations, key management, and non-volatile storage. Client applications link against the wolfHSM client library and communicate with the server via an abstract transport layer. The primary value proposition is that client apps can use standard wolfCrypt APIs directly, and wolfHSM automatically offloads operations to the HSM core as remote procedure calls -- no vendor-specific HSM code required in the application.

wolfHSM's only dependency is wolfCrypt. It supports PKCS11, AUTOSAR SHE, TPM 2.0 interfaces, SecOC integration, and FIPS 140-3. It provides every algorithm in wolfCrypt (including SM2/SM3/SM4 and post-quantum algorithms like Kyber, LMS, XMSS) regardless of what the silicon vendor's hardware accelerates.

## Architecture: Client-Server Model

The server is a standalone application on the HSM core. It processes one client request at a time to ensure isolation. The client is a library linked into user applications. Each client context (`whClientContext`) represents a one-to-one connection to a server -- multiple servers require multiple client contexts. Communication uses a split transaction model: request functions send without blocking, response functions poll until the reply arrives.

The transport layer is pluggable. Built-in transports include shared memory (`wh_transport_mem`) and POSIX TCP sockets. Custom transports implement the `whTransportClientCb` interface and can be swapped without changing application code.

## Client Initialization

Configuring a client requires binding a transport to the comm layer, then initializing the client context:

```c
#include "wolfhsm/client.h"
#include "wolfhsm/wh_transport_mem.h"

whTransportMemConfig transportCfg = { /* shared memory config */ };
whTransportMemClientContext transportCtx = {0};
whTransportClientCb transportCb = {WH_TRANSPORT_MEM_CLIENT_CB};

whCommClientConfig commCfg = {
    .transport_cb      = transportCb,
    .transport_context = (void*)&transportCtx,
    .transport_config  = (void*)&transportCfg,
    .client_id         = 123,
};

whClientConfig clientCfg = { .comm = &commCfg };
whClientContext clientCtx = {0};
wh_Client_Init(&clientCtx, &clientCfg);
```

## Crypto Offload via wolfCrypt Device Callbacks

The defining feature: pass `WOLFHSM_DEV_ID` as the `devId` parameter to any wolfCrypt API call, and the operation executes on the HSM server transparently. To run locally instead, pass `INVALID_DEVID`. This uses wolfCrypt's crypto callback (cryptocb) framework under the hood.

```c
/* Remote execution on HSM server */
wc_AesInit(&aes, NULL, WOLFHSM_DEV_ID);
wc_AesSetKey(&aes, key, AES_128_KEY_SIZE, iv, AES_ENCRYPTION);
wc_AesCbcEncrypt(&aes, cipherText, plainText, sizeof(plainText));

/* Local execution -- only the devId changes */
wc_AesInit(&aes, NULL, INVALID_DEVID);
```

If the server does not support a requested algorithm, the API returns `CRYPTOCB_UNAVAILABLE`.

## Key Management

Keys are cached in server RAM and optionally committed to NVM for persistence:

- `wh_Client_KeyCache()` -- stores key in RAM cache, returns a `keyId`. Pass `WOLFHSM_KEYID_ERASED` to auto-assign an ID. Cache slots are limited by `WOLFHSM_NUM_RAMKEYS`.
- `wh_Client_KeyCommit()` -- persists a cached key to NVM.
- `wh_Client_KeyEvict()` -- removes from cache but keeps NVM copy.
- `wh_Client_KeyExport()` -- reads key data back to client.
- `wh_Client_KeyErase()` -- removes from both cache and NVM.
- `wh_Client_KeyRevoke()` -- clears all usage flags and sets `WH_NVM_FLAGS_NONMODIFIABLE`. Revoked keys remain in storage but return `WH_ERROR_USAGE` for crypto operations.

To use a cached HSM key with wolfCrypt, call the algorithm-specific setter (e.g., `wh_Client_SetKeyAes(&aes, keyId)`) before invoking the crypto operation. The IV must be set separately with `wc_AesSetIV()`.

## Non-Volatile Memory (NVM)

NVM stores objects with metadata (ID, access, flags, label, length). It uses a dual-partition flash architecture with epoch counters for crash recovery -- transactions are always atomic. Duplicate IDs are allowed but only the latest is readable.

Important NVM flags for key policy:
- `WH_NVM_FLAGS_NONEXPORTABLE` -- data cannot be read/exported
- `WH_NVM_FLAGS_NONMODIFIABLE` -- cannot modify or destroy
- `WH_NVM_FLAGS_NONDESTROYABLE` -- cannot destroy
- `WH_NVM_FLAGS_USAGE_*` -- restrict key to specific operations (encrypt, decrypt, sign, verify, wrap, derive)

Keys stored with `WH_NVM_FLAGS_NONE` are treated as not permitted for any cryptographic use.

## Platform Ports

wolfHSM requires a "port" to run on real hardware -- the port provides transport drivers, NVM flash drivers, and boot initialization. Available ports:

- **POSIX** -- public, supports shared memory/TCP/Unix transports and RAM/file-based NVM simulators. Use for development and testing.
- **Infineon Aurix TC3xx** -- NDA required. ARM Cortex M3 HSM core at 100MHz, hardware TRNG/AES128/ECDSA/ED25519/SHA.
- **ST Micro SPC58N** -- NDA required. PowerPC HSM core, hardware TRNG/AES128.
- **Infineon Aurix TC4xx, Traveo T2G, Renesas RH850/RL78, NXP S32** -- coming soon, NDA required.

Restricted ports are only available to qualified customers. Direct inquiries to support@wolfssl.com.

## Customization Points

**Custom server callbacks**: register functions on the server (via `wh_Server_RegisterCustomCb()`) that clients invoke by ID. Useful for peripheral control, authentication routines, or secure boot staging. The callback receives a request with typed data payload and returns a response.

**DMA callbacks**: hooks for address translation and cache coherency when the server accesses client memory directly. Register via `wh_Server_DmaRegisterCb32()`/`Cb64()`. Essential when porting to new shared-memory architectures.

**DMA address allow list**: restricts which client memory regions the server may access. Second layer of defense on top of hardware memory protection.

## Common Issues and Mistakes

### Cache slot exhaustion
`wh_Client_KeyCache()` returns `WH_ERROR_NOSPACE` when all `WOLFHSM_NUM_RAMKEYS` slots are full. Keys that exist in both cache and NVM are auto-evicted to make room, but cache-only keys are not. Fix: commit important keys to NVM and evict after committing.

### Forgetting to initialize NVM on the client
Client NVM operations require calling `wh_Client_NvmInit()` first. This is currently a no-op on the server side but may trigger initialization in future versions. Always include it.

### Wrong devId for crypto offload
Passing `INVALID_DEVID` instead of `WOLFHSM_DEV_ID` silently runs crypto locally. Passing `WOLFHSM_DEV_ID` without initializing the wolfHSM client first causes undefined behavior. Verify client init before any HSM crypto call.

### IV not set separately for HSM keys
When using `wh_Client_SetKeyAes()` to reference an HSM-stored key, `wc_AesSetKey()` is not called (since the key is on the server). The IV must be set independently via `wc_AesSetIV()`. Forgetting this results in a zero IV.

### NVM flags and key revocation confusion
Keys with `WH_NVM_FLAGS_NONE` (no usage flags set) are not usable for crypto. This looks like revocation but is actually a misconfiguration. When caching a key, always set appropriate `WH_NVM_FLAGS_USAGE_*` flags or `WH_NVM_FLAGS_USAGE_ANY`.

### Port access and NDA requirements
All hardware ports except POSIX require an NDA with the silicon vendor. Customers asking for Aurix/SPC58N port access need to go through the NDA process first. The POSIX port is the right starting point for evaluation and prototyping.

### CMAC with cached keys
The standard `wc_AesCmacGenerate_ex`/`wc_AesCmacVerify_ex` functions only work with client-supplied keys. For HSM-cached keys, use `wh_Client_AesCmacGenerate`/`wh_Client_AesCmacVerify` instead, or use `wh_Client_SetKeyCmac()` with the non-oneshot API and pass `NULL` for the key parameter.
