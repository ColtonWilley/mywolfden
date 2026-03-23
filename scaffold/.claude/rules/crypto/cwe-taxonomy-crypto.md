---
paths:
  - "**/random.c"
  - "**/rsa.c"
  - "**/ecc.c"
---

# CWE Taxonomy for C Cryptographic Libraries

## Why CWE Matters for Vulnerability Triage

The Common Weakness Enumeration (CWE) is a community-developed taxonomy of software and hardware weaknesses. When triaging a vulnerability report, correctly identifying the CWE category does two things: it connects the specific report to a body of knowledge about that weakness class (known exploitation techniques, typical severity, common fix patterns), and it helps assess whether the report describes a real pattern or a false positive by comparing against the typical characteristics of that CWE.

CWE identifiers are also what gets assigned to CVEs in the National Vulnerability Database. Understanding the taxonomy helps contextualize NVD records during investigation.

## Memory Safety CWEs — The Dominant Threat for C Crypto Code

Memory safety vulnerabilities are the single largest category of security issues in C code. For a crypto/TLS library, they arise primarily in protocol parsing (TLS handshake messages, X.509 certificates, ASN.1 structures) and in buffer management for cryptographic operations.

### CWE-787: Out-of-bounds Write

**What it is**: Writing data past the end (or before the beginning) of an allocated buffer. This is the #5 most dangerous software weakness overall (2025 CWE Top 25) and is extremely common in protocol parsing code.

**How it manifests in crypto/TLS code**: A TLS handshake message contains a length field. The parser allocates a buffer based on one length, then copies data using a different length (or the same length without validating it against the buffer size). If the copy length exceeds the buffer, memory is corrupted.

**What to look for when investigating a report**:
- Is there a length field read from network input?
- Is that length validated against the destination buffer size before the copy?
- Are there multiple length fields that must be consistent (e.g., outer message length vs. inner extension length)?
- Does the code handle the case where the stated length exceeds the remaining message data?

**Related**: CWE-121 (Stack-based Buffer Overflow) and CWE-122 (Heap-based Buffer Overflow) are more specific variants. CWE-121 is particularly dangerous because stack overflows can overwrite return addresses, enabling code execution. CWE-122 can corrupt heap metadata, also enabling code execution but typically requiring more sophisticated exploitation.

### CWE-125: Out-of-bounds Read

**What it is**: Reading data from beyond the bounds of an allocated buffer. This is the Heartbleed class — the attacker doesn't corrupt memory but reads memory they shouldn't see.

**How it manifests in crypto/TLS code**: The most famous example is Heartbleed (CVE-2014-0160): OpenSSL's heartbeat extension read the payload length from the request, allocated a response buffer of that size, then copied `payload_length` bytes from the request into the response — without checking that the request actually contained that many bytes. The response included whatever was in memory after the short request, potentially including private keys and session data.

**What to look for**:
- Does the code trust a client-specified length without verifying the actual data available?
- In certificate parsing, does it read a length field and then access that many bytes without checking the remaining buffer?
- Are there off-by-one errors where `<=` should be `<` (or vice versa) in bounds checks?

### CWE-416: Use After Free

**What it is**: Accessing memory that has been freed. The memory may have been reallocated for a different purpose, so reading it returns wrong data and writing to it corrupts unrelated structures.

**How it manifests in crypto/TLS code**: TLS connections involve complex state machines with multiple objects (SSL session, certificate chain, cipher state) that have overlapping lifetimes. When a connection is torn down — especially during error handling or renegotiation — an object might be freed while another object still holds a pointer to it.

**What to look for**:
- Error paths: when a function fails partway through, are all the objects it allocated properly tracked? Does the cleanup code free something that a caller still references?
- Session resumption: when a session is resumed, are old session objects properly managed?
- Renegotiation: during mid-connection renegotiation, old and new state coexist temporarily. Are there dangling references to the old state after it's freed?

### CWE-476: NULL Pointer Dereference

