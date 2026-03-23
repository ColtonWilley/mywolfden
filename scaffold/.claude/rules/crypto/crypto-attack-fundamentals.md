---
paths:
  - "**/rsa.c"
  - "**/ecc.c"
  - "**/random.c"
---

# Fundamental Principles of Cryptographic Attacks

This document distills the foundational principles underlying virtually all attacks against cryptographic implementations. These principles are more important than any specific attack — they explain *why* attacks work and enable reasoning about novel vulnerability reports that don't match any known pattern.

When investigating a security report, apply each principle as a lens: does the reported code exhibit any of these fundamental weaknesses? The specific attack technique may be new, but the underlying principle will be one of these.

## Principle 1: The Oracle Principle

**Any observable difference in system behavior that correlates with secret data creates an oracle an attacker can exploit.**

This is the single most important principle in cryptographic attack theory. An "oracle" is anything that answers a yes/no question about a secret. The attacker doesn't need to see the secret directly — they just need a signal that correlates with it. Given enough queries, even a 1-bit signal per query can reveal an entire secret key.

The observable difference can be almost anything:
- **Timing**: How long the operation takes (Bleichenbacher/ROBOT/Marvin, Lucky Thirteen, Raccoon, KyberSlash)
- **Error messages**: Different error codes for different failure modes (original Bleichenbacher 1998)
- **Error types**: TLS alert types, TCP RST vs FIN, connection close vs timeout
- **Power consumption**: Watts drawn by the CPU during the operation (DPA/SPA)
- **Cache state**: Which cache lines were accessed (Flush+Reload, Prime+Probe)
- **Electromagnetic radiation**: EM emissions from specific chip areas
- **Response presence/absence**: Whether the server responds at all vs drops the connection

**The fundamental question**: "Does the code behave *differently* — in any observable way — depending on the value of a secret?"

**Why even tiny leaks matter**: Information theory guarantees that any consistent correlation between observable behavior and secret data can be amplified through repetition. Bleichenbacher's original attack needed about 1 million queries but recovered a full RSA private key operation from a 1-bit oracle (valid padding vs invalid). Modern variants (ROBOT, Marvin) need far fewer queries with improved techniques, but the principle is the same: one bit at a time, repeated enough times, reveals everything.

**How this manifests in C crypto code**: The most common pattern is an `if` statement that branches on whether a cryptographic operation succeeded:

```c
// THIS CREATES AN ORACLE — even if both branches return the same error code,
// they take different amounts of time
if (rsa_padding_valid(decrypted)) {
    premaster = extract_premaster(decrypted);  // one code path
} else {
    premaster = random_bytes(48);               // different code path
}
```

The fix requires executing both paths and selecting the result with constant-time logic, so the observable behavior is identical regardless of padding validity.

**Examples that embody this principle**: Bleichenbacher's RSA padding oracle (1998 → ROBOT 2017 → Marvin 2023), Lucky Thirteen CBC timing oracle, POODLE padding oracle, Raccoon DH leading-zeros timing oracle, Vaudenay's CBC padding oracle. Each uses a different physical channel, but all exploit the same fundamental principle: the system answers "yes" or "no" to a question about the secret.

## Principle 2: The Trust Boundary Principle

**Every value that crosses a trust boundary must be validated against the receiving code's assumptions before use.**

A "trust boundary" exists wherever data flows from a less-trusted domain to a more-trusted one. In a TLS library, the primary trust boundary is the network: every byte in every received message is attacker-controlled. Secondary boundaries exist between protocol layers (TLS record → handshake message → extension → extension data), between data formats (DER → parsed certificate → validated chain), and between API callers and library internals.

The vulnerability pattern is always the same: a value from an untrusted source is used to control a privileged operation (memory access, loop count, array index, allocation size) without validating that the value is within the expected range.

**The fundamental question**: "Does this code use any attacker-controlled value to determine how much memory to access, how many iterations to perform, or which code path to take — and if so, is that value validated first?"

**Common trust boundary violations in crypto/TLS code**:

- **Length fields as buffer sizes**: Heartbleed is the archetype. A length field from the network was used as a `memcpy` size without checking it against the actual data available. The fix is trivial (one bounds check), but the class of vulnerability is vast because protocol messages are full of length fields.

- **Counts used in size calculations**: `total_size = count * element_size`. If `count` comes from a protocol message and isn't validated, the multiplication can overflow, producing a tiny allocation that's then overflowed by the actual data.

- **Nested length consistency**: A TLS extension says it's 100 bytes, but inside it, a sub-field says it's 200 bytes. If the parser doesn't track remaining bytes at each nesting level, the sub-field read overflows the extension boundary.

