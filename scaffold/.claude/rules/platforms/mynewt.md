---
paths:
  - "**/mynewt*"
---

# Apache Mynewt — wolfSSL Platform Guide

## 1. Overview

Apache Mynewt is an open-source embedded RTOS designed for constrained IoT devices, with strong BLE support and the `newt` package/build system. wolfSSL integrates through the `WOLFSSL_APACHE_MYNEWT` define, which auto-configures the library for single-threaded, memory-constrained targets.

The port ships as two newt packages deployed by `IDE/mynewt/setup.sh`: `crypto/wolfssl` (the library) and `apps/wolfcrypttest` (wolfCrypt unit tests).

---

## 2. Build Configuration

### Primary Define

| Define | Purpose |
|---|---|
| `WOLFSSL_APACHE_MYNEWT` | Enables all Mynewt-specific platform adaptations in wolfSSL |

This define is set in the newt package YAML file (`crypto.wolfssl.pkg.yml`), not in a `user_settings.h`. The default `pkg.cflags` line is:

```
pkg.cflags: -DWOLFSSL_APACHE_MYNEWT -DNO_FILESYSTEM -Wno-error -DHAVE_TLS_EXTENSIONS -DHAVE_SUPPORTED_CURVES
```

### Auto-Set Defines from `settings.h`

When `WOLFSSL_APACHE_MYNEWT` is defined, `settings.h` automatically sets the following:

| Auto-Set Define | Effect |
|---|---|
| `SIZEOF_LONG 4` / `SIZEOF_LONG_LONG 8` | Standard 32-bit target sizes (guarded by `#if !defined`) |
| `LITTLE_ENDIAN_ORDER` or `BIG_ENDIAN_ORDER` | Auto-detected from `__BYTE_ORDER__` |
| `NO_WRITEV` | Scatter/gather I/O disabled |
| `WOLFSSL_USER_IO` | User-provided I/O callbacks required (Mynewt uses `mn_socket`) |
| `SINGLE_THREADED` | Mutex/threading disabled |
| `NO_DEV_RANDOM` | No `/dev/random`; uses `srand(os_time_get())` seed |
| `NO_DH` | Diffie-Hellman disabled to save code size |
| `NO_WOLFSSL_DIR` | Directory operations disabled |
| `NO_ERROR_STRINGS` | Error string table removed to save flash |
| `NO_SESSION_CACHE` | Session cache disabled to reduce RAM |
| `HAVE_ECC` | ECC enabled (preferred for constrained devices) |
| `XMALLOC_USER` | Custom allocator via `os_malloc` / `os_realloc` / `os_free` |

### Package Dependencies and Syscfg

The `crypto/wolfssl` package depends on `@apache-mynewt-core/net/ip/mn_socket`. The test app additionally depends on `@apache-mynewt-core/kernel/os` and `@apache-mynewt-core/sys/console/full`.

Two tunable syscfg settings are exposed via `crypto.wolfssl.syscfg.yml`:

| Setting | Default | Description |
|---|---|---|
| `WOLFSSL_MNSOCK_MEM_BUF_COUNT` | 10 | Number of mbuf buffers for socket I/O |
| `WOLFSSL_MNSOCK_MEM_BUF_SIZE` | 2048 | Size (bytes) of each mbuf buffer |

---

## 3. Platform-Specific Features

### Memory Management

wolfSSL maps `XMALLOC`/`XREALLOC`/`XFREE` to Mynewt's `os_malloc`/`os_realloc`/`os_free` (from `os/os_malloc.h`). The `heap` and `type` parameters are cast to void and ignored.

### Networking (mn_socket)

When `WOLFSSL_LWIP` is not defined, wolfSSL uses Mynewt's native `mn_socket` API. The callbacks `Mynewt_Receive` and `Mynewt_Send` are set as the default `CBIORecv`/`CBIOSend` on every new `WOLFSSL_CTX`. A `Mynewt_Ctx` structure manages the socket handle, address, and an `os_mbuf` pointer for short-read buffering. Bind a socket to an SSL session with:

```c
wolfSSL_SetIO_Mynewt(ssl, mnSocket, &mnSockAddrIn);
```

To use LWIP instead, define both `WOLFSSL_APACHE_MYNEWT` and `WOLFSSL_LWIP`.

### Filesystem, Time, and RNG