**What it is**: Dereferencing a pointer that is NULL, typically causing a crash (denial of service). In some architectures or configurations, NULL dereference can be more severe.

**How it manifests in crypto/TLS code**: A function allocates memory or looks up an object and gets NULL (allocation failure, missing certificate, unsupported extension). The return value isn't checked, and the code proceeds to dereference the NULL pointer.

**What to look for**:
- Does every `malloc`/`XMALLOC` return value get checked?
- When a lookup function returns NULL (e.g., "no certificate found"), does the caller handle that case?
- In error paths, could a pointer be NULL by the time cleanup code tries to use it?

### CWE-190: Integer Overflow or Wraparound

**What it is**: An arithmetic operation produces a value that exceeds the range of its integer type, wrapping around to a small value. When this small value is used as a buffer size, the allocated buffer is far too small for the data that will be written to it.

**How it manifests in crypto/TLS code**: Size calculations are pervasive in crypto code — computing buffer sizes for key material, message construction, certificate chains. A multiplication overflow is the classic pattern: `total_size = count * element_size`. If `count` is attacker-controlled (e.g., number of extensions in a ClientHello), the multiplication can overflow, resulting in a tiny allocation followed by a large write.

**What to look for**:
- Are size calculations validated against overflow before being used for allocation?
- The CERT C rule INT32-C specifies: check that `a * b` doesn't overflow before using the result. For unsigned: `if (a != 0 && b > UINT_MAX / a) { /* overflow */ }`.
- Are length fields from protocol messages validated against reasonable maximums before being used in calculations?
- Addition overflow: `if (a + b < a) { /* overflow */ }` — but note that signed integer overflow is undefined behavior in C, making it even more dangerous.

### CWE-20: Improper Input Validation

**What it is**: The broad category covering any failure to validate input before processing. For a TLS library, "input" is everything received over the network — every byte in every handshake message, every field in every certificate, every extension value.

**How it manifests in crypto/TLS code**: This is the umbrella category. Specific manifestations include:
- Length fields not checked against remaining buffer
- Enum values not checked against valid ranges (e.g., TLS cipher suite IDs, extension types)
- Version numbers not checked for support
- Certificate chain depths not limited
- DH parameters not checked for minimum size (enables Logjam)
- RSA key sizes not checked against policy

## Cryptographic CWEs — Algorithm and Implementation Weaknesses

These CWEs are specific to cryptographic code and address weaknesses in the cryptographic properties rather than memory safety.

### CWE-327: Use of a Broken or Risky Cryptographic Algorithm

**What it is**: Using a cryptographic algorithm that has known weaknesses — either theoretical breaks or practical attacks that reduce its effective security below acceptable levels.

**How it manifests**: Supporting deprecated algorithms like DES, RC4, MD5 (for authentication), or SHA-1 (for signatures). In a TLS library, this usually means the algorithm is available as a cipher suite option. The question is whether it's enabled by default, whether it can be negotiated down to by an attacker, and whether there are configuration options to disable it.

**Triage context**: Reports about "wolfSSL supports [weak algorithm]" require context — does it support it by default, or only when explicitly enabled? Is it behind a `#ifdef` that's off by default? Can an attacker force its use via downgrade? The answers determine whether this is a configuration issue, a protocol issue, or a non-issue.

### CWE-1240: Use of a Cryptographic Primitive with a Risky Implementation

**What it is**: The algorithm is correct, but the implementation has properties that weaken it. This is the CWE for side-channel vulnerabilities — the algorithm (e.g., AES) is fine, but the implementation (e.g., using table lookups indexed by key-dependent values) leaks information.

**How it manifests**: Every side-channel vulnerability in a crypto library falls under this CWE. When a reporter claims a timing or cache side channel, this is the CWE category. The implementation computes the correct mathematical result but does so in a way that leaks secret information through physical observables.

**Triage context**: This is one of the most complex CWE categories to evaluate because the vulnerability exists at the intersection of the C code, the compiler output, and the hardware behavior. Source-level analysis alone cannot confirm or deny a side-channel vulnerability — the compiled binary on the specific target architecture must be considered.

