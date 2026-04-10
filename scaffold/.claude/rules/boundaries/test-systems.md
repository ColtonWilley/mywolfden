---
paths:
  - "**/tests/api.c"
  - "**/tests/api/**"
  - "**/wolfcrypt/test/test.c"
  - "**/wolfcrypt/test/test.h"
---

# Test System Boundary

wolfSSL has TWO independent test systems. Using the wrong one is a
common mistake.

## wolfcrypt/test/test.c — Crypto Primitives
- Tests wolfCrypt operations: ECC, RSA, AES, SHA, HMAC, etc.
- Crypto callback testing, PKCS#11 key operations
- Error wrapping: `WC_NO_ERR_TRACE()`, `WC_TEST_RET_ENC_EC()`
- `goto done` cleanup pattern
- New functions need forward declarations in `test.h`

## tests/api.c — TLS/SSL API
- Tests TLS-level functionality: connections, sessions, certificates
- Full handshake integration tests (e.g., 24-combination ECH suite test)
- `TEST_DECL(func)` inline or `TEST_DECL_GROUP` in `tests/api/`
- `EXPECT_DECLS` / `ExpectIntEQ` / `EXPECT_RESULT()` macros

## The Rule

- Pure wolfCrypt changes (crypto callbacks, algorithm fixes) test in
  `test.c` only. Do NOT add companion `tests/api.c` changes.
- TLS-level changes (handshake, session, certificate API) test in
  `tests/api.c`.
- If a feature spans both layers, use both — but don't add api.c tests
  for wolfCrypt-only work.
