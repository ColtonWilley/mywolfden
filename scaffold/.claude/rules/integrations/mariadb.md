---
paths:
  - "repos/osp/**/mariadb/**"
---

# MariaDB Server — External Platform Summary

## Current State
MariaDB Server is a community-developed fork of MySQL. wolfSSL support was added as an alternative to OpenSSL/yaSSL for client-server TLS connections. MariaDB builds with `-DWITH_SSL=wolfssl` in CMake.

## Architecture
- **TLS layer**: `mysys_ssl/` contains the SSL abstraction. `vio/viosslfactories.c` handles SSL context creation for client and server connections.
- **Build system**: `cmake/ssl.cmake` detects and configures the SSL library. When wolfSSL is selected, it sets `HAVE_WOLFSSL` and links against wolfssl.
- **Connection flow**: Server creates an SSL context at startup (`new_VioSSLFd()`), each client connection gets wrapped via `sslaccept()`/`sslconnect()`.

## wolfSSL Integration Notes
- Build: `cmake -DWITH_SSL=wolfssl -DWOLFSSL_ROOT=/path/to/wolfssl ..`
- wolfSSL must be built with `--enable-mariadb` which enables OpenSSL compatibility layer features MariaDB needs: `WOLFSSL_MYSQL_COMPATIBLE`, session caching, `SSL_CTX_set_info_callback`.
- MariaDB uses the OpenSSL compat API — it calls `SSL_new()`, `SSL_CTX_new()`, etc. so wolfSSL's `--enable-opensslextra` is required.
- Certificate handling uses PEM format exclusively. DER certs need conversion.
- Known issue: Some MariaDB versions check for `SSLv23_method()` which maps to `wolfSSLv23_method()` — ensure compat layer is complete.
- Thread safety: MariaDB is heavily multi-threaded. wolfSSL must be built with `--enable-threadlocal` or proper mutex callbacks.

## Key Files
- `cmake/ssl.cmake` — SSL library detection and configuration
- `mysys_ssl/my_crypt.cc` — Crypto helper functions
- `vio/viosslfactories.c` — SSL context factory for connections
- `vio/viossl.c` — SSL read/write wrappers
- `include/ssl_compat.h` — SSL API compatibility macros
