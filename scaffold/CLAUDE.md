# wolfDen

## How to Use This Environment

Your primary tool is **reading the actual code**. Read the target function,
its callers, and analogous functions nearby. The code around your target
contains the pattern you need to follow.

`.claude/rules/` contains scaffolding — not reference material:
- **`discipline.md`** — Verification mandates (always loaded)
- **`conventions.md`** — wolfSSL coding/build conventions (always loaded)
- **`scope-map.md`** — Companion-file pairs (always loaded)
- **`checklists/`** — Task-type checklists (loaded when touching relevant files)
- **`boundaries/`** — Scope disambiguation (loaded when touching relevant files)
- **`naming/`** — Naming conventions (loaded when touching relevant files)

If a checklist or boundary file loads, use it as a starting point — then
verify each item against the actual code. If the code shows a different
pattern than what the scaffolding suggests, follow the code.

`knowledge/` contains deep domain reference files (crypto patterns, platform
constraints, integration gotchas). These are **never auto-loaded** — consult
the index below and read a file only when your task matches its trigger.

@knowledge/index.md

## Active Repositories

@.repos-context.md

## Repository Layout (wolfSSL core)

```
wolfssl/
├── src/                    # TLS/DTLS protocol implementation
│   ├── internal.c          # Core TLS state machine
│   ├── ssl.c               # Public API layer
│   ├── tls.c / tls13.c     # TLS version-specific code
│   └── dtls.c / dtls13.c   # DTLS implementation
├── wolfcrypt/src/          # Cryptographic primitives
│   ├── asn.c               # ASN.1/X.509 parsing
│   ├── rsa.c / ecc.c       # Public key algorithms
│   ├── aes.c / sha256.c    # Symmetric / hash algorithms
│   ├── random.c            # DRBG / entropy
│   └── port/               # Hardware acceleration backends
├── wolfssl/                # Public headers
│   └── wolfcrypt/          # Crypto headers + settings.h
├── configure.ac            # Build feature flags (source of truth)
├── tests/api.c             # TLS/SSL API tests
├── wolfcrypt/test/test.c   # wolfCrypt algorithm tests
└── IDE/                    # Platform-specific configs
```

## Build System

- **Autoconf**: `./configure --enable-X --disable-Y && make` (primary)
- **CMake**: `cmake -DWOLFSSL_X=yes ..` (secondary, may lag behind)
- **IDE/Embedded**: `user_settings.h` with `#define WOLFSSL_USER_SETTINGS`
- Code is heavily `#ifdef`-guarded — establish active defines before tracing paths
