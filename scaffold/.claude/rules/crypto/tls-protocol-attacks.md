---
paths:
  - "**/internal.c"
  - "**/tls13.c"
---

# TLS Protocol Attacks and Implementation Vulnerability Patterns

## Protocol Flaws vs. Implementation Bugs

When investigating a TLS vulnerability report, the first critical distinction is whether the reported issue is a protocol-level flaw or an implementation bug. This distinction fundamentally changes the triage approach.

**Protocol-level flaws** are weaknesses in the TLS specification itself. They affect every conforming implementation — if wolfSSL implements the protocol correctly, it inherits the protocol's weaknesses. Examples include POODLE (SSLv3 padding is not authenticated by design), BEAST (CBC IV reuse is specified in TLS 1.0), and CRIME (TLS compression is specified to occur before encryption). The fix is to disable the vulnerable protocol feature or version.

**Implementation bugs** are mistakes in a specific library's code. The protocol specification is fine, but the library implements it incorrectly. Examples include Heartbleed (OpenSSL-specific bounds check omission), and most buffer overflows. The fix is to correct the code.

**Why this matters for triage**: When a reporter claims a protocol-level vulnerability, the question is: "Does wolfSSL support this protocol version/feature, and is it enabled by default?" When they claim an implementation bug, the question is: "Does the specific code pattern they describe actually exist in wolfSSL's implementation?"

## Historical TLS/SSL Attack Reference

Each entry below documents the attack's mechanism, the root code pattern that enables it, and what a triage engineer should look for in the codebase when evaluating a related report.

### BEAST — Browser Exploit Against SSL/TLS (CVE-2011-3389)

**Affects**: SSL 3.0, TLS 1.0
**Type**: Protocol flaw (CBC IV handling specified in the protocol)

**Mechanism**: In TLS 1.0, CBC mode reuses the last ciphertext block from the previous record as the Initialization Vector (IV) for the next record. This IV is predictable — the attacker can observe it on the wire. With a predictable IV, the attacker can mount a chosen-plaintext attack: they inject known plaintext alongside the secret they want to recover and observe whether the resulting ciphertext matches a predicted value. By iterating, they can recover the secret byte by byte.

**Root Code Pattern**: `IV_for_record_N = last_ciphertext_block_of_record_N-1`. The protocol mandates this — it's not a bug but a design weakness corrected in TLS 1.1 (which uses explicit, random IVs per record).

**Triage relevance**: If a report claims BEAST-like vulnerability, check whether TLS 1.0 is enabled by default and whether 1/n-1 record splitting (a workaround that splits each record to make the IV unpredictable) is implemented.

### CRIME — Compression Ratio Info-leak Made Easy (CVE-2012-4929)

**Affects**: TLS with compression enabled (any version)
**Type**: Protocol flaw (compression before encryption leaks plaintext length)

**Mechanism**: When TLS compression is enabled, the compressed size of a record depends on its content. If an attacker can inject chosen plaintext alongside a secret (like a session cookie) and observe the compressed record size, they can recover the secret: guessing a byte correctly will compress better (smaller output) than guessing incorrectly.

**Root Code Pattern**: `compress(plaintext) → encrypt(compressed_data)`. The compressed output size varies with content, and the encrypted record size is observable on the wire.

**Triage relevance**: Check whether TLS compression is supported and whether it's enabled by default. Most libraries disabled TLS compression entirely after CRIME. If it's behind a build flag that's off by default, the practical risk is low.

### BREACH — Browser Reconnaissance and Exfiltration via Adaptive Compression of Hypertext (CVE-2013-3587)

**Affects**: HTTP-layer compression (not TLS compression)
**Type**: Application-layer issue, not a TLS library vulnerability

**Mechanism**: Same principle as CRIME, but exploits HTTP-level compression (gzip/deflate of response bodies) rather than TLS-level compression. If a web application reflects user input in a compressed response that also contains a secret (like a CSRF token), the attacker can deduce the secret from response size.

