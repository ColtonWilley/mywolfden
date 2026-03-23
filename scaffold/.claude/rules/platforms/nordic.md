---
paths:
  - "**/nrf*"
  - "**/nordic*"
  - "**/nRF*"
---

# Nordic nRF5x — wolfSSL Platform Guide

## 1. Overview

The Nordic nRF5x family (including the nRF51 series) are ARM Cortex-M based microcontrollers commonly used in Bluetooth Low Energy (BLE) and other low-power wireless applications. wolfSSL provides dedicated support for these platforms through two related defines:

- **`WOLFSSL_NRF51`** — targets the nRF51 series specifically, enabling a full set of embedded constraints and hardware integration
- **`WOLFSSL_NRF5x`** — a broader platform define for the nRF5x family, referenced in `settings.h` as the general Nordic nRF5x platform flag

Both defines share a common port file at `wolfcrypt/src/port/nrf51.c`, which provides hardware-backed random number generation and optional AES acceleration using Nordic SDK peripherals.

---

## 2. Build Configuration

### Key Defines

When `WOLFSSL_NRF51` is defined, wolfSSL automatically sets the following in `settings.h`:

| Define | Purpose |
|---|---|
| `NO_DEV_RANDOM` | Disables `/dev/random` (not available on bare-metal) |
| `NO_FILESYSTEM` | Disables file system access |
| `NO_MAIN_DRIVER` | Disables the standard `main()` test driver |
| `NO_WRITEV` | Disables `writev()` support |
| `SINGLE_THREADED` | Disables multi-threading support |
| `TFM_TIMING_RESISTANT` | Enables timing-resistant math (TFM) |
| `WOLFSSL_USER_IO` | Requires user-supplied I/O callbacks |
| `NO_SESSION_CACHE` | Disables TLS session cache to save RAM |

`WOLFSSL_NRF5x` is available as a separate define for the broader nRF5x family and must be uncommented or defined manually (it is commented out by default in `settings.h`).

### Optional Hardware AES Define

To enable hardware AES acceleration via the nRF ECB peripheral, define:

```c
#define WOLFSSL_NRF51_AES
```

> **Note:** Hardware AES (`WOLFSSL_NRF51_AES`) is only available when `SOFTDEVICE_PRESENT` is **not** defined. When the SoftDevice is present, the AES path uses `sd_ecb_block_encrypt()` from the Nordic SoftDevice API instead of direct ECB register access.

### Configure Flags

No autoconf `./configure` flags are documented in the source material for this platform. Configuration is done entirely through defines, typically via a `user_settings.h` file.

### IDE / SDK Integration

The port file `wolfcrypt/src/port/nrf51.c` includes the following Nordic SDK headers, which must be available in your build environment:

```c
#include "bsp.h"
#include "nrf_delay.h"
#include "app_uart.h"
#include "app_error.h"
#include "nrf_drv_rng.h"
#include "nrf_drv_rtc.h"
#include "nrf_drv_clock.h"
#include "nrf_ecb.h"
```

When the SoftDevice is present, the following additional headers are required:

```c
#include "softdevice_handler.h"
#include "nrf_soc.h"
```

Ensure your Nordic SDK paths are correctly configured in your IDE (e.g., Segger Embedded Studio, Keil, or IAR).

---

## 3. Platform-Specific Features

### Hardware Random Number Generation

The port provides `nrf51_random_generate()`, which uses the Nordic `nrf_drv_rng` driver to fill a buffer with hardware-generated random bytes. This function:

- Initializes the RNG driver if not already running
- Polls `nrf_drv_rng_bytes_available()` in a loop until the requested number of bytes is collected
- Returns `0` on success, `-1` on error

This function replaces the standard OS random source (disabled via `NO_DEV_RANDOM`).

### Hardware AES (ECB)

When `WOLFSSL_NRF51_AES` is defined:

- **Without SoftDevice:** Uses `nrf_ecb_init()` and direct ECB hardware registers via the Nordic `nrf_ecb.h` driver
- **With SoftDevice (`SOFTDEVICE_PRESENT`):** Uses `sd_ecb_block_encrypt()` from the Nordic SoftDevice API, which arbitrates hardware access safely in a BLE context

The hardware AES support covers AES-128 ECB block encryption. Higher-level AES modes (CBC, GCM, etc.) are built on top of this primitive by wolfCrypt.

### RTC / Benchmarking