### CWE-326: Inadequate Encryption Strength

**What it is**: Using key sizes or parameters that provide less security than intended. Different from CWE-327 (broken algorithm) — the algorithm itself is fine, but the parameters are too weak.

**How it manifests**: Accepting DH parameters smaller than 2048 bits, RSA keys shorter than 2048 bits, or ECC curves smaller than 256 bits. In TLS, this can happen through negotiation — the server offers weak parameters, or the client accepts them.

### CWE-325: Missing Cryptographic Step

**What it is**: A required step in a cryptographic protocol is skipped or omitted. The individual cryptographic operations may be correct, but the protocol is incomplete.

**How it manifests**: Skipping certificate verification, not checking certificate revocation, not validating the server's key exchange signature, not verifying the Finished message. These omissions can allow man-in-the-middle attacks even though the encryption itself is working correctly.

### CWE-347: Improper Verification of Cryptographic Signature

**What it is**: A cryptographic signature is checked incorrectly or not at all. This is more specific than CWE-325 — it's specifically about signature verification being present but wrong.

**How it manifests**: Checking only part of a signature, accepting malformed signatures, comparing signatures with a non-constant-time comparison (which can leak the valid signature through timing), or having logic errors in the verification path. A classic pattern is BER/DER parsing of PKCS#1 v1.5 signatures where extra data after the digest is ignored, allowing signature forgery (Bleichenbacher's signature forgery attack on RSA PKCS#1 v1.5 with low public exponents).

### CWE-331: Insufficient Entropy

**What it is**: The random number generator doesn't collect enough entropy, making its output predictable. If cryptographic keys or nonces are generated with insufficient entropy, they can be guessed.

**How it manifests in embedded crypto**: Embedded systems often lack good entropy sources. No `/dev/urandom`, no hardware RNG, and possibly no access to high-resolution timing. The DRBG (Deterministic Random Bit Generator) is only as strong as its seed — if the seed has low entropy, all generated keys are weak. Reports may claim that on a specific embedded platform, wolfSSL's RNG initialization doesn't collect sufficient entropy.

## CERT C Secure Coding Rules for Crypto Code

The CERT C Secure Coding Standard from Carnegie Mellon's Software Engineering Institute codifies rules that prevent the root causes of the CWE categories above. These rules are directly applicable when evaluating whether code is vulnerable.

### Integer Rules (INT)

**INT30-C: Ensure that unsigned integer operations do not wrap.** When computing buffer sizes or copy lengths, unsigned wraparound turns a large value into a small one, leading to undersized allocations. Every arithmetic operation on attacker-influenced values must be checked.

**INT31-C: Ensure that integer conversions do not result in lost or misinterpreted data.** Casting a `size_t` (64-bit on modern systems) to `int` (32-bit) silently truncates. If a 5GB length field is truncated to a 32-bit integer, it becomes a small positive number — leading to a small allocation and large overflow.

**INT32-C: Ensure that operations on signed integers do not result in overflow.** Signed integer overflow is undefined behavior in C. The compiler is allowed to assume it never happens, which means overflow checks like `if (a + b < a)` can be optimized away entirely. Use unsigned types for sizes, or check before the operation.

### Memory Rules (MEM)

**MEM30-C: Do not access freed memory.** After `free(ptr)`, any access through `ptr` is undefined. In crypto code, this commonly happens in error-handling cleanup paths where multiple objects are freed but a later cleanup step still references an already-freed object.

**MEM35-C: Allocate sufficient memory for an object.** The allocation size must account for all data that will be stored. Off-by-one errors (forgetting the null terminator, miscounting struct padding) and integer overflow in size calculations are the usual causes.

**MEM36-C: Do not modify the alignment of objects by calling realloc().** Less commonly an issue in crypto code, but relevant when buffers are reallocated during protocol processing.

### Array Rules (ARR)

