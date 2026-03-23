---
paths:
  - "**/hexagon*"
  - "**/Hexagon*"
---

# Qualcomm Hexagon DSP — wolfSSL Platform Guide

## 1. Overview

wolfSSL provides support for offloading cryptographic operations to the Qualcomm Hexagon DSP. The port is located under `IDE/HEXAGON/` and uses the Hexagon SDK build system to produce both a CPU-side shared library and a DSP-side skel library. When `WOLFSSL_DSP` is defined, ECC verify operations are offloaded to the aDSP (audio DSP) by default.

The Hexagon DSP is found in Qualcomm Snapdragon SoCs used in mobile, automotive, and IoT applications. The DSP runs the QuRT (Qualcomm Real-Time OS) microkernel. wolfSSL's Hexagon integration communicates between the CPU (ARM) and DSP via Qualcomm's FastRPC mechanism.

**Port files:**
- `IDE/HEXAGON/Makefile` — CPU-side build (UbuntuARM aarch64)
- `IDE/HEXAGON/DSP/Makefile` — DSP-side build (Hexagon v65)
- `IDE/HEXAGON/user_settings.h` — wolfSSL configuration
- `IDE/HEXAGON/build.sh` — Convenience build and deploy script
- `IDE/HEXAGON/DSP/wolfssl_dsp.idl` — FastRPC interface definition
- `wolfcrypt/src/wc_dsp.c` — DSP handle management and offload logic
- `IDE/HEXAGON/ecc-verify.c`, `ecc-verify-benchmark.c` — Example and benchmark applications

**Note:** There are no HEXAGON- or QUALCOMM-specific defines in `settings.h`. The port is entirely controlled through `WOLFSSL_DSP` in `user_settings.h` and the Hexagon SDK build system.

---

## 2. Build Configuration

### Prerequisites

The Hexagon SDK must be installed and initialized before building:
```sh
source ~/Qualcomm/Hexagon_SDK/3.4.3/setup_sdk_env.source
```

This sets `HEXAGON_SDK_ROOT` and other required environment variables.

### Primary Define

```c
#define WOLFSSL_DSP
```

This enables DSP offloading of ECC operations. It is defined in `IDE/HEXAGON/user_settings.h` and adds a `remote_handle64 handle` field to the `ecc_key` structure for DSP communication.

### Building

The build is split into two stages — DSP-side and CPU-side:

```sh
cd IDE/HEXAGON

# Build DSP library (Hexagon v65)
cd DSP
make V=hexagon_Release_dynamic_toolv83_v65
cd ..

# Build CPU library and executables (ARM64)
make V=UbuntuARM_Release_aarch64
```

Or use the convenience script:
```sh
cd IDE/HEXAGON
./build.sh Release
```

The build produces:
- `DSP/hexagon_Release_dynamic_toolv83_v65/ship/libwolfssl_dsp_skel.so` — DSP skel library
- `UbuntuARM_Release_aarch64/ship/libwolfssl.so` — CPU-side shared library
- `UbuntuARM_Release_aarch64/ship/benchmark` — wolfCrypt benchmark
- `UbuntuARM_Release_aarch64/ship/testwolfcrypt` — wolfCrypt test
- `UbuntuARM_Release_aarch64/ship/eccverify` — ECC verify example
- `UbuntuARM_Release_aarch64/ship/eccbenchmark` — ECC verify benchmark

### Deployment to Device

Files are pushed to the target device via ADB:
```sh
adb push DSP/hexagon_Release_dynamic_toolv83_v65/ship/libwolfssl_dsp_skel.so /data/rfsa/adsp/
adb push UbuntuARM_Release_aarch64/ship/libwolfssl.so /data/
adb push UbuntuARM_Release_aarch64/ship/benchmark /data/
```

### Reference user_settings.h

The default configuration is minimal and focused on ECC performance:

```c
#define WOLFCRYPT_ONLY
#define HAVE_ECC
#define FP_ECC
#define NO_DSA
#define NO_DH
#define NO_RSA
#define USE_FAST_MATH
#define TFM_TIMING_RESISTANT
#define ECC_TIMING_RESISTANT
#define WOLFSSL_HAVE_SP_RSA
#define WOLFSSL_HAVE_SP_ECC
#define WOLFSSL_SP_MATH
#define WOLFSSL_SP_ARM64_ASM          /* ARM NEON on CPU side */
#define WOLFSSL_DSP                    /* Enable DSP offloading */
```

### Compiler Flags

The Makefile adds:
```
-DWOLFSSL_USER_SETTINGS
-mcpu=generic+crypto
```

For increased performance, uncomment `-O3` in both `IDE/HEXAGON/Makefile` and `IDE/HEXAGON/DSP/Makefile`.

---

## 3. Platform-Specific Features

### DSP Offloading Architecture

When `WOLFSSL_DSP` is defined, ECC verify operations are handed off from the ARM CPU to the Hexagon DSP via FastRPC. The architecture consists of:

1. **CPU stub library** (`libwolfssl.so`) — Contains the wolfSSL API and FastRPC client stubs
2. **DSP skel library** (`libwolfssl_dsp_skel.so`) — Contains the wolfSSL cryptographic implementations running on the DSP

A default DSP handle is created during `wolfCrypt_Init()` targeting the aDSP. A mutex protects the default handle for thread safety.

### DSP Handle Management

- **Single-threaded:** The default handle created by `wolfCrypt_Init()` is used automatically. No additional setup needed.
- **Multi-threaded:** Each thread needs its own DSP handle. Set handles using either:
  - `wc_ecc_set_handle(ecc_key* key, remote_handle64 handle)` — set handle per key
  - `wolfSSL_SetHandleCb()` — register a callback to provide handles dynamically

The handle callback signature:
```c
int (*wolfSSL_DSP_Handle_cb)(remote_handle64 *handle, int finished, void *ctx);
```

The callback is invoked with `finished=0` before DSP dispatch and `finished=1` after the DSP returns the result.

### Supported DSP Targets

The Makefile supports multiple DSP targets through the `LIB_DSPRPC` variable:
- **aDSP** (audio DSP) — default
- **cDSP** (compute DSP) — set `CDSP_FLAG=1`
- **mDSP** (modem DSP) — set `MDSP_FLAG=1`
- **sDSP** (sensor/SLPI DSP) — set `SLPI_FLAG=1`

### ARM NEON on CPU Side

The reference configuration enables `WOLFSSL_SP_ARM64_ASM` for ARM NEON-accelerated SP math on the CPU side. This provides fast software-path ECC when DSP offloading is not desired for specific operations.

---

## 4. Common Issues

### Hexagon SDK Environment Not Set

**Issue:** Build fails with missing `HEXAGON_SDK_ROOT` or include errors.
**Resolution:** Source the SDK environment before building:
```sh
source ~/Qualcomm/Hexagon_SDK/3.4.3/setup_sdk_env.source
```

### DSP Performance vs CPU Performance

**Issue:** DSP-offloaded ECC operations are significantly slower than CPU-side NEON operations.
**Resolution:** This is expected. The Hexagon DSP excels at parallel workloads but has high per-call latency due to FastRPC overhead. Reference benchmarks show:
- CPU (ARM NEON): ~5,000 ECC-256 verifies in 1.4 seconds
- DSP (single-threaded, default handle): ~5,000 verifies in 17.5 seconds
- DSP (multi-threaded, 4 threads): ~20,000 verifies in 23.3 seconds

The DSP path is beneficial when the CPU is busy with other tasks or when parallel DSP threads can amortize the overhead. For pure throughput on a free CPU, the ARM NEON path is faster.

### Multi-Threading Handle Errors

