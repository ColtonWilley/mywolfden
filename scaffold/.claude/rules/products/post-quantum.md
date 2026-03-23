---
paths:
  - "**/kyber*"
  - "**/dilithium*"
  - "**/falcon*"
  - "**/sphincs*"
  - "**/ml-kem*"
  - "**/ml-dsa*"
---

# Post-Quantum Cryptography — API & Integration Patterns

## Overview

wolfSSL implements NIST post-quantum algorithms: **ML-KEM** (FIPS 203, formerly Kyber) for key encapsulation and **ML-DSA** (FIPS 204, formerly Dilithium) for digital signatures. ML-KEM is enabled by default. Both have wolfCrypt-native implementations with assembly optimizations (see `post-quantum-asm.md` for platform-specific performance).

## Configure Flags

**ML-KEM (key encapsulation):**
```bash
./configure --enable-mlkem            # Enabled by default; --enable-kyber is an alias
./configure --enable-mlkem=512,768    # Enable only specific parameter sets
./configure --enable-mlkem=all        # Both ML-KEM and legacy Kyber identifiers
./configure --enable-mlkem=small      # Smaller code size (adds -DWOLFSSL_MLKEM_SMALL)
./configure --enable-mlkem=noasm      # Disable assembly, use C reference only
```

**ML-DSA (digital signatures):**
```bash
./configure --enable-mldsa            # Disabled by default; --enable-dilithium is an alias
./configure --enable-mldsa=all        # Enable keygen, sign, and verify
./configure --enable-mldsa=verify-only  # Verify only (smallest footprint)
./configure --enable-mldsa=small      # Smaller code size at cost of speed
./configure --enable-mldsa=44,65      # Enable only specific parameter sets
```

**TLS 1.3 hybrid key exchange:**
```bash
./configure --enable-mlkem --enable-pqc-hybrids          # Hybrid (default when ML-KEM on)
./configure --enable-tls-mlkem-standalone                 # Non-hybrid ML-KEM in TLS
./configure --enable-extra-pqc-hybrids --enable-experimental  # Additional hybrid combos
```

**Key defines** (for `user_settings.h` builds): `WOLFSSL_HAVE_MLKEM`, `WOLFSSL_WC_MLKEM` (native impl), `HAVE_DILITHIUM`, `WOLFSSL_WC_DILITHIUM`, `WOLFSSL_PQC_HYBRIDS`. Disabling specific sizes: `WOLFSSL_NO_ML_KEM_512`, `WOLFSSL_NO_ML_KEM_768`, `WOLFSSL_NO_ML_KEM_1024`, `WOLFSSL_NO_ML_DSA_44`, `WOLFSSL_NO_ML_DSA_65`, `WOLFSSL_NO_ML_DSA_87`.

## ML-KEM API Usage

The ML-KEM API uses `MlKemKey` with type constants `WC_ML_KEM_512`, `WC_ML_KEM_768`, or `WC_ML_KEM_1024`:

```c
#include <wolfssl/wolfcrypt/mlkem.h>

MlKemKey key;
wc_MlKemKey_Init(&key, WC_ML_KEM_768, NULL, INVALID_DEVID);
wc_MlKemKey_MakeKey(&key, &rng);

/* Encapsulation (sender) — produces ciphertext + shared secret */
byte ct[WC_ML_KEM_768_CIPHER_TEXT_SIZE];
byte ss[WC_ML_KEM_SS_SZ];   /* 32 bytes */
wc_MlKemKey_Encapsulate(&key, ct, ss, &rng);

/* Decapsulation (receiver) — recovers shared secret from ciphertext */
byte ss_dec[WC_ML_KEM_SS_SZ];
wc_MlKemKey_Decapsulate(&key, ss_dec, ct, WC_ML_KEM_768_CIPHER_TEXT_SIZE);

/* Import/export */
wc_MlKemKey_EncodePublicKey(&key, pubBuf, &pubLen);
wc_MlKemKey_DecodePublicKey(&key, pubData, pubLen);
wc_MlKemKey_Free(&key);
```

## ML-DSA API Usage

The ML-DSA API uses `dilithium_key` with levels 2, 3, or 5 (mapping to ML-DSA-44, ML-DSA-65, ML-DSA-87):

```c
#include <wolfssl/wolfcrypt/dilithium.h>

dilithium_key key;
wc_dilithium_init(&key);
wc_dilithium_set_level(&key, 3);  /* ML-DSA-65 = level 3 */
wc_dilithium_make_key(&key, &rng);

/* Sign */
byte sig[DILITHIUM_LEVEL3_SIG_SIZE];  /* 3309 bytes */
word32 sigLen = sizeof(sig);
wc_dilithium_sign_msg(msg, msgLen, sig, &sigLen, &key, &rng);

/* Verify */
int verified = 0;
wc_dilithium_verify_msg(sig, sigLen, msg, msgLen, &verified, &key);

/* Import/export and DER encoding */
wc_dilithium_export_public(&key, pubBuf, &pubLen);
wc_dilithium_import_public(pubData, pubLen, &key);
wc_Dilithium_PublicKeyToDer(&key, derBuf, derBufSz, 1);
```