- **Type fields controlling parsing logic**: A certificate extension type determines which parser runs. If an unexpected type causes a code path that doesn't properly validate lengths, the attacker can trigger it by including that extension type.

**Why this principle is so productive for attackers**: Protocol parsers are complex, with many code paths for different message types, extensions, and options. Every `switch` case, every nested structure, every optional field is an opportunity to miss a validation check. The parser is the largest attack surface in a TLS library.

## Principle 3: The Semantic Gap Principle

**When two components interpret the same data differently, an attacker can craft data that means one thing to the first component and another to the second.**

This principle explains an entire class of attacks where the vulnerability isn't in any single component but in the *gap* between how two components understand the same data.

**The fundamental question**: "Are there two parts of this system that interpret the same data according to different rules? Could an attacker construct data that is valid under one interpretation but has a different meaning under the other?"

**How this manifests in crypto code**:

- **ASN.1 strings vs C strings**: ASN.1 strings are length-delimited and can contain embedded null bytes. C strings are null-terminated. A certificate for `"example.com\x00.evil.com"` is one string in ASN.1 (length 24) but appears to be just `"example.com"` to C's `strcmp`/`strlen`. A CA that validates ownership of `evil.com` issues the certificate; a TLS client that uses C string comparison accepts it as valid for `example.com`. This was a real attack that affected multiple libraries.

- **BER vs DER encoding**: BER (Basic Encoding Rules) allows multiple valid encodings for the same data — different length formats, constructed vs primitive forms. DER (Distinguished Encoding Rules) mandates a unique encoding. If a signature is created with DER but verified with a BER-tolerant parser, the parser may accept data with extra bytes, garbage padding, or alternative encodings that the signer never intended. This enables Bleichenbacher's signature forgery: the "signature" contains the correct hash buried in a valid-looking ASN.1 structure, but with trailing garbage that a lenient parser ignores.

- **Protocol version confusion**: TLS 1.3 is disguised as TLS 1.2 in the wire format (for middlebox compatibility). If the version detection logic is wrong, a TLS 1.3 handshake might be processed by TLS 1.2 code paths — accessing fields that don't exist in 1.3, or interpreting 1.3-specific structures with 1.2 semantics.

- **Integer signedness**: A value is unsigned in the protocol specification but stored in a signed integer in C. A large positive value becomes negative, potentially passing a `> 0` check and then being used as a negative offset or size.

## Principle 4: The Downgrade Principle

**If a system supports multiple security levels and the attacker can influence the selection, they will force the weakest option.**

Backward compatibility is the enemy of security. Every time a system supports an older, weaker protocol version, cipher suite, or key size "for compatibility," it gives attackers a lever. The attacker doesn't need to break the strong option — they just need to convince the system to use the weak one.

**The fundamental question**: "Can an attacker influence which security mechanism is selected? Does the system fall back to something weaker on failure?"

**How downgrade works**:

- **Active downgrade**: A man-in-the-middle modifies the ClientHello to remove strong options, leaving only weak ones. The server, seeing only weak options, selects the best available — which is weak. FREAK forced export RSA (512-bit keys, factorable in hours). Logjam forced export DHE (512-bit groups, breakable with precomputation).

- **Fallback downgrade**: The attacker disrupts the initial connection attempt (e.g., by sending a TCP RST). The client retries with a lower protocol version "for compatibility." The attacker keeps disrupting until the client falls back to SSLv3, then exploits POODLE.

- **Cross-protocol downgrade**: The attacker doesn't need to downgrade the victim's connection — they use a different protocol that shares the same key. DROWN uses SSLv2 handshakes (which the server still supports) to attack the RSA key that's shared with TLS connections.

**This isn't limited to protocol versions**: Downgrade applies to any negotiated parameter. Cipher suite negotiation, key size selection, algorithm choice, extension support — any negotiation where the attacker can manipulate messages to influence the outcome.

**Defense**: TLS 1.3's anti-downgrade mechanism embeds a sentinel value in the ServerHello.random field that clients must check. Any implementation that doesn't verify this sentinel is vulnerable to downgrade.

## Principle 5: The Composition Principle

**Individual components that are secure in isolation can become insecure when combined.**

Security properties don't always compose. An encryption scheme can be secure. A compression scheme can be secure. But compression followed by encryption leaks information, because the ciphertext length reveals how well the plaintext compressed, which reveals information about the plaintext content.

**The fundamental question**: "Does this system combine two operations in a way where one leaks information about the other's input? Does the order of operations matter for security?"