**ARR30-C: Do not form or use out-of-bounds pointers or array subscripts.** This covers both reads and writes. In protocol parsing, every array access using a value derived from network input must be bounds-checked. This includes not just the obvious `buffer[index]` patterns but also pointer arithmetic like `ptr + length` where `length` comes from a protocol field.

### String Rules (STR)

**STR31-C: Guarantee that storage for strings has sufficient space for character data and the null terminator.** Particularly relevant for ASN.1 string handling. ASN.1 strings are NOT null-terminated — they use explicit length fields. When these strings are copied into C null-terminated strings, the destination must have space for the length-encoded content PLUS a null terminator. Additionally, ASN.1 strings can contain embedded null bytes, which truncate C string operations — this has been exploited for certificate spoofing (the "null prefix" attack).

## Mapping CWEs to Code Areas

Understanding which CWE categories are most relevant to which parts of the codebase helps focus investigation:

**TLS Handshake Processing** (`internal.c`, `tls.c`, `tls13.c`): CWE-787, CWE-120, CWE-125 — Handshake messages contain length-delimited fields that must be parsed correctly. Extensions have nested length fields. State machine logic must handle messages in unexpected orders.

**X.509 Certificate Parsing** (`asn.c`, `ssl_certman.c`): CWE-121, CWE-122, CWE-125, CWE-190 — ASN.1/DER parsing is complex, with variable-length encoding, nested structures, and many string types. Integer overflow in length calculations is a recurring theme. Stack-based buffers for OID or name processing can overflow.

**Cryptographic Operations** (`aes.c`, `rsa.c`, `ecc.c`, `dh.c`): CWE-1240, CWE-327, CWE-331 — Side-channel leaks through non-constant-time operations. Use of deprecated algorithms. Insufficient entropy in key generation.

**DRBG/RNG** (`random.c`, `sp_drbg.c`): CWE-331 — Entropy collection and seed management. Platform-specific entropy source availability.

**PKCS#7/CMS** (`pkcs7.c`): CWE-122, CWE-787 — Complex nested ASN.1 structures with signed and encrypted data. Multiple layers of length fields and content types.

**wolfSSH/wolfBoot/wolfTPM**: Similar patterns to wolfSSL/wolfCrypt but with protocol-specific parsing (SSH protocol messages, firmware update headers, TPM command structures). Each has its own set of length-delimited fields that must be parsed safely.

## Attack Surface Analysis Framework

When evaluating a vulnerability report, the CWE category tells you *what kind* of weakness exists. But equally important is *what conditions are required to reach it* — the attack surface. A critical buffer overflow in code that can only be reached if a trusted CA issues a malformed certificate is fundamentally different from the same overflow in code that processes unauthenticated ClientHello messages.

### CVSS Dimensions as a Structured Framework

The CVSS scoring system provides a useful vocabulary for describing attack prerequisites, even when not computing a formal score:

**Attack Vector (AV)** — How does the attacker reach the vulnerable code?
- **Network**: The attacker sends a packet over the network. This is the most common scenario for TLS libraries — the attacker is a remote TLS client or server. Most TLS handshake parsing vulnerabilities are network-reachable.
- **Adjacent**: The attacker must be on the same network segment (e.g., same LAN, same WiFi). Relevant for some DTLS or local network protocol attacks.
- **Local**: The attacker must have local access to the system (e.g., running code on the same machine). Relevant for cache-based side-channel attacks where the attacker shares CPU/cache with the victim process.
- **Physical**: The attacker must have physical access to the device. Relevant for fault injection, power analysis, and EM attacks on embedded targets.

**Attack Complexity (AC)** — What conditions beyond the attacker's control must exist?
- **Low**: The attack works reliably without special conditions. Example: sending a malformed ClientHello that crashes the server.
- **High**: The attack requires conditions the attacker cannot reliably control — winning a race condition, specific memory layout, specific network timing. Example: Raccoon attack requires precise timing measurement and many repeated connections.

