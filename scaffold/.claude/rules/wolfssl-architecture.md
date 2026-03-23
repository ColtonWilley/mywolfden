---
paths:
  - "**/src/internal.c"
  - "**/src/ssl.c"
  - "**/src/tls*.c"
  - "**/src/dtls*.c"
  - "**/wolfcrypt/src/asn.c"
---

# wolfSSL Architecture Overview

## Core Subsystems

### wolfCrypt (Cryptography Engine)
**Location**: `wolfcrypt/src/`, headers in `wolfssl/wolfcrypt/`
- All cryptographic primitives: AES, RSA, ECC, SHA, HMAC, DRBG, etc.
- FIPS boundary defined by `wolfcrypt_first` / `wolfcrypt_last` symbols
- Key files: `aes.c`, `rsa.c`, `ecc.c`, `sha256.c`, `random.c`, `asn.c`
- ASN.1/DER encoding/decoding in `asn.c` (~30K lines, most complex file)
- Memory allocation: `XMALLOC`/`XFREE` macros, customizable per-platform

### wolfSSL (TLS/DTLS Protocol Engine)
**Location**: `src/`, headers in `wolfssl/`
- TLS 1.0-1.3 and DTLS 1.0-1.3 implementations
- Key files: `internal.c` (~50K lines, core TLS state machine), `ssl.c` (API layer), `tls.c`, `tls13.c`
- I/O abstracted via callbacks: `wolfSSL_SetIORecv()` / `wolfSSL_SetIOSend()`
- Certificate loading/verification in `ssl.c` + `asn.c`
- Session management in `ssl.c` (session cache, tickets)

### Build System
**Location**: `configure.ac`, `CMakeLists.txt`, `IDE/` directories
- Autoconf is the primary build system; CMake is secondary
- `configure.ac` controls all feature flags (`--enable-*`, `--disable-*`)
- User settings: `wolfssl/wolfcrypt/settings.h` includes `user_settings.h` for IDE builds
- Platform-specific configs in `IDE/` subdirectories (e.g., `IDE/STM32Cube/`, `IDE/ARDUINO/`)

## Component Dependencies

See CLAUDE.md for the dependency diagram. Key principle: issues in wolfCrypt
can manifest as bugs in any satellite product.

## Key Source Files

See CLAUDE.md for the key source files table.

## Threading Model
- wolfSSL is thread-safe when compiled with threading support
- Global structures protected by mutexes (session cache, CA cache)
- Per-SSL object: single-threaded access expected (one thread per SSL*)
- `--enable-singlethreaded` disables all locking (embedded targets)

## Memory Model
- Static memory feature (`--enable-staticmemory`): pre-allocated pools, no malloc at runtime
- `WOLFSSL_SMALL_STACK`: moves large buffers from stack to heap
- `WOLFMEM_TRACK_STATS`: memory usage tracking
- Typical TLS handshake memory: 40-60KB (RSA 2048), 20-30KB (ECC P-256)
