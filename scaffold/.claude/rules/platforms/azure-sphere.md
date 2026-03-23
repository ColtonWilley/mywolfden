---
paths:
  - "**/azure*sphere*"
---

# Microsoft Azure Sphere -- wolfSSL Platform Guide

## 1. Overview

Azure Sphere is a Microsoft IoT security platform built around the MediaTek MT3620 SoC (ARM Cortex-A7 application processor, dual Cortex-M4F real-time cores, Microsoft Pluton security subsystem). wolfSSL provides two IDE project variants:

| Project Path | IDE / Build System | Projects Included |
|---|---|---|
| `IDE/VS-AZURE-SPHERE/` | Visual Studio solution (`.sln` + `.vcxproj`) | wolfSSL library, client, server, wolfCrypt test (4 projects) |
| `IDE/MSVS-2019-AZSPHERE/` | Visual Studio 2019 CMake (`CMakeLists.txt`) | Single combined app (server default, client switchable) |

Both variants use `user_settings.h` for compile-time configuration and define `WOLFSSL_AZSPHERE` as the platform flag. The CMake variant additionally supports multiple hardware definitions (Seeed MT3620 MDB, Avnet MT3620 SK, standard MT3620 RDB).

The platform runs Azure Sphere OS (custom Linux) on the Cortex-A7, so POSIX sockets are available through the SDK's `applibs` layer.

---

## 2. Build Configuration

### Platform Define

The primary define is `WOLFSSL_AZSPHERE`. Its effects in the wolfSSL source:

- **String functions**: Enables wolfSSL's internal `strcasecmp`/`strncasecmp` implementations since the Azure Sphere restricted libc does not provide them.
- **RNG seeding**: Marks the platform as needing a custom seed. Users must provide `wc_GenerateSeed()` or define `CUSTOM_RAND_GENERATE_BLOCK`.

### user_settings.h Reference

Both IDE projects ship equivalent `user_settings.h` files:

| Define | Purpose |
|---|---|
| `WOLFSSL_AZSPHERE` | Platform flag (must always be set) |
| `WOLFSSL_USER_SETTINGS` | Set via compiler flags; tells wolfSSL to use `user_settings.h` |
| `SINGLE_THREADED` | Azure Sphere apps are single-threaded by default |
| `NO_FILESYSTEM` | No filesystem access; use buffer-based cert loading |
| `SIZEOF_LONG_LONG 8` | Correct size for Cortex-A7 (32-bit ARM, 64-bit long long) |

**Enabled features:** ChaCha20-Poly1305, ECC (timing-resistant), AES-GCM, RSA (blinding), SNI, ALPN, OCSP, extended master secret, supported curves, truncated HMAC.

**Disabled:** `NO_PWDBASED`, `NO_DSA`, `NO_DES3`, `NO_RC4`, `NO_MD4`.

**Debug output** is routed through the Azure Sphere logging API:
```c
#include <applibs/log.h>
#define printf Log_Debug
#define WOLFIO_DEBUG
```

### CMake Variant Details

The CMake project configures the Azure Sphere toolchain and API set:
```cmake
azsphere_configure_tools(TOOLS_REVISION "22.02")
azsphere_configure_api(TARGET_API_SET "12")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -DWOLFSSL_USER_SETTINGS -Wno-conversion -Wno-sign-conversion")
```

wolfSSL is built as a static library. Several OpenSSL compatibility source files are excluded (`bio.c`, `conf.c`, `x509.c`, `pk.c`, etc.) since the compatibility layer is not needed on this platform.

Hardware target is selected by editing the `azsphere_target_hardware_definition()` call in `CMakeLists.txt` -- options are `seeed_mt3620_mdb` (default), `avnet_mt3620_sk`, or `mt3620_rdb`.

---

## 3. Platform-Specific Features

### Certificate Embedding

With `NO_FILESYSTEM`, certificates must be compiled-in as DER byte arrays:
```c
ret = wolfSSL_CTX_load_verify_buffer(ctx, CERT, SIZEOF_CERT, WOLFSSL_FILETYPE_ASN1);
```

To embed a custom CA certificate:
1. Convert PEM to DER: `openssl x509 -in ca-cert.pem -outform DER -out ca-cert.der`
2. Generate C array: `./scripts/dertoc.pl ./certs/ca-cert.der ca_cert_der_2048 dertoc.c`
3. Copy the array into `client.h`, update `CERT` and `SIZEOF_CERT` in `user_settings.h`

