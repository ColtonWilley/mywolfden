# Improvement Proposal: PR #9935, Iteration 1

**File:** `scaffold/.claude/rules/discovered-patterns.md`
**Action:** `append_section`
**Anchor:** `N/A`

## Reasoning
Developers mirroring an existing function (e.g., adding IP SAN checks alongside hostname checks) naturally write one test. The convention of one test per code path per compile branch is not documented anywhere and is easy to miss, especially for features forked at OPENSSL_EXTRA, HAVE_*, or WOLFSSL_* boundaries.

## Proposed Content
```

## Forked Code Paths Require Forked Tests

When a feature is split across a compile flag (e.g., `#ifdef OPENSSL_EXTRA` / `#ifndef OPENSSL_EXTRA`), wolfSSL writes a separate test function for each path, each gated by its own guard macro. One test exercising one path is insufficient — the other path is untested and may silently break. Apply this pattern to any feature whose implementation diverges at a compile-time boundary.
```