- **Filesystem**: When `NO_FILESYSTEM` is not defined, `mynewt_port.c` provides POSIX-like wrappers (`mynewt_fopen`, `mynewt_fseek`, etc.) over Mynewt's `fs/fs.h`. In practice, most deployments use `NO_FILESYSTEM` (the default).
- **Time**: `XTIME` maps to `mynewt_time()` via `os/os_time.h`. wolfSSL uses its own `struct tm` and `time_t` types (`USE_WOLF_TM`, `USE_WOLF_TIME_T`). `LowResTimer` uses `os_gettimeofday()`.
- **RNG**: The default `wc_GenerateSeed` calls `srand(os_time_get())` then `rand() % 256`. This is **not cryptographically secure** — production deployments must override `CUSTOM_RAND_GENERATE_BLOCK` with a hardware TRNG.

### Logging

When `DEBUG_WOLFSSL` is added to `pkg.cflags`, wolfSSL registers with Mynewt's log framework on the first call to `wolfSSL_Debugging_ON()`:

```c
log_register("wolfcrypt", &mynewt_log, &log_console_handler, NULL, LOG_SYSLEVEL);
```

Enable debug output on the console by also adding `log`, `stats`, and `console` to `pkg.req_apis`.

---

## 4. Common Issues

### Weak Default RNG

The default `wc_GenerateSeed` uses `srand(os_time_get())` then `rand()` — deterministic and unsuitable for production TLS. Always provide a hardware-backed entropy source via `CUSTOM_RAND_GENERATE_BLOCK` or a custom `wc_GenerateSeed`.

### NO_DH and NO_ERROR_STRINGS Defaults

These auto-set defines surprise users who expect DH cipher suites or readable error messages. To re-enable, add `#undef NO_DH` or `#undef NO_ERROR_STRINGS` in a custom header or `pkg.cflags`. Note that error strings add several KB to flash.

### SINGLE_THREADED Limitation

wolfSSL uses no mutexes. If your application does TLS from multiple Mynewt tasks (e.g., BLE + network), serialize access externally or remove `SINGLE_THREADED` and provide mutex wrappers.

### setup.sh Deployment Errors

The script requires an existing Mynewt project with a valid `project.yml`. Run from the wolfSSL root: `./IDE/mynewt/setup.sh /path/to/myproject`. The `newt` tool must be on `$PATH`. Re-running does `rm -rf` on the target directories, so local modifications are lost.

### Memory Exhaustion on Small Targets

Default syscfg allocates ~20 KB for socket I/O buffers (10 x 2048). Reduce via `syscfg.vals` overrides.

---

## 5. Example Configuration

### Deploying and Building the Test App

```bash
# Deploy packages from wolfSSL source root into Mynewt project
./IDE/mynewt/setup.sh /path/to/my-mynewt-project
cd /path/to/my-mynewt-project

# Create simulator target, build, and run wolfCrypt tests
newt target create wolfcrypttest_sim
newt target set wolfcrypttest_sim app=apps/wolfcrypttest
newt target set wolfcrypttest_sim bsp=@apache-mynewt-core/hw/bsp/native
newt target set wolfcrypttest_sim build_profile=debug
newt build wolfcrypttest_sim
./bin/targets/wolfcrypttest_sim/app/apps/wolfcrypttest/wolfcrypttest.elf
```

### Customizing pkg.cflags

Edit `crypto/wolfssl/pkg.yml` in your Mynewt project to add features:

```yaml
pkg.cflags: >
    -DWOLFSSL_APACHE_MYNEWT -DNO_FILESYSTEM -Wno-error
    -DHAVE_TLS_EXTENSIONS -DHAVE_SUPPORTED_CURVES
    -DHAVE_AESGCM -DWOLFSSL_TLS13 -DDEBUG_WOLFSSL
```

### Enabling Hardware RNG (nRF52 Example)

```c
#include <wolfssl/wolfcrypt/random.h>

int wc_GenerateSeed(OS_Seed* os, byte* output, word32 sz)
{
    /* Replace with your MCU's hardware TRNG read */
    return my_hw_trng_read(output, sz);
}
```

### Reducing Socket Buffer Memory

In your application's `syscfg.yml`:

```yaml
syscfg.vals:
    WOLFSSL_MNSOCK_MEM_BUF_COUNT: 5
    WOLFSSL_MNSOCK_MEM_BUF_SIZE: 1024
```

This cuts socket buffer allocation from ~20 KB to ~5 KB at the cost of more fragmented reads.
