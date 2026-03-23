# wolfDen Claude Response (iter1) — PR #9991

Fix applied. Here's a summary:

**The vulnerability (zd#21354)**: When `WOLFSSL_LEFT_MOST_WILDCARD_ONLY` is set, `MatchDomainName` accepted patterns like `*domain.com` (wildcard not separated by `.` from the domain). This means a certificate with SAN `*evil.com` would match `evil.com` because the wildcard consumed zero characters and the literal suffix matched.

**The fix**: Added an early check inside the `leftWildcardOnly` block (line 13246) that rejects patterns where the character immediately after `*` is not `.`. This ensures only `*.domain.com` forms are accepted, not `*domain.com`.

**Defense in depth**: The current codebase already has a general post-wildcard dot check at line 13271 (`if (patternLen > 0 && p != '.') return 0`), but the new check exits earlier — before entering the inner loop that consumes extra `*` characters — providing an additional guard specifically for the `leftWildcardOnly` path.

**Tests**: The existing tests in `tests/api/test_ossl_x509.c` (test_wolfSSL_X509_name_match1 through test_wolfSSL_X509_name_match3) already cover partial wildcard patterns (`a*`, `a*b*`, `*.example.com`) and verify they're correctly rejected/accepted.
