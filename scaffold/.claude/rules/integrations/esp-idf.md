---
paths:
  - "**/IDE/Espressif/**"
---

# Espressif ESP-IDF — External Platform Summary

## Current State

- **Active releases**: v5.2.x (maintenance), v5.3.x (maintenance), v5.4.x (current stable), v5.5.x (in development). v4.4.x is end-of-life.
- **Supported SoCs**: ESP32, ESP32-S2, ESP32-S3, ESP32-C2, ESP32-C3, ESP32-C5, ESP32-C6, ESP32-H2, ESP32-P4. ESP8266/ESP8285 use a separate RTOS SDK and are **not** ESP-IDF targets.
- **Default TLS library**: mbedTLS (v3.x / TF-PSA-Crypto in IDF v5.3+). wolfSSL replaces this as a component.
- **Build system**: CMake-based (`idf.py` wrapper). Kconfig (`menuconfig`) drives compile-time configuration. No Makefile legacy build support in v5.x.
- **Host toolchain**: xtensa-esp-elf-gcc (ESP32/S-series) or riscv32-esp-elf-gcc (C/H-series). Both are managed by `idf_tools.py`.

---

## Architecture

### Component System
- Every library is a **component**: a directory containing `CMakeLists.txt` that calls `idf_component_register()`.
- Components declare `REQUIRES` (public) and `PRIV_REQUIRES` (private) dependencies. Missing dependency declarations are a common build failure cause.
- wolfSSL ships as a drop-in component, typically placed in `<project>/components/wolfssl/` or registered via `EXTRA_COMPONENT_DIRS` in the project `CMakeLists.txt`.
- Component manager (`idf_component.yml`) can pull components from the Espressif component registry; wolfSSL publishes releases there.

### TLS Layer (`esp_tls`)
- `components/esp_tls/` is an abstraction layer over the underlying TLS library. It exposes `esp_tls_conn_new()`, `esp_tls_conn_read/write()`, etc.
- Internally selects mbedTLS or wolfSSL at compile time via Kconfig (`CONFIG_ESP_TLS_USING_WOLFSSL`).
- Higher-level components (`esp_http_client`, `esp_https_ota`, `mqtt`) call `esp_tls` and are automatically wolfSSL-backed when the option is set.
- **Direct mbedTLS API calls** in application code will break when switching to wolfSSL — these must be ported to wolfSSL APIs or the `esp_tls` abstraction.

### Hardware Acceleration
| Peripheral | ESP32 | ESP32-S2/S3 | ESP32-C3/C6/H2 |
|---|---|---|---|
| SHA (1/256/512) | ✓ | ✓ | ✓ |
| AES-128/256 | ✓ | ✓ (+ AES-XTS) | ✓ |
| RSA accelerator | ✓ (4096-bit) | ✓ | ✗ |
| ECC accelerator | ✗ | ✗ | ESP32-C6/H2 ✓ |
| Big Number (MPI) | ✓ | ✓ | ✗ |

- Hardware drivers live in `components/esp_hw_support/` and `components/hal/`.
- wolfSSL accesses hardware via its ESP32 port files (`wolfcrypt/src/port/Espressif/`). These call IDF hardware APIs directly, not through mbedTLS shims.
- Hardware acceleration requires `esp_hw_support` and `soc` as component dependencies.

### Memory Layout
- **IRAM**: Fast instruction RAM (~128–400 KB depending on chip). Functions can be placed here with `IRAM_ATTR`. wolfSSL hot paths (AES, SHA inner loops) benefit from this.
- **DRAM**: Data RAM, heap-allocated. Default wolfSSL heap.
- **PSRAM** (ESP32, ESP32-S2, ESP32-S3 with external SPI RAM): Accessible as heap after `CONFIG_SPIRAM=y` and `CONFIG_SPIRAM_USE_MALLOC=y`. Latency is higher; DMA-capable buffers must remain in internal DRAM.
- **Flash (XIP)**: Code and read-only data execute from flash via cache. Large certificate bundles and wolfSSL library code typically reside here.
- **Partition table**: Defines flash layout. OTA requires two app partitions (`ota_0`, `ota_1`). Partition table CSV is set via `CONFIG_PARTITION_TABLE_CUSTOM_FILENAME` or a preset.

