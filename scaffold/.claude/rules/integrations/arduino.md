---
paths:
  - "**/IDE/ARDUINO/**"
---

# Arduino Core API — External Platform Summary

## Current State
Arduino provides a simplified C++ framework for embedded development across many boards (AVR, ARM, ESP32, etc.). The ArduinoCore-API defines the standard interfaces (`Client`, `Server`, `WiFiClient`, etc.) that board packages implement. wolfSSL provides an Arduino library for adding TLS to Arduino projects.

## Architecture
- **Core API**: `api/` defines abstract interfaces — `Client` (TCP), `Stream` (I/O), `Print` (output). Board-specific packages implement these.
- **WiFiClientSecure**: Most Arduino board packages provide a `WiFiClientSecure` class for TLS, typically backed by mbedTLS (ESP32) or BearSSL (ESP8266).
- **Library system**: Third-party libraries (like wolfSSL) are installed via the Library Manager or as ZIP imports.

## wolfSSL Integration Notes
- wolfSSL's Arduino library lives in `IDE/ARDUINO/` in the wolfSSL repo. It wraps wolfSSL as an Arduino-compatible library with `library.properties`.
- Installation: Copy `IDE/ARDUINO/` contents to `~/Arduino/libraries/wolfssl/`, or use the Arduino Library Manager.
- Configuration: Arduino projects use `user_settings.h` (no autotools). The default `IDE/ARDUINO/user_settings.h` provides a minimal TLS 1.2/1.3 config suitable for constrained boards.
- Define `ARDUINO` to enable Arduino-specific code paths in wolfSSL (affects includes, random number generation, time functions).
- Memory: AVR boards (ATmega2560: 8KB RAM) are extremely tight — only pre-shared key (PSK) mode is practical. ARM-based Arduino boards (SAMD, Teensy, Due) can handle full TLS with certificates.
- Random number generation: wolfSSL needs a hardware RNG or seed source. On Arduino, this varies by board — ESP32 has hardware RNG, AVR may need `CUSTOM_RAND_GENERATE` pointing to `analogRead()` of a floating pin (not cryptographically secure — fine for dev/testing).
- I/O callbacks: Implement `wolfSSL_SetIOSend`/`wolfSSL_SetIORecv` to wrap Arduino's `Client::write()`/`Client::read()`.
- Common issues:
  - Flash size: wolfSSL with full TLS can be 100-200KB of flash. AVR boards with 256KB flash may not fit both wolfSSL and application code. Use `WOLFSSL_SMALL_STACK` and disable unused features.
  - No filesystem: Certificate loading must use `wolfSSL_CTX_load_verify_buffer()` (load from C arrays) rather than file-based APIs.
  - Compiler: Arduino IDE uses gcc. Ensure `-DWOLFSSL_USER_SETTINGS` is in build flags.

## Key Files (in wolfSSL repo)
- `IDE/ARDUINO/` — Arduino library package
- `IDE/ARDUINO/user_settings.h` — Default Arduino configuration
- `IDE/ARDUINO/library.properties` — Arduino Library Manager metadata
- `IDE/ARDUINO/wolfssl.h` — Main include for Arduino sketches
