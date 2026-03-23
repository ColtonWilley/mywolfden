---
paths:
  - "repos/osp/**/mosquitto/**"
---

# Eclipse Mosquitto — External Platform Summary

## Current State

- **Latest stable version**: 2.1.2 (released 2026-02-09); 2.1.3 in progress as of source material
- **MQTT protocol support**: v5.0, v3.1.1, v3.1
- **Components**: `mosquitto` broker, `libmosquitto` C client library, `libmosquittipp` C++ wrapper, `mosquitto_pub`, `mosquitto_sub`, `mosquitto_rr`, `mosquitto_ctrl`, `mosquitto_passwd`
- **TLS support**: Enabled by default via OpenSSL; PSK support available as a compile-time option (`WITH_TLS_PSK`)
- **Build systems**: GNU Make (Linux/Unix primary), CMake (Windows/Mac, also supported on Linux)
- **Notable recent TLS changes (2.1.0)**:
  - Added `--tls-keylog` option for Wireshark decryption debugging
  - Added `disable_client_cert_date_checks` option
  - Removed TLS v1.1 support from clients (still available in broker but undocumented)
  - Switched to OpenSSL-provided function for x509 hostname verification
  - Added `bridge_tls_use_os_certs` option

---

## Architecture

### Component Layout

```
mosquitto (broker)          libmosquitto (client lib)
    src/net.c                   lib/net_mosq.c
    src/tls_mosq.c              lib/tls_mosq.c
         |                           |
         +--------+  +---------------+
                  |  |
             lib/net_mosq.c (shared networking)
             lib/tls_mosq.h (TLS abstraction header)
                  |
             OpenSSL API (SSL_CTX, SSL, BIO, etc.)
```

### TLS Integration Points

- **TLS is abstracted** through `tls_mosq.h` / `tls_mosq.c` files shared between broker and client library
- **Broker-side TLS**: `src/net.c` — handles `SSL_CTX` setup per listener, client certificate verification, PSK callbacks
- **Client-side TLS**: `lib/net_mosq.c` — handles `SSL_CTX` setup for outbound connections
- **OpenSSL API compatibility**: Code targets OpenSSL 1.1 API (`OPENSSL_API_COMPAT=0x10100000L`); uses ENGINE API (deprecated in OpenSSL 3.0, noted as a TODO in CMakeLists.txt)
- **PSK**: Enabled at compile time with `WITH_TLS_PSK`; uses OpenSSL PSK callback mechanism (`SSL_CTX_set_psk_server_callback`, `SSL_CTX_set_psk_client_callback`)
- **Mutual TLS (mTLS)**: Broker configures `SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT`; client cert path set via `certfile`/`keyfile` config options
- **TLS ex_data**: `tls_ex_index_mosq` (client lib) and `tls_ex_index_context`/`tls_ex_index_listener` (broker) are used to attach Mosquitto context pointers to SSL objects — relevant when debugging callbacks

### Threading

- Client library uses pthreads for `mosquitto_loop_start()` / `mosquitto_loop_stop()`; TLS operations occur on the network thread
- Broker is single-threaded event loop (select/poll); TLS I/O is non-blocking with `SSL_ERROR_WANT_READ`/`SSL_ERROR_WANT_WRITE` handling

---

## wolfSSL Integration Notes

### Build System

**CMake** (`WITH_TLS=ON`):
```cmake
find_package(OpenSSL REQUIRED)
add_definitions("-DWITH_TLS")
add_definitions("-DOPENSSL_API_COMPAT=0x10100000L")
```
wolfSSL must be built with OpenSSL compatibility layer (`--enable-opensslall` or `--enable-opensslextra`) and headers must satisfy `find_package(OpenSSL)`. Point CMake to wolfSSL's compatibility headers:
```
-DOPENSSL_ROOT_DIR=/path/to/wolfssl
-DOPENSSL_INCLUDE_DIR=/path/to/wolfssl/include/wolfssl
-DOPENSSL_LIBRARIES=/path/to/wolfssl/lib/libwolfssl.so
```

**GNU Make**:
Override via `CFLAGS`/`LDFLAGS` in the top-level `Makefile` or `config.mk`. Set include path to wolfSSL's OpenSSL compat headers.

### Required wolfSSL Build Options

| Feature | wolfSSL Configure Flag |
|---|---|
| OpenSSL API compatibility | `--enable-opensslextra` or `--enable-opensslall` |
| TLS-PSK | `--enable-psk` |
| TLS 1.3 | `--enable-tls13` |
| ENGINE API stubs (for `UI_*` calls) | `--enable-opensslall` |
| x509 hostname verification | `--enable-opensslextra` |
| Certificate date override | `--enable-opensslextra` |

