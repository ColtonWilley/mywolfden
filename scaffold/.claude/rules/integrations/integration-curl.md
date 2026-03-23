---
paths:
  - "repos/osp/**/curl/**"
---

# curl + wolfSSL Integration — wolfSSL Platform Guide

## 1. Overview

curl is a widely used command-line tool and library (libcurl) for transferring data with URLs, supporting protocols such as HTTPS, FTPS, SFTP, and others that rely on TLS/SSL. wolfSSL can serve as the underlying TLS backend for curl, replacing OpenSSL or other TLS libraries.

wolfSSL provides an OpenSSL compatibility layer that allows curl to use wolfSSL without requiring significant changes to the curl source code. The integration is supported through wolfSSL's build system via the `--enable-curl` configure flag, which sets the `HAVE_CURL` preprocessor define and enables the appropriate compatibility and feature set required by libcurl.

## 2. Build Configuration

### Configure Flag

To build wolfSSL with curl support, use the following configure flag:

```bash
./configure --enable-curl
make
sudo make install
```

This enables the `HAVE_CURL` define internally and configures wolfSSL with the features and OpenSSL compatibility interfaces that curl expects.

### Key Defines

The `--enable-curl` flag sets `HAVE_CURL` within the wolfSSL build system. No additional user-defined preprocessor macros are documented in the available source material as required beyond what `--enable-curl` enables automatically.

### Building curl Against wolfSSL

After installing wolfSSL built with `--enable-curl`, configure curl to use wolfSSL as its TLS backend:

```bash
./configure --with-wolfssl=/usr/local
make
sudo make install
```

Adjust the path (`/usr/local`) to match your wolfSSL installation prefix if it differs.

## 3. Platform-Specific Features

### OpenSSL Compatibility Layer

wolfSSL's curl integration relies on its OpenSSL compatibility layer. The `--enable-curl` flag ensures that the necessary OpenSSL-compatible API surface is available for libcurl's TLS backend code to function correctly.

### Protocol Support

wolfSSL supports the TLS protocol versions and cipher suites required by curl for HTTPS and other TLS-secured transfers. Specific protocol support (e.g., TLS 1.2, TLS 1.3) depends on the broader wolfSSL build configuration used alongside `--enable-curl`.

### Threading and Networking

No curl-specific threading or networking configuration details are documented in the available source material. wolfSSL's standard threading and networking support applies. Refer to the wolfSSL Manual for details on enabling thread safety (`--enable-threadlocal`, mutex callbacks) if curl is used in a multithreaded application.

## 4. Common Issues

### Compatibility Layer Completeness

Because curl was originally written against OpenSSL, any gaps in wolfSSL's OpenSSL compatibility layer may cause build or runtime errors. Using `--enable-curl` is intended to activate the correct compatibility surface, but if you encounter missing symbols or API mismatches, verify that you are using a current wolfSSL release and that `--enable-curl` was applied at configure time.

### Version Alignment

Ensure that the version of curl being built is compatible with the wolfSSL release in use. Newer curl versions may use OpenSSL APIs that require a correspondingly current wolfSSL compatibility layer.

### Installation Path

If curl's configure script cannot locate wolfSSL, confirm the installation prefix and that `pkg-config` or the `--with-wolfssl` path is set correctly when configuring curl.

### Limited Source Material Note

The available source material for this integration is limited to the configure flag reference (`--enable-curl` / `HAVE_CURL`). For detailed troubleshooting, cipher suite configuration, certificate handling, and advanced options, consult:

- The [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/)
- The wolfSSL curl integration documentation and example files in the wolfSSL source tree (if present under `IDE/` or `examples/`)
- The curl documentation for `--with-wolfssl`

## 5. Example Configuration

### Minimal Build Command

```bash
# Build and install wolfSSL with curl support
./configure --enable-curl
make
sudo make install

# Build curl against the installed wolfSSL
cd /path/to/curl
./configure --with-wolfssl=/usr/local
make
sudo make install
```

### Verification

After building, verify that curl is linked against wolfSSL:

```bash
curl --version
```

The output should list `wolfSSL` (or `WolfSSL`) as the SSL backend, for example:

```
curl 8.x.x (x86_64-pc-linux-gnu) libcurl/8.x.x wolfSSL/5.x.x
```

### Notes

- No `user_settings.h` is required for a standard autoconf-based build; the `--enable-curl` flag manages the necessary defines automatically.
- If a custom `user_settings.h` is needed (e.g., for an embedded or IDE-based build), include `#define HAVE_CURL` and ensure the OpenSSL compatibility layer is enabled (`#define OPENSSL_EXTRA` or equivalent). Consult the wolfSSL Manual for the full set of defines required by the OpenSSL compatibility layer.
