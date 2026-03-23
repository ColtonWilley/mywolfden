---
paths:
  - "**/VULNERABILITIES*"
  - "**/SECURITY*"
---

# Security Vulnerability Handling

## wolfSSL Security Advisory Page

wolfSSL publishes security advisories at: https://www.wolfssl.com/docs/security-vulnerabilities/

Each advisory includes:
- CVE ID (when assigned)
- Severity (Critical/High/Medium/Low)
- Description of the vulnerability
- Time to fix
- Fixed version
- Link to GitHub changelog

wolfSSL Inc. is a CNA (CVE Numbering Authority) and can assign CVE IDs directly for wolfSSL product vulnerabilities.

## Common Vulnerability Report Patterns

### Reports That Are Typically Valid
- Timing side-channel attacks on cryptographic operations (constant-time violations)
- Buffer overflows/underflows in parsing functions (TLS handshake, X.509 certificates, ASN.1)
- Memory safety issues (use-after-free, double-free, null pointer dereference) in protocol state machines
- Fault injection attacks on cryptographic operations (especially on embedded/ARM targets)
- Missing bounds checks on network-received length fields
- PKCS#7/CMS parsing vulnerabilities (heap reads/writes on malformed input)

### Reports That Are Frequently Invalid
- **Static analysis noise**: Tool findings that report theoretical paths not reachable in practice (e.g., a "null deref" on a pointer that was checked 3 lines earlier in a branch the tool didn't follow)
- **Compile-time configuration blindness**: Reports based on reading code without understanding that wolfSSL's extensive `#ifdef` system means many code paths are disabled by default. The reporter sees vulnerable-looking code but it's behind `--enable-something` that isn't in default builds.
- **Test/example/debug code**: "Vulnerabilities" in test harnesses, example programs, or debug-only paths that are never compiled into production builds
- **Bounded integer overflows**: Integer overflow reports in size calculations that are bounded by earlier validation (e.g., `size * 2` where `size` was already validated to be < MAX/2)
- **OpenSSL compatibility confusion**: Reports confusing wolfSSL's API behavior with OpenSSL's — the compatibility layer has intentional differences
- **LLM-generated reports**: Plausible-sounding vulnerability descriptions that don't correspond to actual code. These often describe functions that don't exist, or describe behaviors that the code doesn't exhibit. Key tells: overly generic descriptions, function names that are close-but-not-quite, inability to provide a specific PoC
- **#ifdef-gated features**: Reports about code that is behind `#ifdef` guards for features not enabled in standard builds. Always check `settings.h` / `user_settings.h` defaults.

### Key Triage Signals
- **Fenrir scanner history**: If Fenrir already scanned the reported code area, its finding status (open, false_positive, fixed) provides historical context
- **Version context**: Many reports are against old versions where the issue was already fixed. Check git_log and github_lookup for fix PRs and release tags.
- **Build configuration**: Check whether the reported code is actually compiled in a default build. Key files: `wolfssl/wolfcrypt/settings.h`, `configure.ac`, project-specific `user_settings.h`
- **Attack prerequisites**: What access does the attacker need? Network-reachable (most critical), authenticated, local, or physical?
- **Reachability from external input**: Even if a function has a bug, can an external attacker actually reach it with controlled input? Trace from the TLS/protocol entry point through to the function.
- **Standards compliance**: When the reported code area implements a documented standard (NIST SP 800-90A, FIPS 140-3, RFC 8446, etc.), the specification defines expected behavior. Deviations from spec are stronger signals than general "this looks wrong" claims. Compliance with spec is a strong (but not absolute) counter-signal.

## Version-Comparative Analysis Framework

When a reporter tests against a specific version (e.g., "wolfSSL 5.8.4") and the repository HEAD contains different code, the version delta is a critical factual finding. Many reports target older versions where the issue has already been fixed. Determining whether the reported issue exists on HEAD requires systematic comparison — and the result is a technical fact chain, not an unresolved question.

### Evidence Indicators That Code Changed Between Versions

**Line number shifts**: When the reporter references specific line numbers (from a stack trace, debugger output, ASan trace, or source listing) and those lines contain different code on HEAD, the file was modified between versions. State both: "Reporter references [function] at [file:line] in v[X]. On HEAD, line [N] contains [different code]. The function was modified between these versions."

**Merged PRs touching the reported code**: `git_log` and `github_lookup` may reveal PRs that modified the reported function or file after the reporter's version tag. For each such PR: state the PR number, title, merge date, and which release tag includes it. When the PR title or description mentions the reported vulnerability type (e.g., "rewrite ECH handling," "fix buffer overflow in X," "add bounds checking to Y"), note the match between the PR's stated purpose and the reporter's finding.

**Assigned CVEs targeting the same code**: When `cve_lookup` returns CVEs that reference the same function or code area, and those CVEs list a "fixed version" that falls between the reporter's version and HEAD, this is a version delta indicator. State: "CVE-YYYY-XXXX targets [same function/area], fixed in v[Y]. Reporter tested v[X]. v[X] predates v[Y]."

**Structural code differences**: When the function's control flow, bounds checking, or core logic on HEAD differs substantially from the reporter's description — new validation checks added, loops restructured, entire blocks rewritten — this indicates a substantive code change, not just cosmetic edits. State the structural differences as factual observations.

### Presenting Version Delta Findings

Version delta evidence is a multi-step technical fact chain — each step (reporter's stated version, merged PR date, CVE fix version, code comparison) is independently verifiable from git history, GitHub, and NVD. It belongs in the **Code Context** section of the dossier, NOT in Unresolved Questions.

When multiple indicators converge (line shifts + merged PR + assigned CVE), present them together as a connected factual chain:

> "The reporter tested v[X] [report]. PR #NNN ([title]) modified [function] and was merged on [date] [github_lookup]. CVE-YYYY-XXXX, which targets [same area], lists v[Y] as the fixed version [cve_lookup]. v[X] predates v[Y]. On HEAD, [function] at [file:line] contains [bounds check / validation / restructured logic] that differs from the reporter's description [code observation]."

Each step is verifiable. The engineer reads the chain and determines whether the reporter's specific finding has been addressed.

### When the Version Delta Is Inconclusive

If the code changed but the change doesn't clearly address the reporter's specific finding (e.g., a PR rewrote the function for different reasons and the reporter's bug may or may not have been caught incidentally), state what is known and what is not. The version delta evidence still belongs in Code Context — with a note in Unresolved Questions about what would resolve the ambiguity (e.g., "Testing the reporter's PoC against HEAD would confirm whether the v5.8.4 issue reproduces on current code").

## Multi-Condition Prerequisite Chain Analysis

Some vulnerabilities require multiple independent conditions to all be true simultaneously for exploitation. When investigation reveals such a chain, presenting each condition with its factual context — including relevant published standards — helps the engineer assess the practical scope.

### Methodology

1. **List each prerequisite as a separate numbered item** with its source (code guard, protocol specification, configuration flag, infrastructure dependency)
2. **For each prerequisite, surface factual prevalence context** available from published standards and specifications:
   - Is the condition required or prohibited by a current industry standard? Cite the standard, section, and effective date.
   - Is the condition gated by a build flag with a known default state? State the default.
   - Does the condition require specific infrastructure (trusted CA cooperation, specific server configuration, specific client behavior)?
3. **Present the chain**: "The reported issue requires ALL of the following conditions: [numbered list]. Condition N is gated by [standard / build flag / infrastructure requirement]."

### Standards as Factual Prevalence Anchors

When a prerequisite involves a practice that is required or prohibited by a published standard (RFC, CA/Browser Forum Baseline Requirements, NIST SP, FIPS), citing the specific standard and section provides factual context about the ecosystem. This is data about what the ecosystem requires — not an assessment of likelihood.

Examples of factual standards citations:
- "RFC 6125 Section 6.4.4 states that clients SHOULD NOT seek a match for a reference identifier of CN-ID when the presented identifiers include a DNS-ID" — factual statement about the standard's recommendation
- "CA/Browser Forum Baseline Requirements Section 7.1.4.2.1 has required the inclusion of at least one Subject Alternative Name in all publicly-trusted certificates since 2012-07-01" — factual statement about industry requirements
- "NIST SP 800-131A Revision 2 (2019) disallows RSA key sizes shorter than 2048 bits for all purposes" — factual statement about NIST requirements
- "FIPS 203 Section 4.2.1 specifies the Compress function as a mathematical operation; the standard does not mandate constant-time implementation" — factual statement about what the standard does and does not require

The standard citation provides the engineer with ecosystem context. The engineer evaluates how the citation applies to the specific report.

### Presentation Format

When the dossier's Attack Surface section identifies multi-condition prerequisites, present them as a connected chain rather than isolated bullets:

> "The reported attack requires ALL of the following conditions:
> 1. A name-constrained subordinate CA must exist with permitted DNS constraint `.example.com` [code: ConfirmNameConstraints(), asn.c:NNNN]
> 2. That CA must issue a certificate with the target hostname placed solely in Subject CN [attack description]
> 3. That certificate must contain NO Subject Alternative Names extension [attack description]
> 4. The relying party must match hostnames against Subject CN when no SANs are present [wolfSSL behavior: CheckForAltNames() falls through to CN matching when altNames is NULL, ssl.c:NNNN]
>
> Condition 3: CA/Browser Forum Baseline Requirements Section 7.1.4.2.1 has required SANs in all publicly-trusted certificates since 2012-07-01 [standard reference]. Modern CA tooling (certbot, OpenSSL CA, step-ca) includes SANs by default [ecosystem context]."

## Fenrir Integration

Fenrir (fenrir.wolfssl.com) is wolfSSL's automated security scanner that performs weekly code reviews across all wolfSSL projects.

### Scan Coverage
- 14 projects across 38 scan targets
- Review types: security, bugs, compliance, CI/CD
- Scans run weekly (Sunday) with daily pruning to verify fixes

### Finding Lifecycle
1. **open** — Newly discovered by scanner, not yet reviewed
2. **assigned** — Claimed by an engineer for investigation
3. **false_positive** — Reviewed by an engineer and determined NOT to be a real vulnerability. This is a strong signal but not absolute — the engineer may have had different context.
4. **fixed** — Was a real issue, now resolved. Includes resolved_at date and resolved_by.
5. **wont_fix** — Acknowledged as real but accepted (e.g., acceptable risk, not exploitable in practice)
6. **duplicate** — Same as another finding (linked via duplicate_of field)

### What Fenrir Findings Include
Via the known-issues API: finding ID, severity, file_location, function_name, title, status.
Via the web UI (requires login): full description, code_snippet, recommendation, category, history.

### Grace Period
Recently fixed findings remain visible in search results for ~4 weeks after being resolved. This prevents re-reporting regressions.

## NVD / CVE Data

The National Vulnerability Database (NVD) at nvd.nist.gov provides:
- CVSS scoring (severity, attack vector, complexity, impact) — versions 2.0, 3.0, 3.1, 4.0
- CWE classifications (vulnerability type taxonomy, e.g., CWE-120 for buffer overflow)
- Affected version ranges via CPE matching
- References to patches, advisories, and exploit information

wolfSSL's CPE vendor name is "wolfssl" and products include "wolfssl", "wolfcrypt", "wolfssh", etc.

### CVSS Score Interpretation
- **9.0-10.0 Critical**: Remote code execution, no authentication required
- **7.0-8.9 High**: Significant impact, may require some conditions
- **4.0-6.9 Medium**: Moderate impact, often requires specific conditions or limited scope
- **0.1-3.9 Low**: Minor impact, often requires local/physical access

### Key CVSS Vector Components
- **AV (Attack Vector)**: Network (most severe) > Adjacent > Local > Physical (least severe)
- **AC (Attack Complexity)**: Low (easy to exploit) vs. High (requires specific conditions)
- **PR (Privileges Required)**: None (most severe) > Low > High
- **UI (User Interaction)**: None (most severe) > Required

## wolfSSL's Historical CVE Categories

Based on ~93 filed CVEs, wolfSSL vulnerabilities have historically fallen into these categories:

- **TLS protocol implementation**: Handshake state machine flaws, extension parsing, protocol downgrade attacks
- **Certificate/X.509 parsing**: ASN.1/DER buffer overflows, chain validation bypasses, constraint checking errors
- **Cryptographic side-channels**: Timing attacks on RSA/ECC/DSA, cache-based attacks, constant-time violations
- **Memory safety in crypto**: Buffer overflows in AES-GCM, ChaCha20-Poly1305, PKCS#7/CMS operations
- **Post-quantum**: Fault injection on ML-KEM/ML-DSA Keccak expansion (newer, e.g., CVE-2026-3503)
- **Embedded/ARM specific**: Fault injection, stack overflow on constrained devices, hardware port issues
- **ECH (Encrypted Client Hello)**: Stack buffer overflows from oversized ECH configs (newer)

### Severity Distribution (approximate from NVD)
- Critical: ~17%
- High: ~23%
- Medium: ~48%
- Low: ~12%