### Known Integration Issues

1. **ENGINE API usage**: `lib/net_mosq.c` and `src/net.c` use `UI_create_method()`, `UI_method_set_opener()`, etc. (OpenSSL ENGINE/UI subsystem). wolfSSL's OpenSSL compat layer must stub or implement these. Build with `--enable-opensslall`; if symbols are missing, stub them out or patch `net_mosq.c` to guard with `#ifndef WOLFSSL_OPENSSL_H_`.

2. **`OPENSSL_API_COMPAT=0x10100000L` macro**: This is set globally. wolfSSL's compat headers must not conflict with this define. Verify wolfSSL's `<wolfssl/openssl/ssl.h>` does not conditionally exclude needed symbols based on this value.

3. **PSK callbacks**: Mosquitto uses `SSL_CTX_set_psk_server_callback()` and `SSL_CTX_set_psk_client_callback()`. Confirm wolfSSL exposes these in its compat layer when built with `--enable-psk`. The callback signature must match OpenSSL 1.1 exactly.

4. **`tls_ex_index_mosq` / ex_data**: Mosquitto uses `SSL_get_ex_new_index()` and `SSL_get_ex_data()` / `SSL_set_ex_data()`. These must be functional in wolfSSL's compat layer.

5. **`BIO` usage in broker**: `src/net.c` creates a `BIO` object after `accept()` (`BIO *bio`). wolfSSL's BIO compat must support `BIO_new_socket()` or equivalent.

6. **x509 hostname verification**: 2.1.0 switched to `X509_check_host()` (OpenSSL-provided). wolfSSL must expose this via compat layer (`--enable-opensslextra`).

7. **Non-blocking TLS I/O**: Mosquitto relies on `SSL_ERROR_WANT_READ` / `SSL_ERROR_WANT_WRITE` return codes from `SSL_read()`/`SSL_write()`. wolfSSL supports these but verify behavior with partial records.

8. **`disable_client_cert_date_checks`**: Uses `X509_VERIFY_PARAM` APIs. Confirm wolfSSL compat coverage if this option is needed.

### PSK-Specific Notes

- PSK is a compile-time option (`WITH_TLS_PSK` / `-DWITH_TLS_PSK`); must be enabled in both Mosquitto and wolfSSL builds
- Broker PSK config: `psk_hint`, `psk_file` in `mosquitto.conf`
- Client PSK config: `psk` and `psk_identity` options in client API (`mosquitto_tls_psk_set()`)
- wolfSSL PSK and certificate-based auth cannot be active simultaneously on the same `SSL_CTX` in some configurations — verify listener separation

---

## Key Files

| File | Purpose |
|---|---|
| `CMakeLists.txt` | Primary CMake build; `WITH_TLS`, `WITH_TLS_PSK` options; `find_package(OpenSSL)` |
| `config.mk` | GNU Make build variables; override `CFLAGS`/`LDFLAGS` here for wolfSSL |
| `lib/net_mosq.c` | Client library TLS init, `SSL_CTX` setup, UI method setup, non-blocking I/O |
| `lib/tls_mosq.c` | Shared TLS helper functions (cert loading, verification callbacks) |
| `lib/tls_mosq.h` | TLS abstraction header included by both broker and client |
| `src/net.c` | Broker TLS: listener SSL_CTX setup, `net__socket_accept()`, BIO creation, mTLS verify flags |
| `src/tls_mosq.c` | Broker-side TLS helpers, PSK callbacks, cert verification |
| `mosquitto.conf` (runtime) | TLS config: `cafile`, `certfile`, `keyfile`, `tls_version`, `psk_hint`, `psk_file`, `require_certificate` |
| `include/mosquitto.h` | Public client API including `mosquitto_tls_set()`, `mosquitto_tls_psk_set()`, `mosquitto_tls_opts_set()` |

### Key Configuration Directives (mosquitto.conf)

```
# Certificate-based mutual auth
listener 8883
cafile /path/to/ca.crt
certfile /path/to/server.crt
keyfile /path/to/server.key
require_certificate true
tls_version tlsv1.2   # or tlsv1.3

# PSK
listener 8884
psk_hint broker_hint
psk_file /path/to/psk_file
```

### Client API Entry Points for TLS

```c
/* Certificate-based */
mosquitto_tls_set(mosq, cafile, capath, certfile, keyfile, pw_callback);
mosquitto_tls_opts_set(mosq, SSL_VERIFY_PEER, "tlsv1.2", NULL);

/* PSK */
mosquitto_tls_psk_set(mosq, psk_hex, identity, NULL);
```
