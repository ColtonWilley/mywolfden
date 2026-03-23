# wolfSSL Build System

## configure.ac Gotchas

- `--enable-all` enables almost everything — individual `--disable` after
  it may not override. Always verify in configure.ac.
- `--enable-fips` forces specific algorithm sets regardless of other flags
- Order matters: later assignments override earlier ones
- **Always Grep configure.ac** before claiming a flag exists or doesn't

## FIPS Ordering Constraint

Algorithm flag setup that depends on FIPS state must be physically located
in configure.ac AFTER the FIPS setup block. FIPS setup sets version
variables and restricts algorithms — if your flag runs before FIPS setup,
the version gates haven't executed yet.

## IDE / user_settings.h Builds

For platforms without autoconf (STM32, ESP-IDF, Arduino, Keil, IAR):
- Create `user_settings.h` with `#define` equivalents of configure flags
- Include via `#define WOLFSSL_USER_SETTINGS` before any wolfSSL headers
- Templates in `IDE/` subdirectories
- Common mistake: defining both `HAVE_X` and `NO_X` for the same feature

## Common Macro-to-Flag Mapping

| Macro | Configure Flag |
|-------|---------------|
| `WOLFSSL_TLS13` | `--enable-tls13` |
| `WOLFSSL_DTLS` | `--enable-dtls` |
| `HAVE_ECC` | `--enable-ecc` |
| `OPENSSL_EXTRA` | `--enable-opensslextra` |
| `DEBUG_WOLFSSL` | `--enable-debug` |
| `HAVE_SNI` | `--enable-sni` |
| `WOLFSSL_STATIC_MEMORY` | `--enable-staticmemory` |
| `WOLFSSL_SMALL_STACK` | `--enable-smallstack` |
