---
paths:
  - "**/error-crypt.h"
  - "**/error-ssl.h"
  - "**/error.c"
---

# Add Error Code

## When This Applies
Adding a new wolfSSL or wolfCrypt error code.

## Required Changes

1. **Define**: `wolfssl/wolfcrypt/error-crypt.h` (wolfCrypt) or
   `wolfssl/error-ssl.h` (SSL/TLS).
   VERIFY: read the existing enum to find the next available value.

2. **String mapping**: `wolfcrypt/src/error.c` — add the human-readable
   string for the new error code.
   VERIFY: grep for an adjacent error code to find the switch/array entry.

Both files must be updated — a define without a string mapping will
produce "unknown error" in debug output.
