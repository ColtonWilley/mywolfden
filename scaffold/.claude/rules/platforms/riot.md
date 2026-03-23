---
paths:
  - "**/riot*"
  - "**/RIOT*"
---

# RIOT OS — wolfSSL Platform Guide

## 1. Overview

RIOT OS is an open-source microkernel operating system designed for IoT and constrained devices. It supports 8-bit, 16-bit, and 32-bit microcontrollers and provides the GNRC network stack with native 6LoWPAN/IPv6 support. wolfSSL is integrated into RIOT as an official external package (`pkg/wolfssl`), available through the standard RIOT build system.

wolfSSL on RIOT is primarily used for DTLS over the GNRC UDP/IP stack, securing communication on mesh networks and constrained links where TLS over TCP is impractical. The integration provides custom I/O callbacks (`GNRC_SendTo`, `GNRC_ReceiveFrom`) and a DTLS cookie generation callback tailored for the GNRC `sock_udp` interface.

The RIOT package pins to a specific wolfSSL release (currently v5.5.4) via commit hash, ensuring reproducible builds.

---

## 2. Build Configuration

### Primary Defines

| Define | Purpose |
|---|---|
| `WOLFSSL_RIOT_OS` | Master platform define; enables RIOT-specific settings in `settings.h` |
| `WOLFSSL_GNRC` | Enables GNRC network stack I/O callbacks and DTLS cookie generation |
| `WOLFSSL_USER_SETTINGS` | Always set by RIOT build system; directs wolfSSL to read `user_settings.h` |

### What `WOLFSSL_RIOT_OS` Enables (from `settings.h`)

```c
#ifdef WOLFSSL_RIOT_OS
    #define TFM_NO_ASM           /* Portable C math for broad MCU support */
    #define NO_FILESYSTEM        /* No filesystem on constrained targets */
    #define USE_CERT_BUFFERS_2048 /* Compiled-in test certificate buffers */
    #if defined(WOLFSSL_GNRC) && !defined(WOLFSSL_DTLS)
        #define WOLFSSL_DTLS     /* Auto-enable DTLS when using GNRC stack */
    #endif
#endif
```

The DTLS auto-enable is critical: GNRC is UDP-based, so DTLS is forced on when `WOLFSSL_GNRC` is active.

### RIOT Package Integration

Add `USEPKG += wolfssl` to your application Makefile. The build system automatically sets `-DWOLFSSL_USER_SETTINGS=1 -DWOLFSSL_RIOT_OS=1` and configures include paths for the wolfSSL source, `sock_tls` wrapper, and package headers.

### Pseudomodules

| Pseudomodule | Purpose |
|---|---|
| `wolfcrypt` | Core cryptographic library only (no TLS) |
| `wolfssl` | Full SSL/TLS library |
| `wolfcrypt-test` / `wolfcrypt-benchmark` | Test suite and benchmarks |
| `wolfssl_dtls` | DTLS support (activates GNRC UDP callbacks) |
| `wolfssl_socket` | Full POSIX socket interface instead of GNRC sock |

---

## 3. Platform-Specific Features

### GNRC Network Stack Integration

wolfSSL registers custom I/O callbacks when `WOLFSSL_GNRC` is defined:

- **`GNRC_SendTo`** — Wraps `sock_udp_send()` for outbound DTLS records.
- **`GNRC_ReceiveFrom`** — Wraps `sock_udp_recv()` with DTLS timeout integration via `wolfSSL_dtls_get_current_timeout()`. Supports non-blocking mode.
- **`GNRC_GenerateCookie`** — Hashes the peer's `sock_udp_ep_t` address using SHA-1 or SHA-256 for DTLS cookie verification.

These callbacks are registered automatically in `wolfSSL_CTX_new()` — no manual `wolfSSL_SetIORecv`/`wolfSSL_SetIOSend` calls needed.

### sock_tls Context

The `sock_tls_t` type (defined in `wolfio.h`) wraps the GNRC context passed to I/O callbacks. It contains a `union` of `sock_tcp_t`/`sock_udp_t`, a `closing` flag, and a `peer_addr` endpoint. This structure manages the underlying socket, peer address tracking, and connection state.

### POSIX Socket Alternative

Enable `wolfssl_socket` for targets with full POSIX socket support. This uses standard BSD sockets for both TLS and DTLS, bypassing GNRC-specific callbacks.

