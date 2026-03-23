---
paths:
  - "**/IDE/ARDUINO/**"
  - "**/arduino*"
---

# Arduino — wolfSSL Platform Guide

## 1. Overview

Arduino is a popular open-source electronics platform combining hardware microcontroller boards with a simplified C/C++ IDE and library ecosystem. wolfSSL supports Arduino through a dedicated library package available via the Arduino Library Manager, restructured from the standard wolfSSL source tree to conform to Arduino library conventions.

The official wolfSSL Arduino Library is published to the [Arduino Library Manager index](http://downloads.arduino.cc/libraries/library_index.json) and maintained at [github.com/wolfSSL/Arduino-wolfSSL](https://github.com/wolfSSL/Arduino-wolfSSL). It provides TLS/DTLS client and server capability, symmetric cryptography (e.g., AES), and other wolfCrypt primitives on supported Arduino-compatible boards.

A variant target, the **Intel Galileo**, is also explicitly supported via an additional define (see Section 2).

---

## 2. Build Configuration

### Primary Define

To build wolfSSL for Arduino, define:

```c
#define WOLFSSL_ARDUINO
```

For Arduino running on the **Intel Galileo** board, define both:

```c
#define WOLFSSL_ARDUINO
#define INTEL_GALILEO
```

These defines are listed as commented-out options in `wolfssl/wolfcrypt/settings.h` and should **not** be set there directly. Instead, all customization belongs in `user_settings.h`.

### Configure Flags

There are no `./configure`-based build flags for Arduino. The Arduino IDE does not use autoconf/make. The library is consumed directly through the Arduino IDE's library management system.

### WOLFSSL_USER_SETTINGS

The `WOLFSSL_USER_SETTINGS` macro **must** be defined project-wide. This is handled automatically by the library's `wolfssl.h` wrapper header (located at `IDE/ARDUINO/wolfssl.h`). This macro causes wolfSSL to load configuration from `user_settings.h` rather than relying on a generated `config.h`.

### user_settings.h Location

The `user_settings.h` file is located in the wolfSSL library source directory within the Arduino libraries folder:

| OS      | Path |
|---------|------|
| Windows | `C:\Users\%USERNAME%\Documents\Arduino\libraries\wolfssl\src\user_settings.h` |
| macOS   | `~/Documents/Arduino/libraries/wolfssl/src/user_settings.h` |
| Linux   | `~/Arduino/libraries/wolfssl/src/user_settings.h` |

### IDE / Project Files

- The Arduino library structure is defined by `IDE/ARDUINO/library.properties.template` and `IDE/ARDUINO/keywords.txt`.
- The `wolfssl-arduino.sh` script is used to package and publish releases to the Arduino Registry.
- VisualGDB project files are included with the `template` and `wolfssl_AES_CTR` example sketches for users who prefer the VisualGDB IDE.
- The `wolfssl-arduino.cpp` file provides the Arduino-specific library entry point.

---

## 3. Platform-Specific Features

### Hardware Crypto

The source material does not document specific hardware crypto acceleration for generic Arduino boards. The Intel Galileo variant is called out with `INTEL_GALILEO`, but no hardware crypto offload details are provided in the available source material. Check the [wolfSSL manual](https://www.wolfssl.com/documentation/manuals/wolfssl/chapter02.html) and board-specific documentation for hardware acceleration options.

### Threading

Arduino boards are generally single-threaded (no RTOS). No threading-specific configuration is described in the available source material for the Arduino target. Multi-threading support is not expected to be required for typical Arduino deployments.

### Networking

wolfSSL provides TLS and DTLS networking support on Arduino. The available example sketches demonstrate:

- **TLS Client** (`wolfssl_client`)
- **TLS Server** (`wolfssl_server`)
- **DTLS Client** (`wolfssl_client_dtls`)
- **DTLS Server** (`wolfssl_server_dtls`)

The I/O layer can be customized using `wolfSSL_SetIORecv` (noted in `keywords.txt` as a key API). Networking hardware integration (e.g., Ethernet shield, WiFi module) is handled at the sketch level and is board-dependent.

---

## 4. Common Issues

### WOLFSSL_USER_SETTINGS Must Be Project-Wide

`WOLFSSL_USER_SETTINGS` must be defined for the entire project, not just in individual source files. The library's `wolfssl.h` header handles this, but if you bypass it, the build will fail or use incorrect settings.

### Include Order

For every source file that uses wolfSSL, include `wolfssl/wolfcrypt/settings.h` before any other wolfSSL header. The recommended pattern is:

```cpp
#include "wolfssl.h"   // Arduino wrapper — must come first
```

Do **not** explicitly `#include "user_settings.h"` in any source file.

### Do Not Edit settings.h or config.h

Apply all customizations only to `user_settings.h`. Do not edit wolfSSL's `settings.h` or `config.h` files directly.

### File Warning Suppression

Similar to PlatformIO, Arduino has limited build control over which files are compiled. The `WOLFSSL_IGNORE_FILE_WARN` define is used in analogous environments to suppress warnings about unexpected file inclusions. If you see file-related warnings, consider adding:

```c
#define WOLFSSL_IGNORE_FILE_WARN
```

to your `user_settings.h`.

### Memory Constraints

Arduino boards (particularly AVR-based boards such as the Uno) have very limited RAM and flash. wolfSSL's full TLS stack may exceed the resources of smaller boards. Reduce the build footprint by disabling unused algorithms and features in `user_settings.h`. Boards with more resources (ARM Cortex-M based, ESP32 via Arduino framework, etc.) are better suited for TLS workloads. Specific stack size recommendations are not documented in the available source material; consult the [wolfSSL manual](https://www.wolfssl.com/documentation/manuals/wolfssl/chapter02.html) for memory optimization guidance.

### Intel Galileo

If targeting the Intel Galileo, both `WOLFSSL_ARDUINO` and `INTEL_GALILEO` must be defined. Defining only one may result in incorrect behavior.

---

## 5. Example Configuration

The following is a minimal `user_settings.h` for an Arduino build, based on the available source material. Expand or restrict features based on your board's resources and application requirements.

```c
/* user_settings.h — wolfSSL Arduino minimal configuration */

/* Identify the platform */
#define WOLFSSL_ARDUINO

/* Uncomment if targeting Intel Galileo */
/* #define INTEL_GALILEO */

/* Use this file for all wolfSSL configuration */
/* (WOLFSSL_USER_SETTINGS is defined project-wide by wolfssl.h) */

/* Reduce TLS version surface — enable only what you need */
#define WOLFSSL_TLS13
#define NO_OLD_TLS

/* Disable unused key exchange / cipher features to save memory */
#define NO_DES3
#define NO_RC4
#define NO_MD4

/* Disable features not typically needed on embedded targets */
#define NO_FILESYSTEM
#define NO_WOLFSSL_DIR

/* Suppress file inclusion warnings common in Arduino builds */
#define WOLFSSL_IGNORE_FILE_WARN

/* Optional: enable only specific ECC curves to reduce code size */
/* #define HAVE_ECC */
/* #define ECC_SHAMIR */

/* Optional: static memory (no dynamic allocation) — advanced use */
/* #define WOLFSSL_STATIC_MEMORY */
```

> **Note:** The source material for Arduino is focused on library packaging and IDE integration. For detailed memory optimization macros, algorithm selection, and advanced embedded configuration, refer to the [wolfSSL Manual Chapter 2](https://www.wolfssl.com/documentation/manuals/wolfssl/chapter02.html) and the [Getting Started with wolfSSL on Arduino](https://www.wolfssl.com/getting-started-with-wolfssl-on-arduino/) guide.

---

## References

- Arduino Library Manager: [downloads.arduino.cc/libraries/library_index.json](http://downloads.arduino.cc/libraries/library_index.json)
- wolfSSL Arduino source: `IDE/ARDUINO/` in the wolfSSL repository
- Example sketches: [github.com/wolfSSL/wolfssl-examples/tree/master/Arduino](https://github.com/wolfSSL/wolfssl-examples/tree/master/Arduino)
- wolfSSL Manual: [wolfssl.com/documentation/manuals/wolfssl/chapter02.html](https://www.wolfssl.com/documentation/manuals/wolfssl/chapter02.html)
