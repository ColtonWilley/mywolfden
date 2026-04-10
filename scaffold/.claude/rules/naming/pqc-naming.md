---
paths:
  - "**/dilithium*"
  - "**/kyber*"
  - "**/ml_*"
  - "**/ml-*"
  - "**/pkcs11*"
  - "**/wc_pkcs11*"
---

# Post-Quantum Cryptography Naming

wolfSSL uses dual naming for PQC algorithms:

## PKCS#11 / External Interfaces — Standards Names
- `NO_PKCS11_MLDSA` (not `NO_PKCS11_DILITHIUM`)
- `CKK_ML_DSA`, `CKM_ML_DSA`
- `MLDSA` in PKCS#11 function names

## Internal wolfCrypt Code — Legacy Names
- `DILITHIUM`, `dilithium_key`, `wc_dilithium_*`
- `KYBER`, `KyberKey`, `wc_KyberKey_*`

## The Rule
Follow the naming convention of the layer you're in. When adding PKCS#11
support for a PQC algorithm, the PKCS#11 constants and suppression macros
use standards-aligned names while the internal code retains legacy names.

VERIFY: grep for existing PQC entries in `pkcs11.h` to confirm the
convention before naming new constants.
