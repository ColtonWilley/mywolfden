---
paths:
  - "**/configure.ac"
  - "**/CMakeLists.txt"
  - "**/settings.h"
---

# Add Configure Flag

## When This Applies
Adding a new `--enable-*` or `--with-*` flag to the wolfSSL build system.

## Required Changes

1. **`configure.ac`** — `AC_ARG_ENABLE` + `AM_CFLAGS` + `AC_SUBST`.
   VERIFY: grep for a similar existing flag to match the pattern.
   NOTE: If the flag depends on FIPS state, place it AFTER the FIPS
   setup block (FIPS sets version variables that gate algorithms).

2. **`CMakeLists.txt`** — Equivalent CMake option.
   VERIFY: grep for the same feature name in CMakeLists.txt.

3. **`.wolfssl_known_macro_extras`** — Register any new `WOLFSSL_*`,
   `HAVE_*`, or `NO_*` macros (LC_ALL=C sorted).

4. **IDE templates** — If the feature is commonly used on embedded:
   update `examples/configs/user_settings_all.h` or relevant template.
   VERIFY: check if similar features have template entries.

## Scope Boundaries

- `--enable-all` enables almost everything; individual `--disable` after
  it may not override. Always verify override behavior in configure.ac.
