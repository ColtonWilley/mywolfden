---
paths:
  - "**/wc_pkcs11.c"
  - "**/pkcs11.h"
  - "**/wc_pkcs11.h"
---

# Add PKCS#11 Support for a New Algorithm

## When This Applies
Integrating a new algorithm into wolfSSL's PKCS#11 hardware offload
interface (`wc_pkcs11.c`).

## Required Changes

1. **`wolfssl/wolfcrypt/pkcs11.h`** — Add `CK_*` key type, `CKM_*`
   mechanism constants, and any parameter struct.
   VERIFY: grep for an existing algorithm's `CKK_*` to find insertion point.

2. **`wolfssl/wolfcrypt/wc_pkcs11.h`** — Add entry to the algorithm
   dispatch enum.
   VERIFY: read the existing enum for the pattern.

3. **`wolfcrypt/src/wc_pkcs11.c`** — Add core functions: create key,
   generate, sign, verify, check, store key, free. Add dispatcher
   integration. Expect ~500-600 lines for a full algorithm.
   VERIFY: grep for `Pkcs11CreateEccKey` to find the analog pattern.

4. **`wolfssl/wolfcrypt/<algo>.h`** — Add PKCS#11 metadata fields to the
   key struct: `label`, `labelLen`, `id`, `idLen`.
   VERIFY: read `ecc_key` in `ecc.h` for the reference pattern.

5. **`wolfcrypt/src/<algo>.c`** — Add `wc_CryptoCb_Free()` call in the
   algorithm's free function so PKCS#11 token resources are cleaned up.
   VERIFY: read `wc_ecc_free()` in `ecc.c` for the pattern.

6. **`wolfssl/wolfcrypt/cryptocb.h`** — If the algorithm family needs
   sub-type discrimination in the free path (PQC families with multiple
   algorithms), the `wc_CryptoCb_Free` signature may need a `subType`
   parameter. If changed, update ALL existing call sites (8+ files:
   `aes.c`, `ecc.c`, `sha.c`, `sha256.c`, `sha3.c`, `sha512.c`, etc.).
   VERIFY: grep for `wc_CryptoCb_Free` to find all callers.

7. **`.wolfssl_known_macro_extras`** — Register the suppression macro.

## Scope Boundaries

- This does NOT include CryptoCb test wiring (`test.c` changes) unless
  the PR scope explicitly targets both. See `add-crypto-callback.md`.
- For PQC naming conventions, see `naming/pqc-naming.md`.
