# Attack Principles for wolfSSL

> One-line summary: the core attack principles that constrain how wolfSSL code must be written, with specific named attacks and their wolfSSL defenses.

**When to read**: writing or reviewing cryptographic operations, protocol parsing, error handling, or negotiation logic in wolfSSL.

---

## The Oracle Principle

Any observable difference in behavior that correlates with secret data creates an exploitable oracle. Even a 1-bit signal per query can recover a full key given enough repetitions.

**Observable channels**: timing, error messages/types, TCP behavior (RST vs FIN), cache state, power consumption.

**The test**: "Does this code behave differently -- in any way -- depending on the value of a secret?"

**wolfSSL code constraint**: branches on secret-dependent values must use constant-time selection. Both paths execute; result selected via `ct_select`. WRONG: `if (padding_valid) { pms = extract(); } else { pms = random(); }` -- timing differs even with same error code. RIGHT: compute both, then `pms = ct_select(valid, real_pms, random_pms);`.

### Named Oracle Attacks on wolfSSL

| Attack | Channel | wolfSSL Defense |
|--------|---------|-----------------|
| Bleichenbacher / ROBOT / Marvin | RSA PKCS#1 v1.5 padding validity via timing | Constant-time padding check + `ct_select` on premaster |
| Lucky13 | CBC MAC-then-encrypt: padding length leaks via timing | Constant-time padding verification, additional hash iterations to equalize timing |
| POODLE | SSLv3 padding not MAC'd; padding oracle via error | Disable SSLv3 (off by default) |
| Raccoon | DH shared secret leading zeros stripped, variable KDF input length | Pad DH secret to full prime length before KDF |
| Vaudenay padding oracle | CBC decrypt returns different errors for bad padding vs bad MAC | Unified error path; verify MAC regardless of padding validity |

## Trust Boundaries

**Primary boundary**: the network -- every byte in every received TLS message is attacker-controlled. **Secondary**: protocol layer transitions (record -> handshake -> extension -> data), format transitions (DER -> parsed cert -> validated chain), API boundary (caller -> library).

**The test**: "Does this code use any attacker-controlled value to determine memory access size, loop count, array index, or allocation size -- and is that value validated first?"

**Key wolfSSL patterns**:
- Nested length consistency: outer SEQUENCE says 500 bytes, inner field says 600 -- parser must track remaining bytes at each nesting level
- ASN.1 vs C strings: ASN.1 is length-delimited, can contain embedded NULLs. `"example.com\x00.evil.com"` truncates to `"example.com"` via `strlen`. Use length-aware comparison
- Integer signedness: unsigned protocol value in signed C int; large positive becomes negative, passes `> 0` check

## The Downgrade Principle

If the system supports multiple security levels and the attacker can influence selection, they force the weakest option.

| Attack | Mechanism | wolfSSL Defense |
|--------|-----------|-----------------|
| FREAK | MITM modifies ClientHello to request export RSA (512-bit) | Export suites removed/disabled by default |
| Logjam | MITM forces export DHE (512-bit DH groups) | Minimum DH parameter size enforcement |
| DROWN | SSLv2 oracle used cross-protocol to attack shared RSA key | SSLv2 not supported |
| Fallback downgrade | Attacker disrupts connections until client retries with lower version | TLS_FALLBACK_SCSV support |
| TLS 1.3 -> 1.2 | MITM strips supported_versions extension | Anti-downgrade sentinel in ServerHello.random (last 8 bytes); client MUST verify |

## PKCS#1 v1.5 Signature Forgery (Bleichenbacher 2006)

When `e = 3`, an attacker constructs a cube root that looks like a valid PKCS#1 v1.5 block with the correct hash, but with trailing garbage after the ASN.1 DigestInfo.

**Vulnerable verification**: parses the decrypted block to extract the hash, ignoring bytes after the ASN.1 structure. **Correct verification**: constructs the expected block and compares byte-for-byte; any trailing data causes failure.

**wolfSSL defense**: construction-based verification with strict DER (not BER) parsing. Still relevant -- CVE-2026-22866 shows this class persists in other systems.

## Composition Failures

Individual secure operations become insecure when combined.

| Attack | Composition | wolfSSL Defense |
|--------|-------------|-----------------|
| CRIME | compress-then-encrypt leaks plaintext via ciphertext length | TLS compression disabled by default |
| BREACH | HTTP compression + encryption (application-layer, NOT a wolfSSL issue) | N/A -- above TLS boundary |
| MAC-then-encrypt | Receiver must decrypt before MAC check, creating padding oracle | TLS 1.3 uses AEAD (encrypt-then-MAC equivalent); pre-1.3: constant-time padding + MAC |

## State Machine Attacks

Any state transition not explicitly denied is implicitly allowed. wolfSSL-relevant patterns: out-of-order messages (Finished before key exchange -> uninitialized key), skipped messages (ChangeCipherSpec without key exchange -> null encryption), TLS 1.2/1.3 version confusion (wrong code path for handshake), duplicate messages (resource exhaustion).

tlspuffin (Dolev-Yao model-guided fuzzer) found 4 wolfSSL CVEs (2022-38152, -38153, -39173, -42905) via protocol-level mutations that byte-level fuzzers cannot reach.

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| RSA decryption timing varies with padding | Branch on padding validity | RSA PKCS#1 v1.5 decrypt path |
| CBC decrypt timing varies with padding length | Early-exit on bad padding before MAC | CBC decrypt + MAC verify path |
| DH handshake timing varies | Leading-zero stripping changes KDF input size | DH premaster secret handling |
| Forged signature accepted | Parsing-based verification ignores trailing bytes | RSA PKCS#1 v1.5 signature verify |
| Client downgrades to TLS 1.2 | Anti-downgrade sentinel not checked | `tls13.c` ServerHello processing |

## What This File Does NOT Cover

- Physical/fault attacks (power analysis, EM, voltage glitching) -- relevant for embedded but separate concern
- Specific CVE triage methodology and version-comparative analysis
- Build configuration and `#ifdef` guard details for feature-gating
- DTLS-specific attack patterns (cookie verification, amplification)
