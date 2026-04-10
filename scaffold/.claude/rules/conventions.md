# wolfSSL Conventions

Things Claude cannot derive from reading a single file.

## Formatting (CI-Enforced)

- 4-space indent, no tabs — any tab in `.c`/`.h` fails CI
- C-style comments only: `/* comment */`, never `// comment`
- No trailing whitespace

## Memory and Error Patterns

- `XMALLOC(size, heap, DYNAMIC_TYPE_X)` / `XFREE` — never raw malloc
- `ForceZero(buf, len)` for any buffer that held secret material (keys,
  nonces, seeds). Never `XMEMSET` — compilers optimize it away.
- `mp_forcezero()` for bignums with private key material
- Functions return negative error codes on failure (see `error-crypt.h`)
- Crypto signing/key paths: sequential `if (ret == 0)` chains, not early
  returns — early returns skip `ForceZero`/`wc_FreeXxx` cleanup

## Input Validation at API Boundaries

Public `wc_*` and `wolfSSL_*` functions must validate buffer lengths before
`XMEMCPY`. Each `#ifdef` path that copies input must independently validate.

## Macro Registration

New `WOLFSSL_*`, `HAVE_*`, or `NO_*` macros must be registered in
`.wolfssl_known_macro_extras` in the repo root (LC_ALL=C sorted).
Unregistered macros fail the `check-source-text` CI check.

## Build System

- `configure.ac` ordering matters: FIPS setup block must precede algorithm
  flag setup (FIPS sets version variables that gate algorithms)
- Makefile recipes contain awk/sed scripts generating C code that reference
  struct types and field names — when renaming structs or fields, grep
  Makefile recipes for the old names
- `--enable-all` enables almost everything; individual `--disable` after
  it may not override — verify in configure.ac