An RTC instance (`NRF_DRV_RTC_INSTANCE(0)`) is configured for use by the wolfCrypt benchmark (`wc_bench`). This is compiled in unless `NO_CRYPT_BENCHMARK` is defined.

### Threading

The platform is configured as `SINGLE_THREADED`. No RTOS threading integration is provided by the port layer. If an RTOS is used, threading support would need to be added separately.

### Networking / I/O

`WOLFSSL_USER_IO` is set, meaning the application must supply its own `EmbedSend` and `EmbedReceive` callbacks (or equivalent) for TLS I/O. No network abstraction layer is provided by the port itself.

---

## 4. Common Issues

### Stack Size
The nRF51 and nRF5x devices have limited RAM. wolfSSL's TLS handshake and cryptographic operations can require significant stack space. Ensure your stack is sized appropriately — wolfSSL recommends at minimum several kilobytes of stack for TLS operations on constrained devices. Check the wolfSSL documentation and benchmark results for your specific cipher suite selection.

### SoftDevice Conflicts
When `SOFTDEVICE_PRESENT` is defined, direct hardware peripheral access (e.g., ECB registers) is not permitted. The port handles this by routing AES through `sd_ecb_block_encrypt()`. Ensure `SOFTDEVICE_PRESENT` is correctly defined or undefined to match your build configuration, or hardware conflicts may occur at runtime.

### Session Cache
`NO_SESSION_CACHE` is enabled by default for nRF51 to conserve RAM. If session resumption is required, this will need to be re-evaluated against available memory.

### No Filesystem
`NO_FILESYSTEM` is set, so certificate and key loading from files is not available. Certificates and keys must be loaded from buffers in memory using the `_buffer` variants of wolfSSL API calls (e.g., `wolfSSL_CTX_load_verify_buffer()`).

### RNG Initialization
The `nrf51_random_generate()` function calls `nrf_drv_rng_init()` each time it is invoked and tolerates `NRF_ERROR_INVALID_STATE` (already initialized). If the RNG driver is managed elsewhere in your application, verify there are no conflicts.

### `WOLFSSL_NRF5x` vs `WOLFSSL_NRF51`
`WOLFSSL_NRF5x` is listed in `settings.h` as a platform identifier but does not independently trigger the full set of embedded constraint defines that `WOLFSSL_NRF51` does. If you are using a newer nRF52 or nRF53 series device, review `settings.h` and `nrf51.c` to confirm which define applies and whether additional configuration is needed.

---

## 5. Example Configuration

The following is a minimal `user_settings.h` for an nRF51-based project. For nRF5x devices, replace `WOLFSSL_NRF51` with `WOLFSSL_NRF5x` and adjust as needed.

```c
/* user_settings.h — wolfSSL for Nordic nRF51 / nRF5x */

#ifndef WOLFSSL_USER_SETTINGS_H
#define WOLFSSL_USER_SETTINGS_H

/* Platform identification */
#define WOLFSSL_NRF51
/* Or for broader nRF5x family: */
/* #define WOLFSSL_NRF5x */

/* These are set automatically by settings.h when WOLFSSL_NRF51 is defined,
 * but may be listed explicitly for clarity: */
#define NO_DEV_RANDOM
#define NO_FILESYSTEM
#define NO_MAIN_DRIVER
#define NO_WRITEV
#define SINGLE_THREADED
#define TFM_TIMING_RESISTANT
#define WOLFSSL_USER_IO
#define NO_SESSION_CACHE

/* Enable hardware AES via nRF ECB peripheral (omit if using SoftDevice) */
#define WOLFSSL_NRF51_AES

/* Reduce memory footprint */
#define WOLFSSL_SMALL_STACK
#define NO_CRYPT_BENCHMARK      /* Remove if benchmarking is needed */

/* Select a minimal cipher suite set appropriate for your application */
#define NO_DES3
#define NO_RC4
#define NO_MD4
#define WOLFSSL_SHA256
#define NO_SHA512               /* Remove if SHA-512 is needed */

/* Use buffer-based certificate loading */
/* (NO_FILESYSTEM already enforces this) */

#endif /* WOLFSSL_USER_SETTINGS_H */
```

> **Note:** The source material for this platform is focused on the nRF51 port layer. For more detailed guidance on memory optimization, cipher suite selection, and TLS configuration for constrained devices, consult the [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/) — particularly the chapters on building wolfSSL and porting to embedded systems.