**Triage relevance**: This is NOT a TLS library vulnerability. If a reporter claims BREACH against wolfSSL, the issue is in the application layer, not the crypto library. wolfSSL does not control HTTP response compression.

### Heartbleed (CVE-2014-0160)

**Affects**: OpenSSL only (implementation bug, not protocol)
**Type**: Implementation bug (CWE-125, out-of-bounds read)

**Mechanism**: The TLS heartbeat extension allows one side to send a payload and receive it echoed back. The heartbeat message includes a payload length field and the actual payload data. OpenSSL trusted the payload length field without checking it against the actual payload data received. If the attacker sent a heartbeat with `payload_length = 65535` but only 1 byte of actual payload, OpenSSL would read 65534 bytes past the end of the received data — returning whatever happened to be in adjacent memory, potentially including private keys, session tokens, and other sensitive data.

**Root Code Pattern**:
```c
// Pseudocode of the bug:
payload_length = read_uint16(request);  // attacker-controlled
payload = request + 3;                   // actual data starts here
// MISSING: check that (payload_length <= request_remaining_bytes)
memcpy(response, payload, payload_length);  // reads past end of request
```

**Triage relevance**: This pattern — trusting a client-specified length to determine how much data to read — is the archetype of CWE-125 in protocol code. When evaluating reports about buffer over-reads, look for this exact pattern: a length field read from the message, used without validation against the actual remaining message data.

### POODLE — Padding Oracle On Downgraded Legacy Encryption (CVE-2014-3566)

**Affects**: SSL 3.0
**Type**: Protocol flaw (padding not authenticated)

**Mechanism**: In SSL 3.0, CBC mode padding is not covered by the MAC. The protocol specifies that the last byte of padding indicates the padding length, but the content of the other padding bytes is unspecified and not verified. This means an attacker can manipulate padding bytes without detection. By carefully positioning a secret byte at the end of a cipher block and manipulating the padding, the attacker can determine whether their guess for that byte is correct (valid padding = no error; invalid padding = error). This requires ~256 requests per byte of secret.

**Root Code Pattern**: The server checks `padding_length = last_byte` and verifies that padding fills the right number of bytes, but does NOT verify padding byte values (unlike TLS 1.0+ which requires all padding bytes to equal the padding length). The MAC is computed over the plaintext before padding is added, so padding manipulation is undetected by the MAC.

