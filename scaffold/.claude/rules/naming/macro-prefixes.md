---
paths:
  - "**/.wolfssl_known_macro_extras"
  - "**/configure.ac"
  - "**/user_settings*.h"
---

# Macro Naming and Registration

## Prefix Conventions

- `WOLFSSL_*` — wolfSSL-specific feature flags
- `HAVE_*` — feature availability (usually set by configure)
- `NO_*` — feature exclusion (disables something)
- `WOLFCRYPT_*` — wolfCrypt-specific flags
- `WC_*` — wolfCrypt constants and helpers

## Registration Requirement

ALL new macros must be registered in `.wolfssl_known_macro_extras` in the
repo root. Entries are LC_ALL=C sorted. Unregistered macros fail CI
(`check-source-text` check).

VERIFY: after adding a new macro, grep `.wolfssl_known_macro_extras` to
confirm it's registered and properly sorted.

## Common Mistake

Defining both `HAVE_X` and `NO_X` for the same feature causes undefined
behavior. Check `configure.ac` for mutual exclusion before adding new
feature/exclusion pairs.
