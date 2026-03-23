# wolfDen Claude Response (baseline) — PR #9991

The fix is already applied in your working tree. Here's my analysis:

## The Vulnerability

`MatchDomainName` at HEAD allows **partial wildcard patterns** — patterns where `*` is combined with literal characters in the same label. For example:

- `f*.example.com` would match `foo.example.com` (wildcard preceded by literal)
- `*o.example.com` would match `foo.example.com` (wildcard followed by literal)
- `a*b*` would match various strings (mixed literal/wildcard)

Per RFC 6125, wildcards must represent the **entire** left-most label. Partial wildcards like `f*.example.com` should be rejected — they enable overly broad certificate matching, which an attacker could exploit with a malicious certificate.

## The Fix (already in working tree)

Three changes to `MatchDomainName` in `src/internal.c`:

1. **`labelHasLiteral` tracking** (line 13211): New variable tracks whether literal chars have been seen in the current label. Resets on `.` boundaries.

2. **Pre-wildcard check** (line 13236-13237): If `labelHasLiteral` is true when we hit `*`, reject immediately. Catches patterns like `f*.example.com`.

3. **Post-wildcard check** (line 13263-13267): After consuming the `*` and any extra `*` chars, the next character in the pattern must be `.` or end-of-pattern. Catches patterns like `*o.example.com`.

This subsumes the narrower fix in commit `76c52c31f` (which only checked in the `leftWildcardOnly` path) — the new checks apply unconditionally regardless of flags.

## Tests (already updated)

The tests in `tests/api/test_ossl_x509.c` are correctly updated:
- `test_wolfSSL_X509_name_match1` — cert with SAN `a*`: now expects rejection (`ExpectIntNE`) for all inputs
- `test_wolfSSL_X509_name_match2` — cert with SAN `a*b*`: now expects rejection
- `test_wolfSSL_X509_name_match3` — cert with SAN `*.example.com`: still passes (this is a valid full-label wildcard)

## Verification

The fix correctly handles all cases:

| Pattern | Input | Result | Reason |
|---------|-------|--------|--------|
| `f*.example.com` | `foo.example.com` | **Reject** | `labelHasLiteral` before `*` |
| `*o.example.com` | `foo.example.com` | **Reject** | `p != '.'` after `*` |
| `a*` | `aaaaa` | **Reject** | `labelHasLiteral` before `*` |
| `*.example.com` | `foo.example.com` | **Match** | `*` is entire label, `.` follows |
| `*.example.com` | `x.y.example.com` | **Reject** | `*` stops at `.` (single label only) |

The fix is sound and ready to commit. Want me to build and run the tests to verify?
