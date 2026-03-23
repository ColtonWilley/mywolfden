# wolfSSL Coding Standards

## Formatting (CI-enforced)

- **4-space indent, no tabs** — any tab in `.c`/`.h` fails CI
- **C-style comments only** — `/* comment */`, never `// comment`
- **No trailing whitespace**

## Memory and Error Conventions

- Use `XMALLOC(size, heap, DYNAMIC_TYPE_X)` / `XFREE` — never raw malloc
- Functions return negative error codes on failure (see `error-crypt.h`)
- Cleanup pattern: `goto exit;` with resource freeing at the label

## Sensitive Data Cleanup Discipline

**`ForceZero` vs `XMEMSET`**: Use `ForceZero(buf, len)` for any buffer that
held secret material (private keys, nonces, seeds, shared secrets). Never
use `XMEMSET` — compilers may optimize it away. Similarly, `mp_forcezero()`
wipes bignum data from memory while `mp_clear()` only resets metadata —
use `mp_forcezero()` for any bignum that held private key material.

**Error propagation for cleanup safety**: In crypto signing/key paths,
prefer sequential `if (ret == 0)` chains over early `return` statements.
Early returns skip cleanup code (`ForceZero`, `wc_FreeXxx`), leaking
sensitive intermediates on the stack. The canonical pattern:
```c
if (ret == 0)
    ret = step_one();
if (ret == 0)
    ret = step_two();
/* cleanup always runs regardless of which step failed */
ForceZero(secret, sizeof(secret));
wc_FreeXxx(&obj);
return ret;
```

**Init return values must be checked**: `wc_InitRsaKey()`, `wc_ecc_init_ex()`,
and similar init functions can fail. Never use the object or call the
corresponding free function without first confirming init succeeded.

## Input Validation at API Boundaries

Public `wc_*` and `wolfSSL_*` functions must validate buffer lengths
before any `XMEMCPY`. When a function accepts `(data, len)` pairs and
copies into a fixed-size struct field, check `len <= sizeof(dest)` and
return `BAD_FUNC_ARG` before the copy. This applies to all backend
variants (`WOLFSSL_KCAPI_*`, `WOLF_CRYPTO_CB`, hardware ports) — each
`#ifdef` path that copies input must independently validate lengths.

## Macro Registration

New `WOLFSSL_*`, `HAVE_*`, or `NO_*` macros must be registered in
`.wolfssl_known_macro_extras` in the repo root (LC_ALL=C sorted).
Unregistered macros fail the `check-source-text` CI check.

## Test Registration

Tests live in two separate files with different conventions:

**`tests/api.c`** — TLS/SSL API tests:
- `TEST_DECL(func)` — inline test, function implemented in api.c
- `TEST_DECL_GROUP("group", func)` — grouped test in `tests/api/test_FEATURE.c`
  with declaration in `test_FEATURE.h`
- Uses `EXPECT_DECLS` / `ExpectIntEQ` / `EXPECT_RESULT()` macros

**`wolfcrypt/test/test.c`** — wolfCrypt algorithm tests:
- `WC_NO_ERR_TRACE(expected_error)` wraps calls expected to fail
- `WC_TEST_RET_ENC_EC(ret)` encodes error location
- `goto done` cleanup pattern with single exit point
- `#ifdef HAVE_*` guards for optional features
