# ESP32 / ESP-IDF Platform

> One-line summary: ESP32 variant capabilities, hardware crypto defines, and memory constraints for wolfSSL on ESP-IDF.

**When to read**: porting wolfSSL to any ESP32 variant, debugging ESP-IDF component integration, or diagnosing memory/crash issues during TLS on Espressif chips.

---

## Variant Table

| Chip | RAM | ISA | HW Crypto | Notes |
|------|-----|-----|-----------|-------|
| ESP32 | 520 KB | Xtensa LX6 | SHA, AES, RSA | Most common; full HW accel |
| ESP32-S2 | 320 KB | Xtensa LX7 | SHA, AES | No Bluetooth, USB OTG |
| ESP32-S3 | 512 KB | Xtensa LX7 | SHA, AES | AI acceleration, USB |
| ESP32-C3 | 400 KB | RISC-V (RV32IMC) | SHA, AES | No RSA/DS peripheral |
| ESP32-C6 | 512 KB | RISC-V (RV32IMAC) | SHA, AES | Wi-Fi 6, Thread |
| ESP32-H2 | 320 KB | RISC-V (RV32IMC) | SHA, AES | Thread/Zigbee only, no Wi-Fi |
| ESP8266 | 80 KB | Xtensa L106 | None | Very constrained; ECC-only, `--enable-lowresource` |

## RISC-V Variants (C3, C6, H2)

- Use `WOLFSSL_SP_RISCV32` for hand-tuned RISC-V 32-bit SP math assembly (2-5x speedup for ECC/RSA, constant-time)
- The M extension (hardware multiply) is present and used by SP RISC-V assembly
- C3 lacks a dedicated RSA/DS peripheral -- SP math with RISC-V assembly is the primary asymmetric acceleration path
- Do NOT use ARM or Xtensa assembly flags on these variants

## Hardware Acceleration Defines

| Define | Purpose |
|--------|---------|
| `WOLFSSL_ESP32_CRYPT` | Enable ESP32 hardware SHA/AES |
| `WOLFSSL_ESP32_CRYPT_RSA_PRI` | Enable hardware RSA acceleration |
| `WOLFSSL_ESP32_CRYPT_RSA_PRI_EXPTMOD` | Enable RSA modular exponentiation HW path |
| `WOLFSSL_SP_RISCV32` | RISC-V SP math assembly (C3/C6/H2 only) |

## Key Embedded Defines for ESP32

```c
#define WOLFSSL_SMALL_STACK    // essential -- default task stack is 3840 bytes
#define ALT_ECC_SIZE           // reduce ECC point memory
#define NO_OLD_TLS             // remove TLS 1.0/1.1
#define HAVE_SNI               // most servers require SNI
#define WOLFSSL_TLS13          // modern server connectivity
```

## ESP-IDF Integration

- wolfSSL available as managed ESP-IDF component or manual component in `components/wolfssl/`
- Configuration via `idf.py menuconfig` or `user_settings.h`
- Template: `IDE/Espressif/ESP-IDF/user_settings.h`
- Examples: `IDE/Espressif/ESP-IDF/examples/`

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| Crash or error -308 during `wolfSSL_connect()` | Default task stack (3840 B) too small for TLS | Set task stack to 10-12 KB in `xTaskCreate()` |
| Certificate date validation fails (-152 / -153) | ESP32 starts with time=0; NTP not synced | Call `esp_sntp_init()` before TLS |
| `.rodata` won't fit in `drom0_0_seg` | Full-feature wolfSSL exceeds default app partition | Use custom `partitions.csv` with larger app partition |
| Handshake fails intermittently under load | Wi-Fi stack disconnects during heavy crypto | Add retry logic; check Wi-Fi state before TLS |

## What This File Does NOT Cover

ESP-IDF installation, generic Wi-Fi/BLE setup, menuconfig walkthrough. See `embedded-common.md` for cross-platform patterns (stack sizing, RNG, time source).
