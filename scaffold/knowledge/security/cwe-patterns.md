# CWE Patterns in wolfSSL

> One-line summary: which CWE classes actually bite in wolfSSL, where they live, and what code patterns trigger them.

**When to read**: reviewing or writing protocol parsing, ASN.1 handling, buffer management, or cryptographic operation code in wolfSSL.

---

## CWE-787: Out-of-bounds Write

The dominant threat in TLS handshake and certificate parsing. A length field read from network input controls a `memcpy` size without validation against the destination buffer.

**High-risk pattern**: multiple length fields that must be consistent (outer message length vs inner extension length). If the parser uses one length for allocation and a different length for the copy, memory is corrupted.

**wolfSSL hotspots**: `internal.c`, `tls.c`, `tls13.c` (handshake messages), `asn.c` (ASN.1/DER nested structures), `pkcs7.c` (multi-layer content types).

**Mitigation**: every copy must validate `copy_len <= dest_size` AND `copy_len <= remaining_input`. Track remaining bytes at each nesting level during parsing.

## CWE-125: Out-of-bounds Read (Heartbleed class)

The code trusts a client-specified length to determine how much data to read from a buffer, without verifying actual data available.

**Archetype**: `payload_length = read_uint16(request); memcpy(response, payload, payload_length);` -- missing check that `payload_length <= request_remaining_bytes`.

**wolfSSL hotspots**: TLS record header parsing, certificate message processing, extension data reading. Any place a length from the wire drives a read.

**Watch for**: off-by-one (`<=` vs `<`) in bounds checks on buffer reads.

## CWE-416: Use After Free

Complex object lifetimes during error handling, session resumption, and renegotiation create dangling pointer risks.

**wolfSSL-specific patterns**:
- Error paths that free an object while a caller still holds a reference
- Session cache reuse: `AddSessionToCache` reusing entries for oversized tickets freed wrong pointer (CVE-2022-38153)
- `wolfSSL_clear()` during session resumption accessing freed session data (CVE-2022-38152)
- Renegotiation: old and new state coexist temporarily; old state freed while new state references it

**Mitigation**: NULL pointers after free. Trace all holders of a pointer through every error/cleanup path.

## CWE-476: NULL Pointer Dereference

`XMALLOC` returns NULL on failure; lookup functions return NULL for missing objects. Unchecked, these become crashes (DoS).

**wolfSSL hotspots**: allocation-heavy paths in certificate chain building, extension processing, session object creation. Error paths where a pointer may already be NULL by the time cleanup runs.

## CWE-190: Integer Overflow / Wraparound

Size calculations overflow when attacker-controlled counts multiply with element sizes: `total = count * element_size`. A large `count` (e.g., number of extensions in ClientHello) wraps to a small allocation, followed by a large write.

**wolfSSL-specific example**: CVE-2022-39173 -- `RefineSuites` did not reset state between handshakes; duplicate cipher suites across two ClientHellos exceeded the 150-suite stack buffer.

**Check pattern** (unsigned): `if (a != 0 && b > UINT_MAX / a) { /* overflow */ }`. Also watch for `size_t` to `int` truncation -- a 5GB value silently becomes small and positive.

**Addition variant**: `if (a + b < a) { /* overflow */ }` -- but signed overflow is undefined behavior in C; the compiler can optimize this check away. Use unsigned types for sizes.

## CWE-20: Improper Input Validation (umbrella)

Every byte from the network is attacker-controlled. Common gaps:
- Enum values not range-checked (cipher suite IDs, extension types, version numbers)
- Certificate chain depth unlimited
- DH parameters below minimum size (enables Logjam)
- RSA key sizes below policy minimum

---

## CWE-to-Code-Area Map

| Code Area | Key Files | Primary CWEs |
|-----------|-----------|-------------|
| TLS handshake | `internal.c`, `tls.c`, `tls13.c` | 787, 125, 20 |
| X.509 / ASN.1 | `asn.c`, `ssl_certman.c` | 121, 122, 125, 190 |
| Crypto ops | `aes.c`, `rsa.c`, `ecc.c` | 1240 (side-channel) |
| RNG / DRBG | `random.c`, `sp_drbg.c` | 331 (entropy) |
| PKCS#7 / CMS | `pkcs7.c` | 122, 787 |
| Session mgmt | `internal.c` | 416 |

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| Crash on malformed ClientHello | Extension length exceeds message | `internal.c` handshake parsing |
| Heap over-read on TLS record | Untrusted length in record header | CVE-2022-42905, record parsing |
| Stack overflow on duplicate suites | State not reset between handshakes | CVE-2022-39173, `RefineSuites` |
| Use-after-free on session resume | Cache entry pointer reused after free | CVE-2022-38153, `AddSessionToCache` |
| NULL deref during cleanup | Allocation failure not checked on error path | Various allocation-heavy paths |

## What This File Does NOT Cover

- Side-channel CWEs (CWE-1240) -- see `attack-principles.md` for oracle/timing patterns
- Cryptographic algorithm CWEs (CWE-327, CWE-326) -- algorithm selection policy, not code patterns
- Application-layer vulnerabilities above the TLS library boundary
