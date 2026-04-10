# Certificate Chain Validation

> One-line summary: error-code-to-root-cause mappings and decision tree for the most common wolfSSL support failures.

**When to read**: Debugging TLS certificate verification failures, loading certs from buffers, or triaging -313/-188/-150 errors.

---

## Error Code → Root Cause

| Code | Constant | Most Common Cause |
|------|----------|-------------------|
| -188 | `ASN_SIG_CONFIRM_E` | Wrong CA, corrupt cert, or algorithm mismatch |
| -313 | `ASN_NO_SIGNER_E` | Missing intermediate or root not loaded |
| -150 | `ASN_NO_PEM_HEADER` | DER file loaded as PEM, or corrupt PEM (BOM, encoding) |
| -212 | `ASN_AFTER_DATE_E` | Certificate expired (or system clock not set — common on embedded) |
| -213 | `ASN_BEFORE_DATE_E` | Certificate not yet valid (clock issue) |
| -243 | `ASN_PATHLEN_E` | Too many intermediates for path length constraint |
| -245 | `ASN_KEY_SIZE_E` | Key below minimum (FIPS rejects <2048-bit RSA) |
| -329 | `VERIFY_CERT_ERROR` | Wraps underlying ASN error at TLS layer — find inner error |

## Decision Tree

### -313 (No Signer) — Missing Intermediates
- `wolfSSL_CTX_use_certificate_file` loads leaf only — use `_chain_file` for leaf + intermediates
- Client needs full chain: either server sends intermediates, or client loads them via `load_verify_locations`
- Chain file must be ordered: **leaf first**, then intermediates, root optional

### -188 (Sig Confirm) — Self-Signed or Chain Order
- Self-signed certs must be explicitly loaded into trust store via `load_verify_locations`
- Chain files in wrong order (root first) cause wolfSSL to treat root as leaf
- Verify: subject of cert N must be issuer of cert N-1

### -150 (No PEM Header) — Format Mismatch
- File starting with `0x30` (ASN.1 SEQUENCE) = DER; starting with `-----` = PEM
- `SSL_FILETYPE_PEM` vs `SSL_FILETYPE_ASN1` must match the actual format
- Check for BOM (byte order mark) at start of PEM file

### -245 (Key Size) — FIPS Policy Enforcement
- `WOLFSSL_MIN_RSA_BITS` / `WOLFSSL_MIN_ECC_BITS` control minimums
- FIPS enforces 2048-bit RSA minimum — this is intentional, not a bug
- Customer needs to upgrade certificates

### -212/-213 (Date) — Clock Not Set
- Embedded devices often boot at epoch (1970-01-01)
- Sync time via NTP before `wolfSSL_connect()`
- Dev workaround: `NO_ASN_TIME` skips date checks (security-degraded)

## Investigation Sequence

1. Get the **inner error code** (not just -329)
2. Check cert format and loading method (PEM vs DER, file vs buffer, chain vs single)
3. Check trust store contents (`load_verify_locations` / `load_verify_buffer` calls)
4. Examine cert: `openssl x509 -text` for fields
5. Check build config: FIPS mode, min key sizes, CRL/OCSP enabled
6. Trace code: `ProcessPeerCerts()` in `internal.c` is the validation entry point

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| -313 with correct CA loaded | Intermediate missing from chain | Use `_chain_file` on server, verify order |
| -188 with self-signed cert | Cert not in trust store | Load via `load_verify_locations` |
| -150 on valid-looking cert | DER loaded as PEM (or BOM in PEM) | Check first bytes: `0x30` = DER |
| -212 on valid cert | System clock at epoch | Sync NTP before TLS |
| -245 on 1024-bit RSA | FIPS min key size policy | Upgrade cert to 2048-bit+ |

## What This File Does NOT Cover

- CRL/OCSP checking details (see wolfSSL manual)
- Custom verification callbacks
- Certificate generation or signing
