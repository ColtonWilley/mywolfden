---
paths:
  - "**/wolfcrypt/src/port/**"
  - "**/stm32*"
  - "**/esp32*"
  - "**/hmac.c"
  - "**/aes.c"
  - "**/sha*.c"
---

# Add Hardware Acceleration Backend

## When This Applies
Adding a new HW acceleration mode to an existing port (e.g., HW HMAC on
STM32, HW AES-GCM on a new SoC).

## Required Changes

1. **Port file** (`wolfcrypt/src/port/<vendor>/<chip>.c`) — ALL hardware-
   specific functions belong here: algo mapping, peripheral control, key
   handling, register manipulation. NOT in the generic crypto source.
   VERIFY: confirm port file exists; check existing functions for patterns.

2. **Generic crypto file** (`wolfcrypt/src/hmac.c`, `aes.c`, etc.) — Add
   dispatch points using existing multi-backend state flags in the
   algorithm struct (e.g., `innerHashKeyed` sentinel values for HMAC).
   Look for how other backends (PKCS#11, CryptoCb) dispatch in the same
   file — follow that pattern.
   VERIFY: grep for existing backend dispatch in the target crypto file.

3. **Header** (`wolfssl/wolfcrypt/<algo>.h` or port header) — New struct
   fields, flag values, or port function declarations. Existing struct
   fields are often reused for alternate backends (e.g., `ipad` buffer
   repurposed for HW key storage) — check how other backends use the
   struct before adding new fields.

4. **Build guards** — Use dual macros: `#if defined(STM32_HASH) &&
   defined(STM32_HMAC)`, not single `#ifdef`. Hardware features are
   layered.

5. **`.wolfssl_known_macro_extras`** — Register any new macros.

## Scope Boundaries

- Hardware-specific code goes in port files, not in generic crypto source.
  If you're writing register manipulation in `hmac.c`, stop — it belongs
  in the port file.
- Prefer zero-overhead macro wrappers that reuse existing peripheral
  functions over separate implementations.