**Issue:** Crashes or incorrect results when calling ECC verify from multiple threads.
**Resolution:** In multi-threaded mode, you must provide per-thread DSP handles. Either call `wc_ecc_set_handle()` on each `ecc_key` or register a callback via `wolfSSL_SetHandleCb()` that returns a unique handle per thread. The default handle uses mutex locking which serializes access.

### DSP Library Not Found on Device

**Issue:** Runtime error when wolfSSL tries to open the DSP connection.
**Resolution:** Ensure the skel library is pushed to the correct path:
```sh
adb push libwolfssl_dsp_skel.so /data/rfsa/adsp/
```
The path varies by DSP target (adsp, cdsp, etc.).

### Build Variant Mismatch

**Issue:** Linker errors when CPU and DSP builds use incompatible variants.
**Resolution:** Ensure both builds use matching Release/Debug modes. Use `./build.sh Release` or `./build.sh Debug` to build both consistently.

---

## 5. Example Configuration

The following `user_settings.h` enables DSP-offloaded ECC verify with ARM NEON fallback on the CPU side:

```c
/* user_settings.h — wolfSSL for Qualcomm Hexagon DSP */

#ifndef WOLFSSL_USER_SETTINGS_H
#define WOLFSSL_USER_SETTINGS_H

/* ---- Core ---- */
#define WOLFCRYPT_ONLY                 /* No TLS, crypto only */

/* ---- ECC ---- */
#define HAVE_ECC
#define FP_ECC
#define ECC_TIMING_RESISTANT

/* ---- Math ---- */
#define USE_FAST_MATH
#define TFM_TIMING_RESISTANT
#define WOLFSSL_HAVE_SP_RSA
#define WOLFSSL_HAVE_SP_ECC
#define WOLFSSL_SP_MATH

/* ---- ARM NEON (CPU side) ---- */
#define WOLFSSL_SP_ARM64_ASM

/* ---- Hexagon DSP Offloading ---- */
#define WOLFSSL_DSP

/* ---- Disable unused algorithms ---- */
#define NO_DSA
#define NO_DH
#define NO_RSA

#endif /* WOLFSSL_USER_SETTINGS_H */
```

**Multi-threaded usage example:**
```c
#include <wolfssl/wolfcrypt/ecc.h>

/* Callback to provide per-thread DSP handles */
int my_handle_cb(remote_handle64 *handle, int finished, void *ctx) {
    if (!finished) {
        /* Open or retrieve a per-thread handle */
        *handle = get_thread_local_handle();
    } else {
        /* Optionally release the handle */
    }
    return 0;
}

/* Register before use */
wolfSSL_SetHandleCb(my_handle_cb);
```

---

## 6. Additional Resources

- wolfSSL Hexagon README: `IDE/HEXAGON/README.md`
- wolfSSL DSP source: `wolfcrypt/src/wc_dsp.c`
- wolfSSL documentation: [https://www.wolfssl.com/documentation/](https://www.wolfssl.com/documentation/)

**Qualcomm Documentation:**
- Hexagon SDK: Available at [https://developer.qualcomm.com](https://developer.qualcomm.com) (requires free Qualcomm developer account for download)
- QuRT RTOS reference: Included with Hexagon SDK documentation (requires developer account)
- NPU SDK documentation: Partially available at [https://docs.qualcomm.com](https://docs.qualcomm.com) (public)
- FastRPC programming guide: Included in the Hexagon SDK under `docs/`

**Note on Documentation Availability:** QuRT internals and detailed DSP architecture documentation are scarce in public resources. The most detailed public information about Hexagon DSP internals has historically come from security researchers. The official Qualcomm developer documentation requires a free developer account to access but is comprehensive for SDK-level programming.

**Benchmark Reference (with -O3, single thread):**
- CPU (ARM NEON): ~3,572 ECC-256 verify ops/sec
- aDSP (default handle): ~286 ECC-256 verify ops/sec
- cDSP: ~269 ECC-256 verify ops/sec
- aDSP (4 threads parallel): ~860 ECC-256 verify ops/sec total
