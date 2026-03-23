You are improving wolfDen — a domain knowledge base that wolfSSL developers load into Claude Code to get better assistance with wolfSSL development. The knowledge base consists of rules files in `.claude/rules/` covering platforms, products, crypto internals, build system, coding standards, and investigation methodology.

## Philosophy — Read This Carefully

**The goal is NOT to spoon-feed answers.** Do not inject information so that Claude "magically" knows the answer to this specific PR next time. That is cheating — it doesn't generalize and it bloats the context window.

**The goal IS to improve domain knowledge and technical reasoning** so that a developer using Claude Code with wolfDen loaded would organically arrive at better architectural decisions, find the right integration points faster, and follow wolfSSL patterns correctly. Think of it like onboarding documentation for a new engineer — not a cheat sheet for one specific task.

**Every token in the rules files costs attention.** Claude's context window is shared between the knowledge rules, the developer's conversation, and tool results from reading code. Bloating rules files with verbose content degrades Claude's ability to follow existing rules. A well-placed 2-line insight is better than a 20-line explanation.

**wolfDen helps developers, not support agents.** The knowledge should be framed as "here's how this subsystem works and how to implement against it" — not "here's how to investigate a customer issue." Think API patterns, build system conventions, integration points, `#ifdef` gate relationships, cross-module dependencies.

**Knowledge that increases confidence without increasing verification is NEGATIVE VALUE.** If wolfDen Claude performed worse than bare Claude, the most likely cause is that knowledge rules gave Claude false confidence — it "knew" how wolfSSL works and skipped actually reading the code, leading to hallucination. Before proposing new knowledge content, first consider whether the failure was caused by too much prescriptive guidance rather than too little domain knowledge. Sometimes the best improvement is making existing rules less prescriptive, not adding more rules.

## What Happened

### The PR Task
{{ pr_context }}

### Analysis Findings
{{ findings_json }}

### Root Causes
{{ root_causes_json }}

### wolfDen Advantage (or lack thereof)
{{ wolfden_advantage }}

## File Selection Guide

Choose the right file based on what knowledge was missing:

| Gap Type | Primary Target |
|----------|---------------|
| Missed companion files (tests, headers, wrappers) | CLAUDE.md (Change Scope), cross-file-relationships.md |
| Didn't know cross-file conventions (table naming, test patterns) | cross-file-relationships.md |
| Didn't understand the build system / configure flags | build-system.md, configure-dependencies.md |
| Didn't follow wolfSSL coding conventions | coding-standards.md |
| Missing platform-specific knowledge | platforms/<platform>.md |
| Missing product-specific knowledge | products/<product>.md |
| Didn't understand crypto internals | crypto/<relevant-topic>.md |
| Didn't know about integration patterns | integrations/<integration>.md |
| Didn't understand error handling patterns | error-taxonomy.md |
| Version-specific behavior caused confusion | version-gotchas.md |
| Missed embedded/RTOS constraints | embedded-integration-checklist.md |

**Priority**: Improvements that tell Claude WHERE ELSE to look (scope awareness,
cross-file relationships) are almost always more valuable than improvements that
tell Claude HOW to read code. Claude is already good at reading code — the value
is in knowing what other files are affected by a change.

## Current File Contents

{% for file_entry in relevant_files %}
### {{ file_entry.path }}
```
{{ file_entry.content }}
```
{% endfor %}

## When Domain Knowledge IS Appropriate

Adding specific technical knowledge is not "cheating" — sometimes it is exactly the right improvement. The distinction is **reusability**, not specificity.

**YES — add domain knowledge when:**
- The pattern applies across many PRs in the same subsystem (e.g., "all cryptoCb implementations must register via wc_CryptoCb_RegisterDevice and dispatch through the WOLF_CRYPTO_CB ifdef gate")
- It describes a general mechanism (how the PKCS#11 dispatch works, how configure flags map to `#define`s, how platform ports are structured in `IDE/`)
- A developer working on a DIFFERENT feature in the same subsystem would benefit from knowing this
- It documents relationships between components that aren't obvious from reading any single file (e.g., "adding a new TLS extension requires changes in internal.h, ssl.c, and the relevant handshake message handler in internal.c")

**NO — do not add domain knowledge when:**
- It describes the specific implementation of one PR (function names, exact code changes)
- It would only help if this exact feature were being re-implemented
- The information is easily discoverable by reading the code (e.g., "function X takes parameters Y and Z")

**The bar:** Would a developer working on a FRESH, DIFFERENT task in the same subsystem benefit from this knowledge? If yes, it belongs. If it only helps on tasks that look like this specific PR, it does not.

**Example — GOOD:** "When adding a new algorithm to the cryptoCb interface (cryptocb.c), follow the existing pattern: add a new case to the `wc_CryptoCb_*` dispatch function, define the callback info struct in wolfssl/wolfcrypt/cryptocb.h, and gate the entire implementation behind the algorithm's `HAVE_*` define AND `WOLF_CRYPTO_CB`. Check existing implementations like ECC or RSA for the pattern."

**Example — BAD:** "PR #9836 added ML-DSA support to PKCS#11 by creating MlDsa_xxx functions in wc_pkcs11.c and registering new CKM_* constants."

## Constraints

1. **No cheating.** Do not inject PR-specific facts. Ask: "If this PR had never existed, would this knowledge still be useful to a developer in this area?"
2. **Improve reasoning, not answers.** Add patterns, architectural guidance, and investigation strategies — not specific solutions.
3. **Small and targeted.** Max 2 proposals. Prefer 2-5 line additions over paragraphs. A concise insight that fits naturally into an existing section is ideal.
4. **Additive by default.** Add content, never delete unless factually wrong.
5. **Consider context budget.** If the target file is already large, your addition must be especially concise.

## Output

Respond with ONLY valid JSON (no markdown fencing, no commentary):

{
  "proposals": [
    {
      "file": "scaffold/.claude/rules/...",
      "action": "append_section|insert_after|replace_lines|new_file",
      "anchor": "Text to find for insert_after, or section header for replace_lines. Not used for append_section or new_file.",
      "content": "The content to add.",
      "reasoning": "Why this helps developers working in this subsystem — not just for this PR."
    }
  ]
}

ACTIONS:
- `append_section`: Append content to end of file.
- `insert_after`: Find anchor text, insert content immediately after.
- `replace_lines`: Replace content under a section header. Use only for factually wrong content.
- `new_file`: Create a new file (must be under scaffold/.claude/rules/).
