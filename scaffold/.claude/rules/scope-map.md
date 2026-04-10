# Companion-File Scope Map

Changes in one file often require coordinated changes elsewhere.

## Error Codes
- Define: `wolfssl/wolfcrypt/error-crypt.h`
- String mapping: `wolfcrypt/src/error.c`

## Configure Flags
- Autoconf: `configure.ac`
- CMake: `CMakeLists.txt`

## New wolfCrypt Algorithms
- Header: `wolfssl/wolfcrypt/<algo>.h`
- Implementation: `wolfcrypt/src/<algo>.c`
- Test: `wolfcrypt/test/test.c`
- Test header: `wolfcrypt/test/test.h` (forward declarations for new
  test functions — external callers in `IDE/` include this)

## Public SSL/TLS API
- Declaration: `wolfssl/ssl.h`
- Implementation: `src/ssl.c`
- Test: `tests/api.c`
- Bindings: `wrapper/` if FFI-visible

## Two Test Systems (Different Conventions)

**`wolfcrypt/test/test.c`** — wolfCrypt primitives (ECC, RSA, AES, SHA):
- `WC_NO_ERR_TRACE(expected_error)` wraps expected failures
- `WC_TEST_RET_ENC_EC(ret)` encodes error location
- `goto done` single-exit cleanup
- Negative tests and crypto-layer validation go HERE

**`tests/api.c`** — TLS/SSL API (connect, sessions, certs):
- `TEST_DECL(func)` inline, or `TEST_DECL_GROUP("group", func)` grouped
  in `tests/api/test_FEATURE.c` with `test_FEATURE.h`
- `EXPECT_DECLS` / `ExpectIntEQ` / `EXPECT_RESULT()` macros
- TLS-level integration tests go HERE

## Dual-Path APIs (Native + OPENSSL_EXTRA)

Features with both a native `wolfSSL_*` API and an OpenSSL-compat path
need separate test functions in `tests/api.c` — one for native, one for
the compat path.

## Lookup Tables in internal.c

`sig_names[]`, `cipher_names[]`, `sigalgs_list` are populated independently
from internal dispatch. Supporting an algorithm internally does NOT mean it
has a table entry. When adding entries, match the existing prefix format.
