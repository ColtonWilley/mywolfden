---
paths:
  - "**/memory.c"
  - "**/user_settings.h"
  - "**/staticmemory*"
---

# Embedded Memory Constraints

## Typical Memory Requirements

| Operation | Stack | Heap | Notes |
|-----------|-------|------|-------|
| TLS 1.2 handshake (RSA 2048) | 8-12 KB | 40-60 KB | Peak during key exchange |
| TLS 1.2 handshake (ECC P-256) | 6-8 KB | 20-30 KB | Significantly less than RSA |
| TLS 1.3 handshake (ECC P-256) | 6-8 KB | 25-35 KB | Slightly more than 1.2 (transcript hash) |
| wolfCrypt RSA sign (2048-bit) | 4-8 KB | 15-20 KB | Big number operations |
| wolfCrypt ECC sign (P-256) | 3-5 KB | 8-12 KB | |
| DTLS handshake | +2-4 KB | +5-10 KB | Reassembly buffers |
| Per-session after handshake | 1-2 KB | 8-15 KB | Ongoing session state |

## Stack Overflow Symptoms
- Hard fault / crash during handshake (most common)
- Corrupted data in seemingly unrelated variables
- Random crashes that move when code is reorganized
- FreeRTOS: `vApplicationStackOverflowHook()` triggered

## Reducing Memory Usage

### Stack
- `#define WOLFSSL_SMALL_STACK` — moves large arrays from stack to heap (critical for RTOS)
- `#define WOLFSSL_SMALL_STACK_CACHE` — caches heap allocations within a function scope
- FreeRTOS task stack: 24KB minimum for RSA 2048 handshake with SMALL_STACK enabled
- ESP32: default task stack (3840 bytes) is insufficient — set to 10KB+ in menuconfig

### Heap
- `--enable-lowresource` — reduces buffers and disables non-essential features
- `--enable-staticmemory` — pre-allocated pools, deterministic memory usage
- `WOLFMEM_TRACK_STATS` — track peak and current memory usage
- `#define ALT_ECC_SIZE` — reduces ECC point memory (significant savings)
- `#define RSA_LOW_MEM` — reduces RSA operation memory at cost of speed
- Use ECC instead of RSA — 50-70% less memory for equivalent security

### Disabling Unused Features
- `#define NO_SESSION_CACHE` — saves ~2KB per connection if session resumption not needed
- `#define NO_OLD_TLS` — removes TLS 1.0/1.1 support
- `#define WOLFSSL_NO_TLS12` — removes TLS 1.2 (TLS 1.3 only)
- `#define NO_PSK` — if not using pre-shared keys
- `#define NO_DH` — if using ECC-only cipher suites

## Static Memory System
For systems that cannot use malloc at runtime:
```c
#define WOLFSSL_STATIC_MEMORY
byte memory[80000];  // pre-allocated buffer
wolfSSL_CTX_load_static_memory(&ctx, wolfSSLv23_client_method_ex,
                                memory, sizeof(memory), 0, 1);
```
- Buffer sizing: use `wolfSSL_StaticBufferSz()` to determine minimum
- Multiple pools supported (general vs I/O)
- Thread-safe with proper locking configuration

## Common Embedded Pitfalls
- **Not checking return values**: `wolfSSL_CTX_new()` returns NULL on OOM
- **Global vs per-connection**: CTX is shared, SSL is per-connection — don't multiply CTX memory
- **Certificate loading**: loading PEM on memory-constrained devices wastes memory on Base64 decode — use DER format
- **Shared buffers**: `wolfSSL_set_using_nonblock()` + shared I/O buffer can reduce memory
- **Debug build**: `--enable-debug` significantly increases memory usage — disable for production
