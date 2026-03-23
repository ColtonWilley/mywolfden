---
paths:
  - "repos/osp/**/strongswan/**"
---

# strongSwan — External Platform Summary

## Current State

- **Latest stable version:** 6.0.5 (as of configure.ac: `AC_INIT([strongSwan],[6.0.5dr1])`)
- **wolfSSL plugin status:** Active, maintained, compatible with wolfSSL FIPS module as of 6.0.2
- **Notable recent changes relevant to wolfSSL:**
  - 6.0.2: wolfssl plugin confirmed compatible with wolfSSL's FIPS module
  - 6.0.3: MD2 support removed (affects hash algorithm availability)
  - 6.0.3: Plugin version matching enforced — only plugins with matching version numbers are loaded
- **Build system:** Autotools (`configure.ac` + `Makefile.am`); CMake not used
- **Primary IKE daemon:** `charon`; configuration via `swanctl` / vici interface

---

## Architecture

### Component Overview

```
swanctl (CLI) ──vici──► charon (IKE daemon)
                              │
                    ┌─────────┴──────────┐
                    │   libcharon        │  IKEv2 state machine, SA management
                    └─────────┬──────────┘
                              │
                    ┌─────────┴──────────┐
                    │  libstrongswan     │  Crypto abstraction, cert handling
                    └─────────┬──────────┘
                              │
                    ┌─────────┴──────────┐
                    │  Plugin layer      │  wolfssl, openssl, pkcs11, etc.
                    └────────────────────┘
```

### Crypto Plugin Architecture

- `libstrongswan` defines abstract crypto interfaces (`aead_t`, `hasher_t`, `signer_t`, `diffie_hellman_t`, etc.)
- Plugins register implementations of these interfaces with the crypto factory
- The wolfssl plugin is one of several interchangeable crypto backends (alongside openssl, gcrypt, botan)
- Plugin selection is priority-based; multiple crypto plugins can coexist, with the highest-priority plugin winning for a given algorithm

### IKEv2 Authentication Flow (relevant to wolfSSL)

- Certificate loading: `swanctl --load-creds` → charon credential manager
- Certificate validation: handled via `libstrongswan` certificate/credential abstractions
- IKEv2 AUTH payload signing/verification: uses registered public/private key implementations from the active crypto plugin
- EAP methods (e.g., EAP-TLS) may invoke separate TLS stack — **not** the wolfssl crypto plugin directly

---

## wolfSSL Integration Notes

### Plugin Location

```
src/libstrongswan/plugins/wolfssl/
```

### Build Configuration

Enable the wolfssl plugin at configure time:
```bash
./configure --enable-wolfssl
```

The plugin uses `pkg-config` or direct library detection for wolfSSL. Verify detection in `configure.ac` output. If wolfSSL is installed to a non-standard path:
```bash
./configure --enable-wolfssl \
  CPPFLAGS="-I/path/to/wolfssl/include" \
  LDFLAGS="-L/path/to/wolfssl/lib"
```

### wolfSSL Build Requirements

The plugin conditionally compiles based on wolfSSL's `options.h` feature flags. Required wolfSSL build options depend on which algorithms are needed:

| Feature | Required wolfSSL define |
|---|---|
| AES-GCM AEAD | `HAVE_AESGCM` + `!NO_AES` |
| AES-CCM AEAD | `HAVE_AESCCM` + `!NO_AES` |
| ChaCha20-Poly1305 | `HAVE_CHACHA` + `HAVE_POLY1305` |
| EC keys/DH | `HAVE_ECC` |
| Ed25519/Ed448 | `HAVE_ED25519` / `HAVE_ED448` |
| Classic DH | `!NO_DH` |
| Hashing | `!NO_SHA`, `!NO_SHA256`, `HAVE_SHA512`, etc. |

### Header Inclusion Order — Critical

`wolfssl_common.h` must be included first in every plugin source file. It:
1. Undefines conflicting macros (`AES_BLOCK_SIZE`, `CAMELLIA_BLOCK_SIZE`, `DES_BLOCK_SIZE`, `RSA_PSS_SALT_LEN_DEFAULT`) that collide between strongSwan and wolfSSL
2. Remaps `PARSE_ERROR` → `WOLFSSL_PARSE_ERROR` to avoid enum conflicts
3. Handles `WOLFSSL_USER_SETTINGS` vs `wolfssl/options.h` inclusion
4. Disables the wolfSSL OpenSSL compatibility layer (`#define WOLFSSL_OPENSSL_H_`) to prevent symbol conflicts

**If `wolfssl_common.h` is not included first, expect macro redefinition errors or silent behavioral bugs.**

