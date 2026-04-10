# Post-Quantum Cryptography

> One-line summary: configure flags, API patterns, TLS hybrid key exchange setup, and algorithm/OID tables for ML-KEM and ML-DSA.

**When to read**: Enabling PQC in a wolfSSL build, setting up TLS 1.3 hybrid key exchange, or debugging PQC handshake failures.

---

## Configure Flags

### ML-KEM (Key Encapsulation, FIPS 203)

```bash
--enable-mlkem              # Enabled by default; --enable-kyber is alias
--enable-mlkem=512,768      # Specific parameter sets only
--enable-mlkem=all          # Both ML-KEM and legacy Kyber identifiers
--enable-mlkem=small        # Smaller code (WOLFSSL_MLKEM_SMALL)
--enable-mlkem=noasm        # Disable assembly, C reference only
```

### ML-DSA (Digital Signatures, FIPS 204)

```bash
--enable-mldsa              # Disabled by default; --enable-dilithium is alias
--enable-mldsa=all          # Enable keygen, sign, and verify
--enable-mldsa=verify-only  # Verify only (smallest footprint)
--enable-mldsa=small        # Smaller code (WOLFSSL_DILITHIUM_SMALL)
--enable-mldsa=44,65        # Specific parameter sets only
```

### Key Defines (for `user_settings.h`)

| Define | Purpose |
|--------|---------|
| `WOLFSSL_HAVE_MLKEM` | Enable ML-KEM |
| `WOLFSSL_WC_MLKEM` | Use native (not liboqs) implementation |
| `HAVE_DILITHIUM` | Enable ML-DSA |
| `WOLFSSL_WC_DILITHIUM` | Use native implementation |
| `WOLFSSL_PQC_HYBRIDS` | Enable hybrid TLS key exchange |
| `WOLFSSL_NO_ML_KEM_512/768/1024` | Disable specific ML-KEM sizes |
| `WOLFSSL_NO_ML_DSA_44/65/87` | Disable specific ML-DSA sizes |
| `WOLFSSL_MLKEM_NO_MAKE_KEY` / `NO_ENCAPSULATE` / `NO_DECAPSULATE` | Exclude unused operations |

## ML-KEM API

```c
MlKemKey key;
wc_MlKemKey_Init(&key, WC_ML_KEM_768, NULL, INVALID_DEVID);
wc_MlKemKey_MakeKey(&key, &rng);

/* Encapsulate (sender) → ciphertext + shared secret */
byte ct[WC_ML_KEM_768_CIPHER_TEXT_SIZE];
byte ss[WC_ML_KEM_SS_SZ];  /* 32 bytes */
wc_MlKemKey_Encapsulate(&key, ct, ss, &rng);

/* Decapsulate (receiver) → recovers shared secret */
wc_MlKemKey_Decapsulate(&key, ss_dec, ct, WC_ML_KEM_768_CIPHER_TEXT_SIZE);

wc_MlKemKey_EncodePublicKey(&key, pubBuf, &pubLen);  /* Export */
wc_MlKemKey_DecodePublicKey(&key, pubData, pubLen);   /* Import */
wc_MlKemKey_Free(&key);
```

## ML-DSA API

```c
dilithium_key key;
wc_dilithium_init(&key);
wc_dilithium_set_level(&key, 3);  /* ML-DSA-65 = level 3 */
wc_dilithium_make_key(&key, &rng);

byte sig[DILITHIUM_LEVEL3_SIG_SIZE];  /* 3,309 bytes */
word32 sigLen = sizeof(sig);
wc_dilithium_sign_msg(msg, msgLen, sig, &sigLen, &key, &rng);

int verified = 0;
wc_dilithium_verify_msg(sig, sigLen, msg, msgLen, &verified, &key);

wc_dilithium_export_public(&key, pubBuf, &pubLen);
wc_Dilithium_PublicKeyToDer(&key, derBuf, derBufSz, 1);
```

## TLS 1.3 Hybrid Key Exchange

Hybrid combines ECDH + ML-KEM so security holds even if one is broken. Requires TLS 1.3. Enabled by default when ML-KEM is on (`WOLFSSL_PQC_HYBRIDS`). For non-hybrid: `--enable-tls-mlkem-standalone`.

| Constant | ID | Combination | Notes |
|----------|-----|------------|-------|
| `WOLFSSL_SECP256R1MLKEM768` | 4587 | P-256 + ML-KEM-768 | Standard |
| `WOLFSSL_X25519MLKEM768` | 4588 | X25519 + ML-KEM-768 | Standard |
| `WOLFSSL_SECP384R1MLKEM1024` | 4589 | P-384 + ML-KEM-1024 | Standard |
| `WOLFSSL_SECP256R1MLKEM512` | 12107 | P-256 + ML-KEM-512 | `--enable-extra-pqc-hybrids --enable-experimental` |
| `WOLFSSL_X25519MLKEM512` | 12214 | X25519 + ML-KEM-512 | experimental |
| `WOLFSSL_X448MLKEM768` | 12215 | X448 + ML-KEM-768 | experimental |

### Client Setup

```c
wolfSSL_UseKeyShare(ssl, WOLFSSL_SECP256R1MLKEM768);
/* Or set group list with classical fallback: */
int groups[] = { WOLFSSL_SECP256R1MLKEM768, WOLFSSL_ECC_SECP256R1 };
wolfSSL_set_groups(ssl, groups, 2);
```

Always include a classical fallback group for interop with non-PQC servers.

## ML-DSA Sizes and Level Mapping

| Level | FIPS Name | Pub Key | Signature | vs ECDSA P-256 | Security |
|-------|-----------|---------|-----------|----------------|----------|
| 2 | ML-DSA-44 | 1,312 B | 2,420 B | ~20x / ~37x | ~128-bit |
| 3 | ML-DSA-65 | 1,952 B | 3,309 B | ~30x / ~51x | ~192-bit |
| 5 | ML-DSA-87 | 2,592 B | 4,627 B | ~40x / ~72x | ~256-bit |

Set via `wc_dilithium_set_level(&key, 3)` for ML-DSA-65. TLS 1.3 handshake with ML-DSA-65 certs can exceed 10 KB for the Certificate message alone. For constrained networks, use ML-DSA-44 or `WOLFSSL_DUAL_ALG_CERTS`.

## Embedded Size Reduction

```bash
--enable-mlkem=small,768,enc,dec --enable-mldsa=verify-only,44,small
```

## FIPS Status

ML-KEM/ML-DSA require FIPS v6+ (`--enable-fips=v6`). Earlier FIPS bundles lack SHAKE-128/256.

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| Handshake fails with PQC-enabled peer | Both sides must support same hybrid group ID | Check `wolfSSL_set_groups()` includes matching IDs |
| PQC key exchange attempted over TLS 1.2 | PQC key exchange is TLS 1.3 only | Ensure `--enable-tls13` |
| Certificate message exceeds MTU | ML-DSA cert chain too large for DTLS/constrained link | Use ML-DSA-44 or smaller chain |
| FIPS build rejects ML-KEM | FIPS version < v6 lacks SHAKE support | Upgrade to `--enable-fips=v6` |
| `--enable-mlkem=original` gives unknown groups | Legacy Kyber group IDs differ from ML-KEM | Use `--enable-mlkem=all` for both |

## What This File Does NOT Cover

- PQC algorithm internals (lattice math, NTT, rejection sampling)
- NIST competition history
- Assembly optimization details (see platform-specific knowledge)
- Detailed API usage examples (see wolfSSL documentation)
