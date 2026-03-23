# Cross-File Relationships

Relationships between files that aren't obvious from reading any single one.

## Two Separate Test Systems

wolfSSL has TWO independent test files with DIFFERENT conventions:

**wolfcrypt/test/test.c** — tests wolfCrypt primitives (ECC, RSA, AES, SHA):
- Error wrapping: `WC_NO_ERR_TRACE(expected_error)`
- Error encoding: `WC_TEST_RET_ENC_EC(ret)`
- Flow: `goto done` single-exit cleanup
- Guards: `#ifdef HAVE_COMP_KEY`, `#ifdef HAVE_ECC_CHECK_KEY`, etc.
- Negative tests for validation fixes go HERE (not in tests/api.c)

**tests/api.c** — tests TLS/SSL API (wolfSSL_connect, sessions, certs):
- Inline: `TEST_DECL(func)` — implement and register in api.c
- Grouped: `TEST_DECL_GROUP("group", func)` — implement in
  `tests/api/test_FEATURE.c`, declare in `test_FEATURE.h`
- Macros: `EXPECT_DECLS` / `ExpectIntEQ` / `EXPECT_RESULT()`

## Lookup Table Naming Conventions

`src/internal.c` has string-to-algorithm mapping tables with prefix
conventions. These tables are populated INDEPENDENTLY from internal
dispatch — supporting an algorithm internally doesn't mean it has a
table entry:

- `sig_names[]`: key-type prefix — `ECDSA-BRAINPOOL`, `RSA-PSS`, `ED25519`
- `cipher_names[]`, `sigalgs_list`: similar prefixed conventions
- When adding entries, match the existing prefix format for that key type

## Header/Source/Config Triples

Changes often need updates in multiple locations:
- **Error codes**: `wolfssl/wolfcrypt/error-crypt.h` (define) +
  `wolfcrypt/src/error.c` (string mapping)
- **Configure flags**: `configure.ac` (autoconf) + `CMakeLists.txt` (cmake)
- **New algorithms**: `wolfssl/wolfcrypt/<algo>.h` (header) +
  `wolfcrypt/src/<algo>.c` (impl) + `wolfcrypt/test/test.c` (test)
- **Public API**: `wolfssl/ssl.h` (decl) + `src/ssl.c` (impl) +
  `tests/api.c` (test) + `wrapper/` bindings if FFI-visible