**Privileges Required (PR)** — What access level does the attacker need before the attack?
- **None**: No prior authentication. An anonymous remote attacker can trigger it. This applies to most TLS handshake vulnerabilities since the handshake occurs before authentication.
- **Low**: The attacker needs some kind of authenticated access. Example: a vulnerability in post-handshake client certificate processing that requires the attacker to have a valid client certificate.
- **High**: The attacker needs administrative or highly privileged access. Rarely applies to TLS library vulnerabilities.

**User Interaction (UI)** — Does a human need to do something?
- **None**: The attack is fully automated. Most TLS library vulnerabilities require no user interaction.
- **Required**: A user must take some action (click a link, visit a page). Relevant for browser-side TLS attacks like BEAST where the victim must visit the attacker's page.

### Common Attack Surface Patterns in TLS/Crypto Libraries

These patterns recur across vulnerability reports. Recognizing them helps structure the investigation:

**Pattern 1: Unauthenticated remote, default config** — The most severe. The vulnerable code runs during TLS handshake processing before any authentication, in a default build with no special configuration. An anonymous attacker on the network can trigger it. Examples: buffer overflow in ClientHello extension parsing, heap over-read in certificate message processing. These are typically Critical/High severity.

**Pattern 2: Unauthenticated remote, non-default config** — The vulnerable code is network-reachable without authentication, but only when a specific build option or runtime configuration is enabled. Examples: vulnerability in PSK processing (requires `--enable-psk`), vulnerability in DTLS (requires DTLS to be compiled in and used), vulnerability in ECH (requires `--enable-ech`). Severity depends on how commonly the feature is enabled.

**Pattern 3: Requires MITM position** — The attacker must intercept and modify traffic between client and server. This is a stronger prerequisite than simple network access. Examples: protocol downgrade attacks (POODLE, FREAK), certificate substitution. Still serious but requires a more capable attacker.

**Pattern 4: Requires trusted party misbehavior** — Exploitation requires a trusted entity (CA, server operator, device manufacturer) to act maliciously or make an unusual error. Examples: vulnerability triggered by a certificate with a subject name exceeding typical lengths (requires the CA to issue such a certificate), vulnerability in server-configured DH parameters (requires the server operator to set weak parameters). The question to surface: would this trusted party have any reason to do this? What would a CA or server admin gain? This context is factual — do not assess it, but do surface it.

**Pattern 5: Requires specific build/platform** — The vulnerable code only exists on certain platforms or with certain build flags. Examples: ARM-specific assembly code vulnerability (only affects ARM builds), vulnerability in hardware crypto acceleration (only when hardware crypto is enabled and the specific hardware is present). The key data point: what fraction of deployments would have this configuration?

**Pattern 6: Requires local/physical access** — The attacker must be on the same machine or have physical access to the device. Examples: cache-based side-channel attacks (requires sharing a CPU), fault injection (requires physical access to the board), power analysis (requires measuring power consumption). These are almost always embedded/IoT-specific.

**Pattern 7: Theoretical/requires ideal conditions** — The vulnerability exists in the code but exploitation requires conditions that are difficult to achieve in practice — precise timing across the internet, specific memory layout, millions of observations. Examples: some timing attacks that require sub-microsecond precision over the internet, statistical attacks requiring billions of observations. The key data points to surface: how many observations/attempts are needed, what precision is required, and over what kind of channel.

### What to Surface vs. What to Assess

The attack surface section of a dossier presents **factual data** about prerequisites. It does NOT assess whether those prerequisites are "realistic," "likely," or "difficult." The distinction:

**Surface (factual data)**: "This code path is reached during TLS 1.3 handshake processing of the Certificate message. It requires `HAVE_TLS13` to be defined, which is enabled by default. The attacker must send a server Certificate message containing a malformed X.509 certificate. No prior authentication is required."

**Do NOT assess**: "This is easily exploitable because..." or "This would be difficult to exploit in practice because..." or "This is unlikely to be triggered in a real deployment."

The engineer reads the factual prerequisites and draws their own conclusions about real-world risk.