## TLS 1.3 Hybrid Key Exchange

Hybrid key exchange combines ECDH with ML-KEM so security holds even if one is broken. Supported groups per draft-ietf-tls-ecdhe-mlkem:

| Group Constant                | ID   | Combination               |
|-------------------------------|------|---------------------------|
| `WOLFSSL_SECP256R1MLKEM768`   | 4587 | P-256 + ML-KEM-768        |
| `WOLFSSL_X25519MLKEM768`      | 4588 | X25519 + ML-KEM-768       |
| `WOLFSSL_SECP384R1MLKEM1024`  | 4589 | P-384 + ML-KEM-1024       |

With `--enable-extra-pqc-hybrids --enable-experimental`: `WOLFSSL_SECP256R1MLKEM512` (12107), `WOLFSSL_X25519MLKEM512` (12214), `WOLFSSL_X448MLKEM768` (12215).

**Client-side setup:**
```c
wolfSSL_UseKeyShare(ssl, WOLFSSL_SECP256R1MLKEM768);
/* Or set supported groups list: */
int groups[] = { WOLFSSL_SECP256R1MLKEM768, WOLFSSL_ECC_SECP256R1 };
wolfSSL_set_groups(ssl, groups, 2);
```

The fallback group (`WOLFSSL_ECC_SECP256R1`) ensures interoperability with servers that do not support PQC.

## Certificate Size Implications

ML-DSA keys and signatures are much larger than classical counterparts, affecting certificate chain sizes and potentially causing MTU/fragmentation issues:

| Algorithm   | Public Key | Signature | vs. ECDSA P-256          |
|-------------|------------|-----------|--------------------------|
| ML-DSA-44   | 1,312 B    | 2,420 B   | ~20x key, ~37x sig       |
| ML-DSA-65   | 1,952 B    | 3,309 B   | ~30x key, ~51x sig       |
| ML-DSA-87   | 2,592 B    | 4,627 B   | ~40x key, ~72x sig       |

A TLS 1.3 handshake with ML-DSA-65 certs can exceed 10 KB for the Certificate message alone. For constrained networks, consider ML-DSA-44 or hybrid certificates with `WOLFSSL_DUAL_ALG_CERTS`.

## Performance Considerations

ML-KEM operations are fast (sub-millisecond on modern hardware). ML-DSA signing is more expensive due to rejection sampling. Assembly gives 3-5x speedup on x86_64 AVX2, 2-3x on ARM64 NEON (see `post-quantum-asm.md`).

- **`WOLFSSL_MLKEM_SMALL` / `WOLFSSL_DILITHIUM_SMALL`**: Reduces code size at cost of speed. Good for flash-constrained MCUs.
- **Caching** (`--enable-mlkem=cache-a`): Caches matrix A for repeated operations, trading memory for speed.
- **Operation subsetting**: `WOLFSSL_MLKEM_NO_MAKE_KEY` / `NO_ENCAPSULATE` / `NO_DECAPSULATE` exclude unused operations for constrained builds.

## FIPS Certification Status

wolfSSL FIPS 140-3 validation for ML-KEM/ML-DSA requires FIPS v6+ (`--enable-fips=v6`). Earlier FIPS bundles lack SHAKE-128/256 which ML-KEM requires. Check wolfSSL's FIPS status page for current certification state.

## Common Support Scenarios

**"How do I enable post-quantum in my TLS 1.3 build?"**
`./configure --enable-mlkem --enable-tls13`. Hybrid groups are on by default. Client side: call `wolfSSL_UseKeyShare(ssl, WOLFSSL_SECP256R1MLKEM768)`. No server code changes needed if built with the same flags.

**"My handshake fails with a PQC-enabled peer"**
Verify both sides support the same hybrid group IDs. Use `wolfSSL_set_groups()` with classical fallbacks. PQC key exchange is TLS 1.3 only.

**"Can I use Kyber (original) instead of ML-KEM?"**
Yes: `./configure --enable-mlkem=original` or define `WOLFSSL_MLKEM_KYBER`. Use `--enable-mlkem=all` for both.

**"How do I reduce PQC code size for embedded?"**
`--enable-mlkem=small,768,enc,dec --enable-mldsa=verify-only,44,small` gives only ML-KEM-768 encap/decap and ML-DSA-44 verify with small code paths.
