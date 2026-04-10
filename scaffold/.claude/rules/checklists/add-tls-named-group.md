---
paths:
  - "**/tls.c"
  - "**/tls13.c"
  - "**/internal.h"
  - "**/ssl.h"
  - "**/internal.c"
---

# Add or Modify TLS Named Groups / Signature Schemes

## When This Applies
Adding a new TLS named group, signature scheme, or restructuring which
groups are populated by default.

## Required Changes

1. **`wolfssl/ssl.h`** — Named group constants (public API).
   VERIFY: grep for existing group constant (e.g., `WOLFSSL_ECC_SECP256R1`).

2. **`wolfssl/internal.h`** — Wire format constants, enum values for
   signature algorithms. For signature scheme families, wolfSSL typically
   uses a single family enum (e.g., `ecc_brainpool_sa_algo`) with
   hash-based dispatch, not per-curve values.
   VERIFY: read the existing sig algo enum to confirm the pattern.

3. **`src/tls.c`** — Key share generation/processing, supported curves
   extension handling.
   VERIFY: grep for an existing group in `tls.c` to find insertion points.

4. **`src/tls13.c`** — TLS 1.3 signature scheme encoding/decoding,
   HelloRetryRequest handling.

5. **`src/internal.c`** — Suite tables, `InitSuitesHashSigAlgo` for
   sig algo registration. Note: `InitSuitesHashSigAlgo` acts as a
   gatekeeper — new sig algo families may need a version-flag parameter
   for conditional advertisement.
   VERIFY: read `InitSuitesHashSigAlgo` for the parameter pattern.

6. **`src/ssl.c`** — API plumbing for the new group/scheme.

7. **`examples/client/client.c`** — New `--flag`, parameter threading
   through `SetKeyShare`/benchmark functions, usage message update. This
   is often the largest change (~400+ lines). Read an existing flag
   (e.g., `--x25519`) as template.

8. **`examples/server/server.c`** — `group_id_to_text` table entry.

9. **`examples/benchmark/tls_bench.c`** — `group_info` table entry.

10. **`src/sniffer.c`** — Group ID recognition for key log parsing.

11. **`tests/api.c`** — Negotiation tests.

12. **`configure.ac`** — New `--enable` flag and `#define` gates.

## Scope Boundaries

- TLS 1.2 and TLS 1.3 handshake paths are independent code. Changes in
  `DoHandShakeMsg` (internal.c) do NOT imply changes in
  `DoTls13HandShakeMsg` (tls13.c) or vice versa.
- Existing TLS 1.2 support does NOT mean any TLS 1.3 infrastructure
  exists for the same feature.
