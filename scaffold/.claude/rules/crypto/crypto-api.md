---
paths:
  - "wolfcrypt/src/**"
---

# wolfCrypt API Common Patterns

## General API Patterns
## General API Patterns
All wolfCrypt objects follow init/use/free pattern:
```c
ret = wc_InitXxx(&obj);            // Can fail — MUST check return
if (ret == 0)
    ret = wc_XxxOperation(&obj, ...); // Use only if init succeeded
wc_FreeXxx(&obj);                  // Free (safe even after failed init in most cases)
```
**Common mistake**: Forgetting `wc_InitXxx()` → crash or undefined behavior.
**Common mistake**: Forgetting `wc_FreeXxx()` → memory leak, especially on embedded.
**Common mistake**: Not checking `wc_InitXxx()` return value — using an
uninitialized object leads to undefined behavior or security issues.
## RSA Common Issues

### Key Generation
- `wc_MakeRsaKey(&key, 2048, WC_RSA_EXPONENT, &rng)` — rng must be initialized
- Requires `--enable-keygen` or `#define WOLFSSL_KEY_GEN`
- FIPS: minimum 2048-bit keys (1024-bit no longer allowed for signing)

### Encrypt/Decrypt
- `wc_RsaPublicEncrypt()` — uses PKCS#1 v1.5 padding by default
- `wc_RsaPublicEncrypt_ex()` — allows OAEP padding (recommended)
- Max plaintext size = key_size - padding_overhead (11 bytes for PKCS#1 v1.5, 42 bytes for OAEP SHA-256)
- **Common error**: -173 (BUFFER_E) — output buffer too small. Size should be key_size bytes.

### Sign/Verify
- `wc_RsaSSL_Sign()` — PKCS#1 v1.5 signature
- `wc_RsaPSS_Sign()` — PSS signature (requires `--enable-pss`)
- Input to sign should be hash digest, not raw data
- **Common mistake**: Passing full message instead of hash to sign function

## ECC Common Issues

### Key Generation
- `wc_ecc_make_key(&rng, 32, &key)` — 32 bytes = P-256 (256 bits / 8)
- Size parameter is bytes, not bits
- **Common mistake**: Passing 256 instead of 32 → failure or wrong curve

### Sign/Verify (ECDSA)
- `wc_ecc_sign_hash()` — sign a hash digest
- `wc_ecc_verify_hash()` — verify, returns `stat` (1=valid, 0=invalid)
- **Common mistake**: Not checking `stat` return parameter — function returns 0 (success) even if signature is invalid

### Key Import/Export
- `wc_EccPublicKeyDecode()` / `wc_EccPrivateKeyDecode()` — from DER
- `wc_ecc_import_x963()` — import uncompressed point (04 || X || Y)
- `wc_ecc_export_x963()` — export as uncompressed point
- **Common mistake**: Wrong key format (raw vs DER vs X9.63)

## AES Common Issues

### AES-GCM
- `wc_AesGcmEncrypt()` — encrypts AND generates auth tag
- `wc_AesGcmDecrypt()` — decrypts AND verifies auth tag
- **Critical**: IV must NEVER be reused with same key (breaks GCM security)
- Auth tag size: 16 bytes default, configurable (min 12 for FIPS)
- AAD (Additional Authenticated Data): optional but must match for decrypt

### AES-CBC
- `wc_AesCbcEncrypt()` / `wc_AesCbcDecrypt()`
- Input must be multiple of 16 bytes (AES block size)
- **Common error**: Not padding input → `-170 (BAD_FUNC_ARG)` or truncated output
- IV must be unique per encryption (not necessarily secret, but don't reuse)

## Hashing

### SHA-256 (most common)
```c
wc_Sha256 sha;
wc_InitSha256(&sha);
wc_Sha256Update(&sha, data, len);  // Can call multiple times
wc_Sha256Final(&sha, hash);        // Output: 32 bytes
wc_Sha256Free(&sha);
```
- One-shot: `wc_Sha256Hash(data, len, hash)` — init+update+final in one call
- **Common mistake**: Not calling `Final` before reading hash
- **Common mistake**: Output buffer < 32 bytes → buffer overflow

## Random Number Generation
- `wc_InitRng(&rng)` — seeds DRBG from OS/hardware entropy
- `wc_RNG_GenerateBlock(&rng, buf, size)` — fill buffer with random bytes
- `wc_FreeRng(&rng)` — zeroizes state
- **Common error on embedded**: `-199 (RNG_FAILURE_E)` — no entropy source configured
- FIPS: must use NIST-approved DRBG, reseeding required after 2^48 requests

## Crypto Callbacks (WOLF_CRYPTO_CB)
wolfSSL supports crypto callbacks for hardware acceleration and custom crypto implementations:
- Enable with `--enable-cryptocb` or `#define WOLF_CRYPTO_CB`
- Register callbacks via `wc_CryptoCb_RegisterDevice()` with a device ID
- Assign device ID to a context: `wolfSSL_CTX_SetDevId(ctx, devId)`
- Callback receives operation type and dispatches to hardware-specific code
- Supports: RSA, ECC, AES, Hashing, RNG, and HMAC operations
- Use case: offloading crypto to HSM, TPM, secure element, or hardware accelerator
- Working examples in `wolfssl-examples` repository (crypto callback directory)
- For SE050, ATECC508A, and similar: crypto callbacks are the recommended integration path
