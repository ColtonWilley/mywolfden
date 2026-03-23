---
paths:
  - "repos/osp/**"
---

# nginx, HAProxy, stunnel, OpenVPN, Apache + wolfSSL — wolfSSL Platform Guide

## 1. Overview

wolfSSL provides compatibility layers and integration support for several widely-used open-source server and networking applications. Each integration allows the respective application to use wolfSSL as its underlying TLS/SSL library in place of OpenSSL, leveraging wolfSSL's smaller footprint, performance characteristics, and FIPS-readiness where applicable.

The supported platforms covered in this guide are:

- **nginx** — High-performance HTTP server and reverse proxy
- **HAProxy** — High-availability load balancer and proxy server
- **stunnel** — SSL/TLS tunneling proxy
- **OpenVPN** — Open-source VPN solution
- **Apache HTTPD** — The Apache HTTP Server

Each integration is enabled through a dedicated configure flag and sets a corresponding preprocessor define that activates the appropriate compatibility shims within the wolfSSL source tree.

> **Note:** The source material available for this guide covers configure-level integration. For detailed patching instructions, application-specific build steps, and runtime configuration, consult the wolfSSL documentation portal and the relevant application integration guides at [https://www.wolfssl.com](https://www.wolfssl.com).

---

## 2. Build Configuration

### Configure Flags and Preprocessor Defines

Each application integration is activated by passing the corresponding flag to wolfSSL's `./configure` script. The flag sets a preprocessor define used internally by wolfSSL.

| Application    | Configure Flag           | Preprocessor Define     |
|----------------|--------------------------|-------------------------|
| nginx          | `--enable-nginx`         | `WOLFSSL_NGINX`         |
| HAProxy        | `--enable-haproxy`       | `WOLFSSL_HAPROXY`       |
| stunnel        | `--enable-stunnel`       | `HAVE_STUNNEL`          |
| OpenVPN        | `--enable-openvpn`       | `WOLFSSL_OPENVPN`       |
| Apache HTTPD   | `--enable-apachehttpd`   | `WOLFSSL_APACHE_HTTPD`  |

### Apache HTTPD — Additional Requirements

The Apache HTTPD integration has explicit additional dependencies within the build system. Enabling `--enable-apachehttpd` automatically enables:

- `OPENSSL_EXTRA` (`-DOPENSSL_EXTRA`)
- `OPENSSL_ALL` (`-DOPENSSL_ALL`)

This is because Apache HTTPD requires the full OpenSSL compatibility API surface (`opensslextra` and `opensslall`). If `ENABLED_OPENSSLALL` and `ENABLED_OPENSSLCOEXIST` are both disabled at configure time, the build system will automatically enable them when `--enable-apachehttpd` is specified.

In practice, a minimal configure command for Apache HTTPD support would be:

```bash
./configure --enable-apachehttpd
```

The build system handles enabling `--enable-opensslall` and `--enable-opensslextra` automatically.

### Building wolfSSL for Each Platform

General build steps apply across all integrations:

```bash
./autogen.sh        # if building from a git clone
./configure <flags>
make
make install
```

After installing wolfSSL, the target application must be patched or configured to link against wolfSSL rather than OpenSSL. Refer to the wolfSSL application integration guides for patch files and application-side build instructions.

---

## 3. Platform-Specific Features

### nginx (`WOLFSSL_NGINX`)

- Enables wolfSSL's nginx-specific compatibility code paths.
- nginx uses an event-driven, non-blocking I/O model; wolfSSL's non-blocking TLS support is used in this context.
- The define `WOLFSSL_NGINX` gates nginx-specific API adjustments within wolfSSL.

### HAProxy (`WOLFSSL_HAPROXY`)

- Enables HAProxy-specific compatibility within wolfSSL.
- HAProxy is a high-throughput proxy; the integration is designed to support HAProxy's SSL termination and passthrough modes.
- The define `WOLFSSL_HAPROXY` gates HAProxy-specific code paths.

### stunnel (`HAVE_STUNNEL`)

- stunnel wraps arbitrary TCP connections in TLS. The `HAVE_STUNNEL` define enables stunnel-compatible API behavior within wolfSSL.
- stunnel integration is listed alongside signal handling (`--enable-signal`) in the configure system, suggesting signal-related compatibility may be relevant for this integration.

### OpenVPN (`WOLFSSL_OPENVPN`)

- Enables OpenVPN-specific compatibility code within wolfSSL.
- OpenVPN uses TLS for control channel security and optionally for data channel encryption. wolfSSL's OpenVPN integration targets the control channel TLS layer.
- The define `WOLFSSL_OPENVPN` gates OpenVPN-specific adjustments.

### Apache HTTPD (`WOLFSSL_APACHE_HTTPD`)

- The most API-intensive integration of those listed. Apache's `mod_ssl` relies heavily on the OpenSSL API, requiring the full `OPENSSL_ALL` and `OPENSSL_EXTRA` compatibility surface.
- OCSP support is also noted as being enabled in the configure logic surrounding the Apache HTTPD section, suggesting OCSP stapling or validation may be expected by Apache's SSL module.

---

## 4. Common Issues

### Apache HTTPD: OpenSSL Compatibility Surface Required

Apache HTTPD will not build correctly against wolfSSL without `OPENSSL_ALL` and `OPENSSL_EXTRA`. The configure system handles this automatically, but if you are building wolfSSL manually (e.g., via a custom `user_settings.h`), you must ensure both defines are present:

```c
#define OPENSSL_EXTRA
#define OPENSSL_ALL
```

Omitting these will result in missing API symbols at compile or link time.

### OCSP Dependency with Apache HTTPD

The configure source shows OCSP being enabled in the context of the Apache HTTPD integration. If OCSP is required (e.g., for `SSLUseStapling` in Apache), ensure wolfSSL is built with:

```bash
--enable-ocsp
--enable-ocspstapling
```

Or in `user_settings.h`:

```c
#define HAVE_OCSP
#define HAVE_CERTIFICATE_STATUS_REQUEST
```

### stunnel: Signal Handling

The configure system lists `--enable-signal` in proximity to `--enable-stunnel`. If stunnel behaves unexpectedly with respect to process signals, verify whether signal-related compatibility options are needed in your build.

### General: OpenSSL Coexistence

For applications that may load both OpenSSL and wolfSSL in the same process (e.g., via modules), the `--enable-opensslcoexist` flag may be required to avoid symbol conflicts. The Apache HTTPD configure logic explicitly checks for `ENABLED_OPENSSLCOEXIST` as an alternative to `ENABLED_OPENSSLALL`.

### General: Patching the Application

wolfSSL does not replace OpenSSL as a drop-in shared library for these applications automatically. Each application typically requires:

1. A patch to its build system to locate and link wolfSSL.
2. Possibly source-level patches to use wolfSSL's OpenSSL-compatibility headers (`wolfssl/openssl/ssl.h` etc.).

Refer to the wolfSSL GitHub repository and the wolfSSL documentation for maintained patch sets for each application.

---

## 5. Example Configuration

### Configure Commands

**nginx:**
```bash
./configure --enable-nginx
make
sudo make install
```

**HAProxy:**
```bash
./configure --enable-haproxy
make
sudo make install
```

**stunnel:**
```bash
./configure --enable-stunnel
make
sudo make install
```

**OpenVPN:**
```bash
./configure --enable-openvpn
make
sudo make install
```

**Apache HTTPD:**
```bash
./configure --enable-apachehttpd
make
sudo make install
```

> Apache HTTPD automatically enables `--enable-opensslall` and `--enable-opensslextra` as part of its configure logic.

---

### Minimal `user_settings.h` Equivalents

If you are building wolfSSL without autoconf (e.g., for an IDE or embedded toolchain), the following defines correspond to each integration. Include the relevant block for your target application.

**nginx:**
```c
#define WOLFSSL_NGINX
#define OPENSSL_EXTRA
```

**HAProxy:**
```c
#define WOLFSSL_HAPROXY
#define OPENSSL_EXTRA
```

**stunnel:**
```c
#define HAVE_STUNNEL
#define OPENSSL_EXTRA
```

**OpenVPN:**
```c
#define WOLFSSL_OPENVPN
#define OPENSSL_EXTRA
```

**Apache HTTPD:**
```c
#define WOLFSSL_APACHE_HTTPD
#define OPENSSL_EXTRA
#define OPENSSL_ALL
/* Optional but recommended for Apache SSL stapling: */
#define HAVE_OCSP
#define HAVE_CERTIFICATE_STATUS_REQUEST
```

---

## Additional Resources

- wolfSSL Manual: [https://www.wolfssl.com/documentation/manuals/wolfssl/](https://www.wolfssl.com/documentation/manuals/wolfssl/)
- wolfSSL GitHub (integration patches and examples): [https://github.com/wolfSSL/wolfssl](https://github.com/wolfSSL/wolfssl)
- Application-specific integration guides are available on the wolfSSL website and may include maintained patch files for nginx, HAProxy, stunnel, OpenVPN, and Apache HTTPD.

> The source material for this guide is primarily derived from wolfSSL's `configure.ac`. For full integration details — including application-side patching, runtime configuration, and version compatibility — consult the wolfSSL documentation and support resources directly.