### FreeRTOS / Threading
- Dual-core on ESP32/S3/P4; single-core on C/H series.
- wolfSSL mutex callbacks must be set (`wolfSSL_SetMutexCb`) or the default FreeRTOS mutex wrappers in the ESP32 port are used.
- Stack sizes for TLS tasks typically need 8–16 KB minimum; set via `xTaskCreate` stack parameter or `CONFIG_ESP_MAIN_TASK_STACK_SIZE`.

---

## wolfSSL Integration Notes

### Build System
- Place wolfSSL as a component: `<project>/components/wolfssl/` with its own `CMakeLists.txt` calling `idf_component_register()`.
- The wolfSSL repository includes a pre-built ESP-IDF component under `IDE/Espressif/ESP-IDF/` or as a standalone component repo.
- `user_settings.h` is the primary wolfSSL configuration file. It must be on the include path before any wolfSSL headers. Ensure `CMakeLists.txt` adds its directory via `INCLUDE_DIRS` or `target_include_directories`.
- To enable `esp_tls` wolfSSL backend: set `CONFIG_ESP_TLS_USING_WOLFSSL=y` in `sdkconfig` or `sdkconfig.defaults`. This also requires `CONFIG_WOLFSSL_CERTIFICATE_BUNDLE` if using the ESP certificate bundle.

### Kconfig / sdkconfig
- `CONFIG_WOLFSSL_*` options are exposed when the wolfSSL component provides a `Kconfig` file.
- Key options to verify: `CONFIG_WOLFSSL_HAVE_ESP32_CRYPT_HW_ACCEL`, `CONFIG_WOLFSSL_DEBUG_WOLFSSL`, `CONFIG_WOLFSSL_TLS13`.
- `sdkconfig.defaults` in the project root is the correct place to set persistent defaults; do not edit `sdkconfig` directly in version control.

### Hardware Acceleration Enablement
- Controlled by `#define WOLFSSL_ESP32` (or chip-specific variants) in `user_settings.h`.
- Specific accelerators: `#define NO_ESP32_CRYPT` disables all HW; individual disables: `#define NO_WOLFSSL_ESP32_CRYPT_HASH`, `NO_WOLFSSL_ESP32_CRYPT_AES`, `NO_WOLFSSL_ESP32_CRYPT_RSA_PRI`.
- Hardware SHA/AES requires the `esp_hw_support` component dependency in wolfSSL's `CMakeLists.txt`.
- **DMA constraint**: AES hardware on some chips requires source/destination buffers in internal DRAM. Passing PSRAM pointers to HW AES will cause faults or silent failures. Use `heap_caps_malloc(size, MALLOC_CAP_INTERNAL | MALLOC_CAP_DMA)` for crypto buffers when PSRAM is enabled.

### Common Integration Issues