**Triage relevance**: Is SSLv3 support compiled in? Is it enabled by default? Can a man-in-the-middle downgrade a connection from TLS to SSLv3? (This is the "Downgraded" part of POODLE — the attacker forces the downgrade, then exploits SSLv3's weak padding.)

### FREAK — Factoring RSA Export Keys (CVE-2015-0204)

**Affects**: Implementations supporting RSA export cipher suites
**Type**: Implementation bug (accepting export-grade crypto when not offered)

**Mechanism**: During the TLS handshake, a man-in-the-middle modifies the ClientHello to request export cipher suites (using 512-bit RSA keys, which can be factored in hours). The server responds with an export-grade key. The vulnerability was that many clients would accept this export-grade key even though they didn't request it — they'd use the weak 512-bit key for the key exchange, allowing the attacker to decrypt the session.

**Root Code Pattern**: The client's handshake processing accepted the server's export-grade key exchange without checking that it matched the cipher suites the client had offered. The state machine didn't enforce consistency between what was negotiated and what was received.

**Triage relevance**: Are export cipher suites supported? Are they available by default? Does the handshake state machine validate that the server's key exchange is consistent with the negotiated cipher suite?

### Logjam (CVE-2015-4000)

**Affects**: Implementations supporting DHE export cipher suites
**Type**: Protocol weakness + implementation issue

**Mechanism**: Similar to FREAK but for Diffie-Hellman. Export DHE uses 512-bit DH groups, which can be broken with precomputation. Additionally, many servers use the same small set of standard DH groups. By precomputing the discrete logarithm for common 512-bit groups, an attacker can break DHE in real time. The attack is amplified because many servers also used 1024-bit groups that share structure, potentially allowing state-level attackers to break even non-export DHE.

**Root Code Pattern**: Accepting DH parameters below a minimum size. The client doesn't check that the server's DH prime is large enough, or the server offers small parameters.

**Triage relevance**: What's the minimum DH parameter size enforced? Is there a configurable minimum? Does the default configuration reject small DH groups?

### DROWN — Decrypting RSA with Obsolete and Weakened eNcryption (CVE-2016-0800)

**Affects**: Servers with SSLv2 enabled (even if not used by clients)
**Type**: Cross-protocol attack

**Mechanism**: SSLv2 has fundamental weaknesses that allow an attacker to decrypt RSA key exchanges. If a server supports SSLv2 (even if all clients use TLS 1.2), the attacker can use SSLv2 handshakes to perform a Bleichenbacher-style oracle attack against the server's RSA key. Since the RSA key is shared between SSLv2 and TLS, decrypting an SSLv2 session reveals the RSA private key, which can then be used to decrypt TLS sessions.

**Root Code Pattern**: The server uses the same RSA key for SSLv2 and TLS. SSLv2 support is compiled in and enabled.

**Triage relevance**: Is SSLv2 support compiled in? Even if it's not the default, can it be enabled? Does the server share RSA keys between protocol versions?

### ROBOT — Return of Bleichenbacher's Oracle Threat (CVE-2017-13099)

**Affects**: Implementations using RSA key exchange with PKCS#1 v1.5 padding
**Type**: Implementation bug (timing/behavior oracle)

**Mechanism**: Daniel Bleichenbacher's 1998 attack showed that if a server reveals whether RSA PKCS#1 v1.5 padding is valid — through error messages, timing, or any other signal — an attacker can iteratively decrypt RSA ciphertexts with about 1 million adaptive queries. The ROBOT researchers found that this vulnerability persists because servers leak padding validity through subtle channels: different TLS alert codes, TCP RST vs. FIN, different response timing, or different numbers of alert messages.

**Root Code Pattern**: Any code path difference between "padding valid" and "padding invalid" creates an oracle. Even this seemingly safe code leaks:
```c
// STILL VULNERABLE — execution time differs
if (pkcs1_padding_valid(decrypted)) {
    premaster_secret = extract_premaster(decrypted);
} else {
    premaster_secret = generate_random_premaster();
}
```
The `extract_premaster` and `generate_random_premaster` paths take different amounts of time, different numbers of instructions, and may trigger different cache patterns.

**The correct fix** is to always perform both operations and select the result with a constant-time conditional:
```c
random_pms = generate_random_premaster();
real_pms = extract_premaster(decrypted);
valid = pkcs1_padding_valid(decrypted);
// constant-time select:
premaster_secret = ct_select(valid, real_pms, random_pms);
```

**Triage relevance**: Is RSA key exchange with PKCS#1 v1.5 supported? What does the error handling look like? Does the code path diverge based on padding validity? Even if the error codes are the same, is the timing identical?

### Raccoon (CVE-2020-1968)

**Affects**: DH key exchange in TLS (any version using DHE)
**Type**: Protocol weakness + implementation timing

**Mechanism**: The DH shared secret (the result of `g^(ab) mod p`) can have leading zero bytes. When these zeros are stripped before being passed to the PRF/KDF as the premaster secret, the input to the hash function is shorter. Shorter input means fewer bytes to hash, which takes less time. An attacker measuring the TLS handshake timing can detect whether the shared secret had leading zeros, which leaks information about the private DH values.

**Root Code Pattern**: `premaster_secret = strip_leading_zeros(dh_shared_secret)` followed by `kdf(premaster_secret)`. The `kdf` call takes variable time because `premaster_secret` has variable length.

**Fix pattern**: Pad the DH shared secret to the full size of the DH prime before passing it to the KDF, so the hash always processes the same amount of data.

**Triage relevance**: How is the DH premaster secret handled before KDF? Is it padded to fixed length? Is the hash computation constant-time with respect to input length?

## ASN.1 and X.509 Parsing Vulnerability Patterns

ASN.1 (Abstract Syntax Notation One) is the encoding format used for X.509 certificates, PKCS structures, and many other cryptographic data formats. Parsing ASN.1 in C is one of the most vulnerability-prone operations in a TLS library. Understanding why helps evaluate reports about parsing issues.

### Why ASN.1 Is a Vulnerability Magnet

**Variable-length everything**: Every field in ASN.1 has a type tag, a length, and a value. The length itself is variable-length — short form (1 byte for lengths 0-127) and long form (first byte indicates how many subsequent bytes encode the length). This means parsing code must handle lengths-of-lengths, which is inherently complex.

**Attacker-controlled input**: Certificates come from the network. A malicious server (or MITM) can send any bytes as a certificate. The parser must handle arbitrary, potentially malformed input safely.

**Deeply nested structures**: A certificate contains multiple layers of ASN.1 structures — the outer SEQUENCE, the TBS (to-be-signed) certificate, extensions (which are themselves ASN.1-encoded), and extension values (often ASN.1 again). Each layer has its own length fields that must be consistent.

**No null termination**: ASN.1 strings use explicit length, not null termination. They can contain embedded null bytes. When an ASN.1 string containing `"example.com\x00.evil.com"` is converted to a C string, `strlen()` returns `11` (stopping at the null), but the ASN.1 length says `24`. If the certificate validation uses C string functions while the CN was matched using the full ASN.1 length, the certificate for `evil.com` can appear to be valid for `example.com`. This "null prefix" attack was real and affected multiple libraries.

**Type confusion**: ASN.1 has constructed and primitive forms of some types. A SEQUENCE is always constructed, but an OCTET STRING can be either primitive (data inline) or constructed (data is a sequence of sub-OCTET-STRINGs). Parsers that don't handle both forms correctly can be tricked into misinterpreting data.

### Specific ASN.1 Vulnerability Patterns

**Length overflow**: A length field says the value is 2GB, but only 100 bytes follow. If the parser allocates based on the length field without checking remaining data, it either allocates too much memory (DoS) or reads past the end of the buffer.

**Nested length inconsistency**: The outer SEQUENCE says it contains 500 bytes. Inside, a sub-element says it contains 600 bytes. If the parser doesn't track remaining bytes at each nesting level, the sub-element read overflows the outer boundary.

**Indefinite length**: BER (but not DER) allows indefinite-length encoding, terminated by `\x00\x00`. If a parser expects DER but encounters indefinite-length encoding, it may process data incorrectly. Parsers should reject indefinite-length in contexts requiring DER (like certificates).

**Integer encoding**: ASN.1 integers are big-endian with a sign bit. A negative number is valid in ASN.1 but nonsensical for a certificate serial number or RSA public exponent. Parsers that convert ASN.1 integers directly to C unsigned types without checking for negative values can produce unexpected behavior.

## Handshake State Machine Vulnerabilities

The TLS handshake is a complex state machine where both client and server exchange messages in a specific order. Vulnerabilities arise when the state machine accepts messages in unexpected states.

### Out-of-Order Messages
The TLS specification defines a strict message ordering (ClientHello → ServerHello → Certificate → ...). If the implementation doesn't enforce this ordering, an attacker can send messages out of order to reach unexpected code paths. For example, sending a ChangeCipherSpec before key exchange is complete could cause the implementation to switch to encryption with a null or uninitialized key.

### Unexpected Message Types
Each state in the handshake expects specific message types. If the implementation doesn't validate the message type against the current state, unexpected messages can trigger unintended behavior. For example, sending a ClientHello when the server expects a Certificate could confuse the state machine.

### Version Confusion
TLS 1.2 and TLS 1.3 have significantly different handshake flows. TLS 1.3 is disguised as TLS 1.2 in the ClientHello (for middlebox compatibility), with the real version negotiated via the `supported_versions` extension. If the version detection logic is wrong, the implementation might process a TLS 1.3 handshake using TLS 1.2 code paths (or vice versa), potentially accessing uninitialized fields or using incompatible processing.

### Extension Parsing
TLS extensions are length-delimited and can contain arbitrary data. Each extension type has its own internal format. Common vulnerabilities:
- Total extensions length exceeds the remaining handshake message
- Individual extension length exceeds the remaining extensions block
- Extension data is malformed for its type but length checks pass
- Duplicate extensions (spec says some must not be duplicated)
- Unknown extension types — should they be ignored or cause an error?

### Renegotiation
TLS renegotiation (pre-TLS 1.3) allows establishing a new handshake within an existing connection. This is complex because old and new state coexist during the renegotiation. The renegotiation attack (CVE-2009-3555) exploited the fact that data sent before renegotiation could be spliced with data after, allowing an attacker to inject a prefix into an authenticated connection. The fix (RFC 5746) requires a renegotiation_info extension binding the renegotiation to the existing connection.

## PKCS#1 v1.5 Signature Forgery (Bleichenbacher 2006)

This is a different attack from Bleichenbacher's 1998 padding oracle. It targets RSA signature *verification* rather than RSA *decryption*, and it works without any oracle — it's a single-shot forgery.

### How RSA PKCS#1 v1.5 Signatures Work

A PKCS#1 v1.5 RSA signature has this structure after the signer computes `signature^e mod n`:
```
0x00 0x01 [0xFF padding...] 0x00 [ASN.1 DigestInfo] [hash value]
```
The DigestInfo is an ASN.1 structure that identifies the hash algorithm and contains the hash. The hash and DigestInfo must be right-justified — all the space between the 0x00 separator and the DigestInfo is filled with 0xFF padding.

### The Forgery

When `e = 3` (a common choice for RSA public exponents), the attacker can construct a value whose cube root is an integer that looks like a valid PKCS#1 v1.5 signature block. They place the correct ASN.1 DigestInfo and hash toward the left side of the block (not right-justified as required), followed by garbage bytes.

If the verifier:
1. Checks that the block starts with `0x00 0x01`
2. Finds the 0xFF padding and 0x00 separator
3. Parses the ASN.1 DigestInfo to extract the hash
4. **But does NOT verify that the hash is right-justified** (i.e., ignores trailing garbage after the ASN.1 structure)

...then the forged signature passes verification. The attacker never needed the private key.

### Root Cause: Parsing-Based vs Construction-Based Verification

The vulnerability arises from *parsing* the signature block to extract the hash, rather than *constructing* the expected block and comparing it byte-for-byte. A parser that reads the ASN.1 structure and extracts the hash will succeed even if there are extra bytes after the structure. A construction-based verifier builds the exact expected block and compares the entire decrypted signature against it — any extra or modified bytes cause failure.

BER vs DER ambiguity makes this worse: BER allows multiple valid length encodings for the same data, so a BER-tolerant parser may accept malformed length fields that a strict DER parser would reject. The PKCS#1 v2.1 specification changed from BER to DER partly for this reason.

**This attack still appears in the wild**: CVE-2026-22866 (ENS DNSSEC Oracle) demonstrates that PKCS#1 v1.5 signature forgery via missing padding validation continues to affect real systems more than 20 years after the original disclosure.

## Protocol Fuzzing and What It Reveals

### Dolev-Yao Model-Guided Fuzzing (tlspuffin)

Traditional fuzzers mutate bytes randomly and observe crashes. Protocol fuzzers like tlspuffin use a formal model of the attacker (the Dolev-Yao model from protocol verification) where the attacker has full control over network messages — they can intercept, modify, replay, reorder, and inject messages.

tlspuffin represents TLS messages as symbolic terms (not raw bytes). Mutations operate at the protocol level: skip a message, duplicate it, swap two messages, replace a certificate with a different one, modify an extension's content while keeping valid length encoding. This finds logical bugs — state machine violations, session handling errors, resource management flaws — that bit-level fuzzers almost never reach.

### Findings Against wolfSSL (Trail of Bits, 2022)

tlspuffin found four CVEs in wolfSSL, all through message-level mutations:

**CVE-2022-38152**: NULL pointer dereference when `wolfSSL_clear()` is called during session resumption. The fuzzer discovered that certain session cache states combined with connection reuse led to accessing freed session data.

**CVE-2022-38153**: The `AddSessionToCache` function reused a cached entry for a large session ticket (700 bytes). The code allocated a buffer on the heap but then freed a pointer to a static buffer (`cacheSession->_staticTicket`) instead of the heap buffer. The fuzzer found this by mutating NewSessionTicket messages to contain oversized tickets, triggering the cache reuse path. Found within 1 hour of fuzzing. Required ~30 prior connections to populate the session cache's hash buckets.

**CVE-2022-39173**: Stack buffer overflow via duplicate cipher suites. The `RefineSuites` function didn't properly reset state between handshakes. By sending two ClientHellos each containing 13+ copies of the same cipher suite, the fuzzer created 169 suites exceeding the 150-suite stack buffer. This is a state machine issue — the refinement function assumed it would only process suites from a single handshake.

**CVE-2022-42905**: Heap buffer over-read in TLS record header parsing. Malformed record headers caused the parser to read beyond allocated buffer bounds.

## DTLS-Specific Vulnerability Patterns

DTLS (Datagram TLS) runs over UDP instead of TCP. This introduces unique vulnerabilities because UDP is connectionless — there's no TCP handshake to establish that the source IP is real, and packets can arrive out of order, be duplicated, or be lost.

### Cookie Verification Weaknesses

DTLS includes a cookie exchange (HelloVerifyRequest) designed to prevent DoS amplification — the server sends a cookie that the client must echo back before the server commits resources. However, if the cookie is not properly authenticated (using HMAC with a secret key), an attacker can compute valid cookies themselves, bypassing the anti-DoS mechanism.

wolfSSL's DTLS implementation has historically used a hash function rather than HMAC for cookies, meaning cookies don't contain any secret data and can be computed by an adversary who knows the hashing algorithm.

### DoS Amplification

DTLS servers that don't use the cookie exchange (or use weak cookies) can be used as DDoS amplifiers. The attacker sends a small ClientHello with a spoofed source IP. The server responds with a much larger ServerHello + Certificate + ServerKeyExchange directed at the spoofed IP. Research has measured amplification factors of 35-37x, making DTLS a significant amplification vector.

### Relevance to wolfSSL

Many wolfSSL embedded deployments use DTLS for IoT protocols (CoAP over DTLS, LwM2M). These deployments are particularly sensitive to DoS because the devices have limited resources. A vulnerability report about DTLS cookie handling or amplification should be investigated with the understanding that the affected devices may be resource-constrained IoT endpoints.

## TLS 1.3 Downgrade Resistance and Its Failure Modes

TLS 1.3 includes an explicit anti-downgrade mechanism: when a TLS 1.3-capable server negotiates TLS 1.2 (or lower), it embeds a specific sentinel value in the last 8 bytes of ServerHello.random. Clients that support TLS 1.3 check for this sentinel — if present, they know the server supports 1.3 but something (potentially an attacker) caused a downgrade, and they abort.

Despite this mechanism, research has demonstrated that some implementations (including major ones from Microsoft and Apple) could still be downgraded from TLS 1.3 to TLS 1.0. The failures occur when:
- The client doesn't check the sentinel at all
- The client checks the sentinel only for TLS 1.2 downgrades but not TLS 1.1/1.0
- The sentinel check is performed but its result is ignored in certain code paths
- Middle-boxes strip or modify the ServerHello.random before it reaches the client

For triage: any report about TLS version negotiation should include verification that the anti-downgrade sentinel is properly checked for all supported lower versions.
