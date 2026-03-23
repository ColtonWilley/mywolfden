---
paths:
  - "**/platformio*"
  - "**/PlatformIO*"
---

# PlatformIO — wolfSSL Platform Guide

## 1. Overview

PlatformIO is a cross-platform build system and library manager for embedded development, available as a CLI tool or VSCode extension. wolfSSL publishes two distinct library variants to the PlatformIO Registry:

- **wolfssl/wolfssl** (Regular) — Native wolfSSL for ESP-IDF, STM32 HAL, and other non-Arduino frameworks. Registry: https://registry.platformio.org/libraries/wolfssl/wolfssl
- **wolfssl/Arduino-wolfSSL** (Arduino) — wolfSSL for the Arduino framework. Registry: https://registry.platformio.org/libraries/wolfssl/Arduino-wolfSSL

Both variants also have staging/preview builds under the `wolfssl-staging` owner for pre-release testing. The key distinction: if the project uses `framework = arduino`, use Arduino-wolfSSL. If it uses `framework = espidf` or another native framework, use the regular wolfssl library. Mixing these is a common source of build failures.

---

## 2. Build Configuration

### lib_deps — Adding wolfSSL to a Project

Add the dependency to `platformio.ini` using `lib_deps`. Version pinning options:

```ini
lib_deps = wolfssl/wolfssl@*           ; always latest
lib_deps = wolfssl/wolfssl@^5.0.0     ; any 5.x.x (recommended)
lib_deps = wolfssl/wolfssl@>=5.7.0    ; minimum version
lib_deps = wolfssl/wolfssl@^5.7.2     ; specific release series
```

Note: the release library uses lowercase `wolfssl/wolfssl`, while staging uses `wolfssl-staging/wolfSSL` (mixed case).

### build_flags — Required Defines

Two build flags are mandatory for most PlatformIO wolfSSL projects:

```ini
build_flags = -DWOLFSSL_USER_SETTINGS, -DWOLFSSL_ESP32
```

- **`-DWOLFSSL_USER_SETTINGS`** — Required. Tells wolfSSL to load configuration from `user_settings.h` instead of a generated `config.h`.
- **`-DWOLFSSL_ESP32`** — Required for ESP32 targets. Replace with the appropriate define for other boards (e.g., `-DWOLFSSL_STM32`).

### user_settings.h — Feature Configuration

All wolfSSL feature selection is controlled through `user_settings.h`. Place it in the project's `include/` directory. The default shipped with the PlatformIO library is configured for broad compatibility. For production, customize it to enable only what your application needs.

Do **not** edit `wolfssl/wolfcrypt/settings.h` or `config.h` directly.

### sdkconfig.defaults — ESP-IDF Specific

For ESP-IDF projects, key system parameters in `sdkconfig.defaults`:

- **Stack size**: `CONFIG_ESP_MAIN_TASK_STACK_SIZE=10500` (at least 10500 for RSA, 5500 for others)
- **Watchdog**: `CONFIG_ESP_TASK_WDT_EN=n` to prevent timeouts during crypto
- **Partition table**: `CONFIG_PARTITION_TABLE_SINGLE_APP_LARGE=y` for crypto-heavy builds
- **CPU frequency**: `CONFIG_ESP32_DEFAULT_CPU_FREQ_240=y`

---

## 3. Platform-Specific Features

### ESP32 Hardware Crypto Acceleration

When `WOLFSSL_ESP32` is defined, wolfSSL enables hardware-accelerated crypto via ESP32 peripherals:

- **AES-CBC** — 7,500+ KiB/s at 240 MHz
- **SHA-256/384/512** — 15,000+ KiB/s via hardware SHA
- **Big-integer math** — Hardware `esp_mp_mul`, `esp_mp_mulmod`, `esp_mp_exptmod` with automatic software fallback

Hardware acceleration status is reported at startup when `HAVE_VERSION_EXTENDED_INFO` is defined.

### Multi-Board Targeting and Variant Selection