| Issue | Cause | Fix |
|---|---|---|
| `undefined reference to wolfSSL_*` | wolfSSL component not in dependency chain | Add `REQUIRES wolfssl` to app or intermediate component |
| `user_settings.h not found` | Include path not set before wolfSSL headers | Add `user_settings.h` directory to `INCLUDE_DIRS` in component CMakeLists |
| Crash in HW AES with PSRAM enabled | DMA buffer in external RAM | Allocate crypto I/O buffers with `MALLOC_CAP_INTERNAL` |
| `esp_tls` still uses mbedTLS | `CONFIG_ESP_TLS_USING_WOLFSSL` not set | Add to `sdkconfig.defaults`; run `idf.py fullclean` then rebuild |
| Stack overflow in TLS task | Default stack too small | Increase task stack; minimum ~8 KB, recommend 12–16 KB for TLS 1.3 |
| RSA operations fail on C3/C6 | No RSA hardware on RISC-V C-series | Expected; falls back to software. Ensure `NO_WOLFSSL_ESP32_CRYPT_RSA_PRI` is set or HW RSA is not assumed |
| Linker errors with mbedTLS symbols | Both mbedTLS and wolfSSL components active | Exclude mbedTLS: set `CONFIG_MBEDTLS_ENABLED=n` or remove from `COMPONENTS` list |
| `idf_component_register` REQUIRES error | Missing `esp_hw_support` or `soc` dependency | Add to `PRIV_REQUIRES` in wolfSSL component CMakeLists |
| Certificate verification failure | System time not set (epoch 0) | Initialize SNTP before TLS handshake; or disable time checks in testing with `WOLFSSL_NO_SOCK` / custom verify callback |
| OTA partition too small | wolfSSL binary larger than mbedTLS | Increase app partition size in custom partition table CSV |

### PSRAM-Specific Notes
- Enable with `CONFIG_SPIRAM=y`, `CONFIG_SPIRAM_USE_CAPS_ALLOC=y` (preferred over `SPIRAM_USE_MALLOC` for crypto to avoid transparent allocation of DMA-incompatible buffers).
- wolfSSL's `XMALLOC` maps to `malloc` by default; override with `WOLFSSL_USER_MALLOC` and custom allocator if fine-grained control is needed.
- Large TLS record buffers (16 KB input + output) are candidates for PSRAM placement if not used as DMA targets.

---

## Key Files

### ESP-IDF Source Files
| Path | Purpose |
|---|---|
| `components/esp_tls/esp_tls.c` | TLS abstraction; wolfSSL backend selected here |
| `components/esp_tls/esp_tls_wolfssl.c` | wolfSSL-specific `esp_tls` implementation |
| `components/esp_tls/Kconfig` | Defines `CONFIG_ESP_TLS_USING_WOLFSSL` |
| `components/mbedtls/CMakeLists.txt` | mbedTLS component build; must be disabled or coexistence managed |
| `components/mbedtls/Kconfig` | `CONFIG_MBEDTLS_*` options including ROM crypto impl |
| `components/esp_hw_support/` | Hardware crypto driver APIs used by wolfSSL port |
| `tools/cmake/component.cmake` | `idf_component_register()` implementation |
| `tools/cmake/build.cmake` | `idf_build_get_property/set_property` used in component CMakeLists |

### wolfSSL Port Files (within wolfSSL source)
| Path | Purpose |
|---|---|
| `wolfcrypt/src/port/Espressif/esp32_aes.c` | HW AES driver integration |
| `wolfcrypt/src/port/Espressif/esp32_sha.c` | HW SHA driver integration |
| `wolfcrypt/src/port/Espressif/esp32_rsa.c` | HW RSA/MPI driver integration |
| `wolfcrypt/src/port/Espressif/esp32_util.c` | Utility functions, mutex, time |
| `IDE/Espressif/ESP-IDF/user_settings.h` | Reference `user_settings.h` for ESP-IDF |
| `wolfssl/wolfcrypt/settings.h` | Includes `user_settings.h` when `WOLFSSL_USER_SETTINGS` defined |

### Project-Level Configuration
| File | Purpose |
|---|---|
| `sdkconfig.defaults` | Persistent Kconfig overrides (commit this, not `sdkconfig`) |
| `partitions.csv` | Custom partition table; increase app partition for wolfSSL |
| `CMakeLists.txt` (project root) | `EXTRA_COMPONENT_DIRS` for external wolfSSL component path |
| `components/wolfssl/CMakeLists.txt` | wolfSSL component registration; must declare HW support deps |
| `components/wolfssl/user_settings.h` | wolfSSL feature configuration; single source of truth for build options |
