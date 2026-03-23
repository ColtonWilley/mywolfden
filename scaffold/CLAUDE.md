# wolfDen

## How to Use This Environment

You have domain knowledge files in `.claude/rules/`. They are REFERENCE
material — background context about wolfSSL conventions and architecture.

**Your primary tool is reading the actual code.** Read the target function.
Read its callers. Read analogous functions nearby. The code around your
target almost always contains the pattern you need to follow.

Do NOT apply a pattern from loaded knowledge without first verifying it
matches what you see in the actual code. If the code shows a different
pattern than what your loaded knowledge suggests, follow the code.

The knowledge files help you notice things you might miss. They do not
tell you what to do.

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

## API Naming Conventions

- `wolfSSL_*` — TLS/SSL API (e.g., `wolfSSL_CTX_new()`)
- `wc_*` — wolfCrypt API (e.g., `wc_AesCbcEncrypt()`)
- `WOLFSSL_*` — Feature/config macros (e.g., `WOLFSSL_TLS13`)
- `HAVE_*` — Algorithm availability (e.g., `HAVE_ECC`)
- `NO_*` — Algorithm exclusion (e.g., `NO_RSA`)
- `XMALLOC`/`XFREE`/`XREALLOC` — Platform-abstracted memory

## Change Scope Awareness

wolfSSL changes rarely touch just one file. After identifying the core fix,
check whether these companion changes are needed:

- **Validation/bounds fix in wolfcrypt/src/**: Add negative test cases in
  `wolfcrypt/test/test.c` (find the algorithm's existing test function)
- **New public API function**: Declaration in header + check wrapper bindings
  in `wrapper/rust/`, `wrapper/python/`, `java/` (grep for similar functions)
- **New `#ifdef` macro**: Register in `.wolfssl_known_macro_extras` (sorted)
- **Configure flag change**: Update both `configure.ac` AND `CMakeLists.txt`
- **Error code addition**: Define in `error-crypt.h` or `error-ssl.h`, add
  string mapping in `wolfcrypt/src/error.c`

## Build System Quick Reference

- **Autoconf**: `./configure --enable-X --disable-Y && make` (primary)
- **CMake**: `cmake -DWOLFSSL_X=yes ..` (secondary, may lag behind)
- **IDE/Embedded**: `user_settings.h` with `#define WOLFSSL_USER_SETTINGS`
- Code is heavily `#ifdef`-guarded — establish active defines before tracing paths