PlatformIO supports multiple environments in a single `platformio.ini`, each with its own framework and library variant. Use `wolfssl/wolfssl` for native frameworks (`espidf`, `stm32cube`) and `wolfssl/Arduino-wolfSSL` for the `arduino` framework. The native variant gets full hardware crypto port access; the Arduino variant is limited by the Arduino abstraction layer and uses `WOLFSSL_ARDUINO` as its platform define.

---

## 4. Common Issues

### Wrong Library Variant for Framework

Using `wolfssl/wolfssl` with `framework = arduino` or `wolfssl/Arduino-wolfSSL` with `framework = espidf` causes build failures. Match the library variant to your framework.

### Missing WOLFSSL_USER_SETTINGS

Without `-DWOLFSSL_USER_SETTINGS` in `build_flags`, wolfSSL looks for a nonexistent `config.h`, causing missing-header errors. Always include it.

### Stack Overflow on ESP32

The default ESP-IDF main task stack (3,584 bytes) is insufficient for wolfSSL. Set `CONFIG_ESP_MAIN_TASK_STACK_SIZE=10500` in `sdkconfig.defaults` for RSA workloads, or 5,500 for non-RSA.

### Watchdog Timeout During Crypto

Long-running RSA operations or benchmarks trigger the ESP32 watchdog. Disable with `CONFIG_ESP_TASK_WDT_EN=n` in `sdkconfig.defaults`, or define `WOLFSSL_ESP_NO_WATCHDOG` in `user_settings.h`.

### Case Sensitivity in lib_deps

Release uses `wolfssl/wolfssl` (lowercase); staging uses `wolfssl-staging/wolfSSL` (uppercase S). Wrong case causes "library not found" errors.

### Stale sdkconfig Cache

Changes to `sdkconfig.defaults` are ignored if a generated `sdkconfig` already exists. Delete it or run `pio run -t clean` before rebuilding.

### user_settings.h Location Warning

Boot log message `Warning: old cmake, user_settings.h location unknown` is non-fatal. The Espressif port layer cannot detect the path via CMake, but the file is still loaded via the build flag.

---

## 5. Example Configuration

Complete `platformio.ini` based on official wolfSSL PlatformIO examples:

```ini
[env:esp32dev]
platform = espressif32
board = esp32dev
framework = espidf
upload_port = /dev/ttyUSB0
monitor_port = /dev/ttyUSB0
monitor_speed = 115200
build_flags = -DWOLFSSL_USER_SETTINGS, -DWOLFSSL_ESP32
monitor_filters = direct
lib_deps = wolfssl/wolfssl@^5.7.2
```

Minimal `user_settings.h` for ESP32 ESP-IDF:

```c
/* user_settings.h — wolfSSL PlatformIO ESP32 */
#define WOLFSSL_ESPIDF
#define WOLFSSL_ESP32
#define WOLFSSL_TLS13
#define NO_OLD_TLS
#define HAVE_TLS_EXTENSIONS
#define HAVE_SUPPORTED_CURVES
#define HAVE_ECC
#define HAVE_AESGCM
#define WOLFSSL_SHA384
#define WOLFSSL_SHA512
#define WOLFSSL_ESP32_CRYPT       /* hardware acceleration */
#define NO_DES3
#define NO_RC4
#define NO_MD4
#define NO_FILESYSTEM
#define NO_WRITEV
#define TFM_TIMING_RESISTANT      /* side-channel protections */
#define ECC_TIMING_RESISTANT
#define WC_RSA_BLINDING
#define RSA_LOW_MEM               /* memory optimization */
#define USE_FAST_MATH
```

---

## References

- PlatformIO wolfSSL source: `IDE/PlatformIO/` in the wolfSSL repository
- PlatformIO Registry (regular): https://registry.platformio.org/libraries/wolfssl/wolfssl
- PlatformIO Registry (Arduino): https://registry.platformio.org/libraries/wolfssl/Arduino-wolfSSL
- wolfSSL Manual: https://www.wolfssl.com/documentation/manuals/wolfssl/chapter02.html
- PlatformIO docs: https://docs.platformio.org/page/projectconf.html
