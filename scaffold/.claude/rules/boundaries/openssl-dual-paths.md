---
paths:
  - "**/src/ssl.c"
  - "**/tests/api.c"
  - "**/tests/api/**"
---

# OpenSSL Compatibility Dual-Path Pattern

## The Rule

Features with both a native `wolfSSL_*` API and an `OPENSSL_EXTRA`
compatibility path need changes in both paths and separate tests for each.

## What This Means in Practice

- Native path: `wolfSSL_X509_*`, `wolfSSL_CTX_*`, etc.
- Compat path: `X509_VERIFY_PARAM`, `X509_get_ext_d2i`, etc.
  (via `OPENSSL_EXTRA` defines)

When adding a feature that has both paths:
1. Implement both the native and compat code paths
2. Write separate test functions in `tests/api.c` — one exercising
   the native API, one exercising the OpenSSL-compat API
3. Guard the compat test with `#ifdef OPENSSL_EXTRA`

## Extending Shared Helpers

When a new mode/variant extends an existing feature (e.g., IP matching
alongside domain matching), audit shared internal helper functions called
by the existing mode. They may need a new parameter to distinguish modes.
Check ALL callers of those helpers, not just the new code path.
