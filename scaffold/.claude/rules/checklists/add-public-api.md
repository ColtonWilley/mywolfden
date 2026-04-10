---
paths:
  - "**/wolfssl/ssl.h"
  - "**/src/ssl.c"
  - "**/tests/api.c"
  - "**/tests/api/**"
---

# Add Public API Function

## When This Applies
Adding a new `wolfSSL_*` or `wc_*` function to the public API.

## Required Changes

1. **Declaration**: `wolfssl/ssl.h` (TLS API) or
   `wolfssl/wolfcrypt/<algo>.h` (wolfCrypt API).
   VERIFY: grep for a similar existing function to find the right header.

2. **Implementation**: `src/ssl.c` (TLS) or `wolfcrypt/src/<algo>.c`.
   VERIFY: read the analog function for error handling and guard patterns.

3. **Test**: `tests/api.c` for TLS API, `wolfcrypt/test/test.c` for
   wolfCrypt API. If the feature has both native and `OPENSSL_EXTRA`
   paths, write TWO test functions — one for each path.

4. **Input validation**: Validate buffer lengths before any `XMEMCPY`
   into fixed-size fields. Return `BAD_FUNC_ARG` on failure. Each
   `#ifdef` path must validate independently.

5. **Bindings**: Check `wrapper/` if the API is FFI-visible.

## Scope Boundaries

- API additions to `ssl.h` test in `tests/api.c`.
- Algorithm additions to wolfCrypt headers test in `wolfcrypt/test/test.c`.
- Do not mix the two test files for a single feature.