### app_manifest.json Capabilities

Azure Sphere OS enforces a mandatory capability model. Each app must declare what it accesses:

- **Client**: `"AllowedConnections": ["www.wolfssl.com", "192.168.1.200"]` -- every target IP/hostname must be listed or the OS blocks the connection silently.
- **Server**: `"AllowedTcpServerPorts": [11111]` -- declares which ports the app may bind.
- **GPIO** (CMake variant): `"Gpio": ["$WOLF_AZSPHERE"]` -- for LED status indication.

### Network Readiness

Azure Sphere requires checking network status before any socket operation:
```c
#include <applibs/networking.h>
bool isNetworkingReady = false;
if ((Networking_IsNetworkingReady(&isNetworkingReady) < 0) || !isNetworkingReady) {
    /* Wi-Fi not configured or not connected */
    return -1;
}
```

### Device Setup Workflow

1. Install Azure Sphere SDK (includes VS extension and `azsphere` CLI)
2. Create an Azure Sphere tenant and claim the device
3. Configure Wi-Fi: `azsphere device wifi add --ssid <name> --psk <password>`
4. Enable development mode: `azsphere device enable-development`

---

## 4. Common Issues

**"network is not up" error**: Wi-Fi must be configured before running. Verify with `azsphere device wifi show-status`.

**Connection refused to external hosts**: The target IP/hostname is missing from `AllowedConnections` in `app_manifest.json`. This is the most common Azure Sphere issue -- the block happens at the OS level before wolfSSL is involved.

**Certificate verification failures**: Certs must be DER-encoded buffers loaded via `wolfSSL_CTX_load_verify_buffer()`. Verify the byte array was generated correctly with `dertoc.pl` and that `SIZEOF_CERT` matches.

**Custom RNG seeding**: `WOLFSSL_AZSPHERE` flags the platform as lacking a default RNG seed. Provide `wc_GenerateSeed()` or define `CUSTOM_RAND_GENERATE_BLOCK`.

**Wrong hardware definition**: GPIO pin mappings differ between MT3620 RDB, Seeed MDB, and Avnet SK boards. A mismatch causes GPIO open failures at runtime. Update `azsphere_target_hardware_definition()` in `CMakeLists.txt`.

**`strcasecmp` link errors**: Ensure `WOLFSSL_AZSPHERE` is defined. Without it, wolfSSL uses POSIX `strcasecmp` which is unavailable in the Azure Sphere libc.

**OpenSSL compat build errors**: The CMake variant excludes `bio.c`, `x509.c`, `pk.c`, etc. Re-adding them causes conflicts with Azure Sphere SDK headers.

---

## 5. Example Configuration

### Minimal user_settings.h for Azure Sphere TLS Client

```c
#ifndef _USER_SETTINGS_H_
#define _USER_SETTINGS_H_

/* Platform */
#define WOLFSSL_AZSPHERE
#define SINGLE_THREADED
#define NO_FILESYSTEM
#define SIZEOF_LONG_LONG 8

/* Crypto */
#define HAVE_ECC
#define ECC_TIMING_RESISTANT
#define HAVE_AESGCM
#define WC_RSA_BLINDING
#define HAVE_TLS_EXTENSIONS
#define HAVE_EXTENDED_MASTER
#define HAVE_SNI

/* Reduce footprint */
#define NO_PWDBASED
#define NO_DSA
#define NO_DES3
#define NO_RC4
#define NO_MD4

/* Cert buffers (no filesystem) */
#define USE_CERT_BUFFERS_2048
#define USE_CERT_BUFFERS_256

/* Azure Sphere debug logging */
#include <applibs/log.h>
#define printf Log_Debug

#endif /* _USER_SETTINGS_H_ */
```

### Testing on the Device

**TLS server on device, client on host:**
1. Deploy the server app to the MT3620 board
2. Note the device IP from debug output (`util_PrintIfAddr()`)
3. Run from host: `./examples/client/client -h <device-ip> -p 11111 -A ./certs/ca-cert.pem`

**TLS client on device, server on host:**
1. Start host server: `./examples/server/server -b -d -p 11111 -c ./certs/server-cert.pem -k ./certs/server-key.pem`
2. Set `SERVER_IP` in `user_settings.h` to the host IP
3. Add the host IP to `AllowedConnections` in `app_manifest.json`
4. Define `CUSTOM_SERVER_CONNECTION` in `user_settings.h`, then deploy
