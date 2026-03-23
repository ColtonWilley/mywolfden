---
paths:
  - "**/IDE/Espressif/**"
  - "**/esp-idf/**"
  - "**/esp32*"
  - "**/ESP*"
---

# ESP32 / ESP-IDF Platform Patterns

## Integration Method
- **ESP-IDF component**: wolfSSL available as managed component or manual component in `components/wolfssl/`
- **Configuration**: via `idf.py menuconfig` → wolfSSL settings, or `user_settings.h`
- **Key file**: `IDE/Espressif/ESP-IDF/user_settings.h` — template for ESP-IDF builds
- **Examples**: `IDE/Espressif/ESP-IDF/examples/` in wolfSSL repo

## Common ESP32 Issues

### Memory Pressure During Handshake
**Symptom**: Crash or error -308 during `wolfSSL_connect()`.
**Root cause**: ESP32 default task stack (3840 bytes) far too small for TLS.
**Fix**:
- Set task stack to 10-12KB minimum in `xTaskCreate()`
- Enable `WOLFSSL_SMALL_STACK` in user_settings.h
- Use ECC cipher suites instead of RSA (50% less memory)
- Enable `ALT_ECC_SIZE` to reduce ECC point memory

### Wi-Fi Reconnect During TLS
**Symptom**: Handshake fails intermittently, especially under load.
**Root cause**: ESP32 Wi-Fi stack can temporarily disconnect during heavy crypto operations.
**Fix**: Add retry logic around `wolfSSL_connect()`, check Wi-Fi state before TLS.

### Partition Table / Flash Size
**Symptom**: Build fails with "section `.rodata' will not fit in region `drom0_0_seg'"
**Root cause**: wolfSSL with full features exceeds default app partition size.
**Fix**: Use `partitions.csv` with larger app partition, or reduce features.

### Hardware Acceleration
- ESP32 has hardware SHA, AES, RSA acceleration
- Enable: `#define WOLFSSL_ESP32_CRYPT` in user_settings.h
- Sub-options: `WOLFSSL_ESP32_CRYPT_RSA_PRI`, `WOLFSSL_ESP32_CRYPT_RSA_PRI_EXPTMOD`
- ESP32-S3, ESP32-C3: different hardware crypto capabilities — check chip variant

### Time/NTP
**Symptom**: Certificate date validation fails (error -152 or -153).
**Root cause**: ESP32 starts with time at 0 (epoch). NTP not yet synchronized.
**Fix**:
- Initialize SNTP before TLS: `esp_sntp_init()`
- Or disable date checking: `#define NO_ASN_TIME`
- Or use custom verify callback to skip date check

## Recommended user_settings.h for ESP32
Key defines beyond the template:
```c
#define WOLFSSL_SMALL_STACK
#define ALT_ECC_SIZE
#define NO_OLD_TLS              // Remove TLS 1.0/1.1
#define HAVE_SNI                // Most servers require SNI
#define HAVE_TLS_EXTENSIONS
#define WOLFSSL_TLS13           // If connecting to modern servers
```

## ESP32 Variants
| Chip | RAM | Flash | HW Crypto | Notes |
|------|-----|-------|-----------|-------|
| ESP32 | 520KB | 4-16MB | SHA, AES, RSA | Most common in tickets |
| ESP32-S2 | 320KB | 4MB+ | SHA, AES | No Bluetooth, USB OTG |
| ESP32-S3 | 512KB | 8-16MB | SHA, AES | AI acceleration, USB |
| ESP32-C3 | 400KB | 4MB+ | SHA, AES | RISC-V (RV32IMC), lower power |
| ESP32-C6 | 512KB | 4MB+ | SHA, AES | RISC-V (RV32IMAC), Wi-Fi 6, Thread |

**RISC-V variants (C3, C6):** These use a different ISA than the Xtensa-based ESP32/S2/S3. Key implications:
- Enable `WOLFSSL_SP_RISCV32` for hand-tuned RISC-V 32-bit SP math assembly — provides 2-5x speedup over generic C for ECC and RSA operations, plus constant-time guarantees
- The M extension (hardware multiply) is present on both C3 and C6 and is used by the SP RISC-V assembly
- No Xtensa assembly flags apply — `WOLFSSL_SP_RISCV32` is the correct flag, not ARM or x86 variants
- The C3 lacks a dedicated RSA/DS peripheral (unlike ESP32-S2/S3), so SP math with RISC-V assembly is the primary acceleration path for asymmetric crypto
| ESP8266 | 80KB | 1-4MB | None | Very constrained, TLS difficult |

ESP8266 is particularly challenging — may need `--enable-lowresource` and ECC-only.