**How composition failures manifest**:

- **Compression + encryption**: CRIME and BREACH. The attacker injects known text alongside a secret (like a cookie). If their guess compresses well with the secret (because they share a common prefix), the resulting ciphertext is shorter. By trying different guesses and observing ciphertext length, they recover the secret byte by byte. The compression is fine alone. The encryption is fine alone. Together, compression leaks plaintext information through ciphertext size.

- **MAC-then-encrypt vs encrypt-then-MAC**: In MAC-then-encrypt (used in TLS < 1.3), the MAC is computed over plaintext, then everything is encrypted. To verify, the receiver must decrypt first, then check the MAC. If decryption produces invalid padding, the receiver discovers this before checking the MAC — creating a padding oracle. In encrypt-then-MAC, the MAC covers the ciphertext, so it can be verified before any decryption. The MAC and cipher are the same in both cases; only the order differs, but the security properties are dramatically different.

- **Error messages + encryption**: If a system returns different errors for "decryption succeeded but authentication failed" vs "decryption failed due to invalid padding," the attacker learns about the padding structure of the plaintext. This is Vaudenay's padding oracle attack. The encryption is secure. The error handling is reasonable. Together, they create an oracle.

## Principle 6: The State Machine Principle

**Protocol implementations are state machines, and any transition not explicitly denied is implicitly allowed — and potentially exploitable.**

A protocol defines a sequence of messages exchanged between parties. The implementation must track what state it's in and validate that each received message is expected in the current state. If it accepts a message that shouldn't be valid in the current state, the resulting processing may access uninitialized data, skip security checks, or produce undefined behavior.

**The fundamental question**: "Does the code validate that this message/operation is expected in the current state, or does it process whatever arrives?"

**Common state machine vulnerabilities**:

- **Out-of-order messages**: Sending a Finished message before the key exchange is complete. If the implementation doesn't check state, it might try to verify the Finished message with a key that hasn't been established yet — potentially using zeros or whatever happens to be in the key buffer.

- **Skipped messages**: Sending ChangeCipherSpec without doing a key exchange. If accepted, the implementation switches to "encrypted" mode with no key, potentially using null encryption.

- **Repeated messages**: Sending the same handshake message twice. The implementation may allocate resources for each copy, leading to memory exhaustion, or may process the duplicate in a state where the first message's side effects haven't been completed.

- **Cross-version confusion**: A message that's valid in TLS 1.2 but not in TLS 1.3, received during a connection that started as 1.2 but was being upgraded. If the implementation doesn't cleanly switch its state machine between protocol versions, it may process the message incorrectly.

**Why fuzzing is effective here**: State machine bugs are hard to find by code review because they require specific message sequences that exercise unexpected state transitions. Protocol fuzzers like tlspuffin are specifically designed to explore these sequences, which is why they have been effective at finding vulnerabilities in wolfSSL and other TLS implementations.

## Principle 7: The Physical Manifestation Principle

**Every computation has physical effects. If any physical effect correlates with secret data, the secret is leaking.**

This is not a software bug — it's a property of physical hardware. When a CPU executes an instruction, it consumes power, emits electromagnetic radiation, changes cache state, updates branch predictor tables, and takes a measurable amount of time. If any of these physical effects differ depending on the value of secret data, an attacker who can measure them learns about the secret.

**The fundamental question**: "Does this operation's physical footprint change depending on the secret value?" But this question has an essential prerequisite: **is the value actually secret?** Before evaluating whether an operation is constant-time, determine whether the data flowing through it is secret (private key material, nonces, shared secrets) or public (ciphertext, public key, protocol messages). A variable-time operation on public data does not create a side-channel vulnerability. The data secrecy classification methodology (see side-channel-attacks knowledge) provides the framework for making this determination as a factual code observation.

**The three independence requirements** (from Intel's guidance):
1. **Secret-Independent Runtime**: Every instruction operating on secret data must execute in the same amount of time regardless of the data's value. Division (`DIV`/`IDIV`) violates this — execution time varies with operand magnitude.
2. **Secret-Independent Code Access**: The value of a secret must not determine which branch of code executes. Branch prediction state changes are measurable, and speculative execution (Spectre) can amplify the signal.
3. **Secret-Independent Data Access**: Memory access addresses must not depend on secret values. Cache line access patterns reveal which addresses were accessed, leaking secret-dependent indices.

**Why source code analysis is insufficient**: The C compiler can transform constant-time source code into non-constant-time binary. The Clangover attack demonstrated this: Clang 15-18 compiled ML-KEM's constant-time `poly_frommsg` into a secret-dependent branch, enabling full key recovery in minutes. The same C code is constant-time under one compiler but leaking under another. Constant-time properties must be verified at the assembly/binary level for each target platform and compiler version.

**Why this keeps happening**: Most developers don't think about physical effects of their code. A `memcmp` comparison that returns early on mismatch is obviously correct (it gives the right answer) and obviously efficient (it doesn't do unnecessary work). But it leaks the position of the first mismatch through timing, potentially revealing a secret byte at a time. Constant-time programming requires deliberately writing *slower* code that does *unnecessary* work to prevent leakage.

