# Bare Claude Response — PR #9991

That logic at line 13386 checks if `buf[0] == '*'` to detect wildcard patterns. This still works correctly — `*.example.com` starts with `*` and will trigger the wildcard failure path if it doesn't match. Partial wildcards like `a*` won't trigger this (they start with `a`), which is fine since they'll just be treated as non-matching literals.

Here's a summary of the changes:

## Changes

### Problem
`MatchDomainName()` in `src/internal.c` allowed **partial wildcard labels** — patterns like `a*`, `f*.example.com`, `*o.example.com`, or `a*b*` where `*` shares a label with other literal characters. Per RFC 6125 Section 6.4.3, wildcards should only be valid when `*` constitutes the **entire** left-most label (e.g., `*.example.com`).

This allowed certificates with overly broad SAN patterns to match domains they shouldn't.

### Fix (`src/internal.c`)
Two checks added to `MatchDomainName()`:

1. **Pre-wildcard check** (line 13236): Track whether literal characters have been seen in the current label via `labelHasLiteral`. If `*` appears after a literal (e.g., `f*`), immediately reject.

2. **Post-wildcard check** (line 13266): After consuming `*`, verify the next pattern character is `.` or end-of-pattern. Patterns like `*o.example.com` (suffix wildcards) are rejected.

Valid patterns like `*.example.com` are unaffected — the `*` is the first and only character in its label, followed by `.`.

### Test updates (`tests/api/test_ossl_x509.c`)
- `test_wolfSSL_X509_name_match1`: `a*` patterns now always fail to match (previously matched without `WOLFSSL_LEFT_MOST_WILDCARD_ONLY`)
- `test_wolfSSL_X509_name_match2`: `a*b*` patterns now always fail to match
- `test_wolfSSL_X509_name_match3`: `*.example.com` tests unchanged (valid full-label wildcard)