### System Header Exclusion

When `WOLFSSL_GNRC` or `WOLFSSL_RIOT_OS` is defined, wolfSSL skips `<sys/socket.h>` and related POSIX networking headers. RIOT provides its own headers through GNRC.

---

## 4. Common Issues

### DTLS Not Enabled When Expected

The auto-enable logic only sets `WOLFSSL_DTLS` when **both** `WOLFSSL_RIOT_OS` and `WOLFSSL_GNRC` are defined. If using a custom `user_settings.h`, `WOLFSSL_GNRC` must be defined before `settings.h` processes the `WOLFSSL_RIOT_OS` block.

### SHA Requirement for DTLS Cookies

The GNRC cookie callback requires SHA-1 or SHA-256. If both `NO_SHA` and `NO_SHA256` are defined, compilation fails:

```
#error Must enable either SHA-1 or SHA256 (or both) for GNRC.
```

### Assembly Disabled by Default

`TFM_NO_ASM` is set automatically for portability. To override for ARM Cortex-M, `#undef TFM_NO_ASM` and define `WOLFSSL_SP_MATH` + `WOLFSSL_SP_ARM_CORTEX_M_ASM`.

### Memory Constraints

DTLS handshakes require 10-20 KB of heap. On heavily constrained MCUs, use ECC-only (`HAVE_ECC` + `NO_RSA`) to save ~20 KB, enable `WOLFSSL_SMALL_STACK`, disable unused suites (`NO_DH`, `NO_DSA`, `NO_RC4`, `NO_MD4`), or use `WOLFCRYPT_ONLY` for crypto primitives without TLS.

### Package Version Pinning

RIOT pins wolfSSL to a specific commit hash (e.g., v5.5.4). To use a newer version, update `PKG_VERSION` in `RIOT/pkg/wolfssl/Makefile`. Upstream updates may lag behind wolfSSL releases.

### Compiler Warnings

RIOT suppresses `-Wno-maybe-uninitialized` and `-Wno-cast-align` (both false positives). Safe to suppress in custom builds.

---

## 5. Example Configuration

### Minimal DTLS Application Makefile

```makefile
APPLICATION = dtls_example
BOARD ?= native

USEPKG += wolfssl
USEMODULE += wolfssl_dtls
USEMODULE += gnrc_sock_udp
USEMODULE += gnrc_netdev_default
USEMODULE += auto_init_gnrc_netif
USEMODULE += gnrc_ipv6_default

include $(RIOTBASE)/Makefile.include
```

### Recommended `user_settings.h` for Constrained DTLS

```c
/* user_settings.h — wolfSSL config for RIOT OS DTLS */
#define WOLFSSL_RIOT_OS
#define WOLFSSL_GNRC
#define WOLFSSL_DTLS           /* Auto-enabled, but explicit for clarity */
#define WOLFSSL_SMALL_STACK
#define SMALL_SESSION_CACHE
#define NO_OLD_TLS
#define NO_RSA                 /* ECC-only saves ~20 KB */
#define NO_DH
#define NO_DSA
#define NO_RC4
#define NO_MD4
#define HAVE_ECC
#define HAVE_AESGCM
#define HAVE_TLS_EXTENSIONS
#define HAVE_SUPPORTED_CURVES
#define USE_FAST_MATH          /* TFM_NO_ASM set automatically */
```

### RIOT Example Applications

| Example | Location | Purpose |
|---|---|---|
| wolfSSL test/benchmark | `tests/pkg/wolfssl-test` | Cipher verification and performance |
| ED25519 verify | `tests/pkg/wolfcrypt-ed25519-verify` | Minimal-footprint signature demo |
| DTLS client/server | `examples/networking/dtls/dtls-wolfssl/` | Full DTLS over GNRC UDP |

Build and flash: `cd RIOT/examples/networking/dtls/dtls-wolfssl && make BOARD=your_board flash term`

### Notes

- Always include `<wolfssl/wolfcrypt/settings.h>` as the first wolfSSL header.
- The `sock_tls` wrapper in RIOT's package directory provides glue between RIOT's `sock` API and wolfSSL's I/O layer — manual I/O callback setup is not needed.
- For production, replace `USE_CERT_BUFFERS_2048` with your own certificate provisioning.
