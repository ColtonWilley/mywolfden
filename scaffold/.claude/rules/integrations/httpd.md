---
paths:
  - "repos/osp/**/httpd/**"
  - "**/apache*"
---

# Apache httpd — External Platform Summary

## Current State
Apache httpd is one of the most widely deployed web servers. TLS is handled by `mod_ssl`, which traditionally uses OpenSSL. wolfSSL support is available via the `--enable-apachehttpd` configure flag and OSP patches.

## Architecture
- **mod_ssl**: `modules/ssl/` contains the SSL module. `ssl_engine_init.c` creates SSL contexts, `ssl_engine_io.c` handles TLS I/O on connections.
- **APR (Apache Portable Runtime)**: httpd uses APR for cross-platform I/O. SSL sits on top of APR's socket layer.
- **Build system**: `configure.in` / autoconf. `--with-ssl=/path` sets the SSL library root.

## wolfSSL Integration Notes
- wolfSSL must be built with `--enable-apachehttpd` which enables: `WOLFSSL_APACHE_HTTPD`, OpenSSL compat extra, session tickets, OCSP, CRL.
- OSP patches (in `osp/apache-httpd/`) modify `mod_ssl` source to work with wolfSSL's compat layer where needed.
- OCSP stapling: httpd supports OCSP stapling via `SSLUseStapling`. wolfSSL supports this through `--enable-ocsp` and `--enable-ocspstapling`.
- Session tickets: `SSLSessionTickets` directive uses `SSL_CTX_set_tlsext_ticket_key_cb` — wolfSSL implements this in compat layer.
- SNI: httpd relies on SNI for virtual host selection. wolfSSL SNI support is enabled by default.
- TLS 1.3: httpd 2.4.x supports TLS 1.3 with OpenSSL 1.1.1+. wolfSSL TLS 1.3 works but verify `SSLProtocol` directives.
- Common issue: httpd checks `OPENSSL_VERSION_NUMBER` in several places for feature detection. OSP patches update these checks.
- Certificate handling: httpd loads PEM certs/keys via `SSLCertificateFile`/`SSLCertificateKeyFile`. Chain certs via `SSLCertificateChainFile`. All standard PEM operations work with wolfSSL.

## Key Files
- `modules/ssl/ssl_engine_init.c` — SSL context creation and configuration
- `modules/ssl/ssl_engine_io.c` — TLS read/write I/O filter
- `modules/ssl/ssl_engine_kernel.c` — Connection-level SSL hooks
- `modules/ssl/ssl_util_ssl.c` — SSL utility functions
- `modules/ssl/mod_ssl.h` — SSL module header with OpenSSL includes