### FIPS Module Compatibility

- Supported as of strongSwan 6.0.2
- `wolfssl_common.h` contains FIPS-specific conditional compilation blocks
- When building against a FIPS wolfSSL, ensure the wolfSSL library itself is the FIPS-validated build; the plugin adapts automatically via `HAVE_FIPS` define

### User Settings vs options.h

The plugin supports both wolfSSL build styles:
```c
#ifndef WOLFSSL_USER_SETTINGS
    #include <wolfssl/options.h>
#endif
#include <wolfssl/wolfcrypt/settings.h>
```
If using `WOLFSSL_USER_SETTINGS`, define it before compilation and ensure `user_settings.h` is on the include path.

### Common Integration Issues

| Symptom | Likely Cause |
|---|---|
| Plugin fails to load at runtime | Version mismatch between plugin and charon (enforced since 6.0.3) |
| Algorithm not available / fallback to other plugin | Required wolfSSL feature not compiled in (check `options.h`) |
| Macro redefinition compile errors | `wolfssl_common.h` not included first, or OpenSSL compat layer active |
| AEAD operations fail | Salt/IV length mismatch; GCM uses 4-byte salt + 8-byte IV per RFC 4106 |
| EC key operations fail | wolfSSL built without `HAVE_ECC` |
| FIPS self-test failure at startup | wolfSSL FIPS module not properly initialized before plugin use |
| `PARSE_ERROR` compile conflict | Missing `wolfssl_common.h` include or include order wrong |
| OpenSSL compat symbols conflicting | `WOLFSSL_OPENSSL_H_` guard not effective — check include order |

### Algorithm Coverage by Source File

| File | Algorithms |
|---|---|
| `wolfssl_aead.c` | AES-GCM, AES-CCM, ChaCha20-Poly1305 |
| `wolfssl_crypter.c` | Block ciphers (AES-CBC, 3DES, Camellia) |
| `wolfssl_hasher.c` | SHA-1, SHA-2 family, MD5 |
| `wolfssl_diffie_hellman.c` | MODP DH groups |
| `wolfssl_ec_diffie_hellman.c` | ECDH (P-256, P-384, P-521) |
| `wolfssl_ec_private_key.c/h` | ECDSA private key ops |
| `wolfssl_ec_public_key.c/h` | ECDSA public key / verification |
| `wolfssl_ed_private_key.c/h` | Ed25519/Ed448 signing |
| `wolfssl_ed_public_key.c/h` | Ed25519/Ed448 verification |

---

## Key Files

### Plugin Source

```
src/libstrongswan/plugins/wolfssl/
├── wolfssl_common.h          # Must-include-first: macro fixes, options.h handling
├── wolfssl_aead.c/h          # AEAD (AES-GCM, AES-CCM, ChaCha20-Poly1305)
├── wolfssl_crypter.c/h       # Symmetric block ciphers
├── wolfssl_hasher.c/h        # Hash functions
├── wolfssl_diffie_hellman.c/h        # MODP DH
├── wolfssl_ec_diffie_hellman.c/h     # ECDH
├── wolfssl_ec_private_key.c/h        # ECDSA private
├── wolfssl_ec_public_key.c/h         # ECDSA public
├── wolfssl_ed_private_key.c/h        # EdDSA private
├── wolfssl_ed_public_key.c/h         # EdDSA public
└── Makefile.am               # Build rules for the plugin
```

### Build System

```
configure.ac                  # --enable-wolfssl flag, library detection
```

### Runtime Configuration

```
/etc/swanctl/swanctl.conf     # Connection definitions, auth methods
/etc/swanctl/x509/            # End-entity certificates (PEM)
/etc/swanctl/x509ca/          # CA certificates
/etc/swanctl/private/         # Private keys
/etc/strongswan.conf          # Daemon-level config, plugin load order/priority
```

### Daemon and Plugin Loading

```
/usr/lib/ipsec/plugins/libstrongswan-wolfssl.so   # Compiled plugin (typical path)
/etc/strongswan.conf                               # Plugin priority configuration
```

Plugin priority in `strongswan.conf` (higher = preferred):
```
libstrongswan {
    plugins {
        wolfssl {
            load = yes
        }
    }
}
```

### Debugging Plugin Loading

Run charon with increased verbosity to confirm wolfssl plugin loads and which algorithms it registers:
```bash
charon --debug-all 4
# or via swanctl
swanctl --log
```
Check for lines referencing `wolfssl` plugin registration and algorithm provider conflicts with other loaded crypto plugins (e.g., if both `openssl` and `wolfssl` are enabled).