## Principle 8: The Fault Sensitivity Principle

**If an attacker can cause a computation to produce a wrong result and compare it to a correct result, the difference reveals the secret key.**

Cryptographic algorithms have mathematical structure that relates inputs, outputs, and keys. This structure means that knowing both a correct output and a faulty output — where the fault affected a specific part of the computation — provides equations that constrain the key. With enough faulty outputs, the key can be fully determined.

**The fundamental question**: "If an attacker could cause one step of this computation to produce a wrong result, would comparing the wrong output to a correct output reveal the key?"

**How fault attacks work against specific algorithms**:

- **RSA with CRT**: RSA signing using the Chinese Remainder Theorem computes the signature modulo each prime factor separately, then combines. If a fault corrupts one of the two computations, the resulting signature is wrong modulo one prime but correct modulo the other. Given the faulty signature `s'` and any valid message, `gcd(s'^e - m, N)` reveals one prime factor, completely breaking the key. This requires only ONE faulty signature.

- **ECC scalar multiplication**: A fault during point doubling or addition can produce a point on a different curve (one with a different equation parameter `a` or `b`). The resulting "signature" or "shared secret" is computed on the wrong curve, and the relationship between the correct and wrong curves reveals information about the scalar (private key).

- **AES key schedule**: A fault during key expansion corrupts all subsequent round keys in a predictable way (since each round key is derived from the previous one). By comparing correct and faulty outputs, the attacker can determine which round was faulted and recover key material.

- **Signature verification bypass**: The simplest fault attack doesn't extract the key — it just skips the verification. A voltage glitch timed to the comparison instruction in `if (signature_valid) { accept; } else { reject; }` can cause the CPU to skip the branch, accepting any signature. This breaks firmware update verification (wolfBoot), certificate verification, and any authentication.

**This is primarily an embedded/physical-access threat**: Fault injection requires physical proximity to the device (to apply voltage glitches, EM pulses, or laser shots). It is most relevant for IoT devices, smartcards, HSMs, and any embedded deployment where the attacker can physically access the hardware. For server deployments behind locked doors, fault injection is typically not in the threat model — but for a library like wolfSSL that runs on bare-metal embedded systems, it absolutely is.

**Countermeasures in code**: Redundant computation (compute twice, compare), instruction flow verification (set flags before/after critical operations, check they were all set), randomized execution order, error detection codes on key material. These are implemented at the code level but defend against physical attacks.

## Applying the Principles During Investigation

When investigating a vulnerability report, systematically consider each principle:

1. **Oracle**: Does the reported code path create any observable difference based on secret values? Check error handling, timing, response patterns.
2. **Trust Boundary**: Is an attacker-controlled value used without validation? Trace the data flow from network input to the vulnerable operation.
3. **Semantic Gap**: Does the reported issue involve two components interpreting data differently? Check encoding, format parsing, type handling.
4. **Downgrade**: Can the reported behavior be used to force a weaker security option? Check negotiation logic, fallback behavior.
5. **Composition**: Does the issue arise from combining two operations? Check operation ordering, information flow between components.
6. **State Machine**: Does the report involve unexpected message sequences or protocol states? Check state validation.
7. **Physical Manifestation**: Does the code have secret-dependent branches, memory access patterns, or variable-time operations? First determine whether the data IS secret by tracing it to its origin (secret key vs public ciphertext vs constant). Then check constant-time properties at both source and assembly level.
8. **Fault Sensitivity**: Is the reported code vulnerable to producing usefully wrong outputs under fault conditions? Primarily relevant for embedded targets.
9. **Version Context**: If the reporter tested a specific version, trace whether the code path has changed between that version and HEAD. Line number shifts, merged PRs targeting the same function, and CVEs assigned to the same code area with fix versions between the reporter's version and HEAD are factual version-delta indicators.

The data surfaced from this analysis belongs in the **Attack Surface** and **Code Context** sections of the dossier — always as factual observations, never as assessments of whether the vulnerability is real or exploitable.
