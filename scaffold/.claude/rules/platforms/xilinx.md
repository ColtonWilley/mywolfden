---
paths:
  - "**/xilinx*"
  - "**/Xilinx*"
  - "**/Zynq*"
---

# Xilinx FPGA / SoC — wolfSSL Platform Guide

## 1. Overview

Xilinx (now AMD) produces a range of FPGAs and SoCs — including the Zynq-7000, Zynq UltraScale+ MPSoC, and Versal ACAP families — that are commonly used in embedded, industrial, and aerospace applications. These devices often combine programmable logic with hard processor cores (ARM Cortex-A/R/M) and dedicated security hardware.

wolfSSL supports Xilinx platforms through two complementary defines:

- **`WOLFSSL_XILINX`** — General platform support for building wolfSSL on Xilinx targets.
- **`WOLFSSL_XILINX_CRYPT`** — Enables integration with Xilinx hardened (hardware-accelerated) cryptographic engines, such as those found in the CSU/PMC security subsystems.

An additional sub-variant, **`WOLFSSL_XILINX_CRYPT_VERSAL`**, enables support specifically for the Versal ACAP platform, which uses a different hardware security interface (mailbox-based IPI communication via `xsecure_mailbox`) compared to earlier Zynq devices.

> **Note:** The source material available for this guide is limited to header-level definitions and port headers. For full build instructions, IDE project files, and detailed API usage, consult the [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/) and the `IDE/` directory in the wolfSSL source tree.

---

## 2. Build Configuration

### Key Defines

| Define | Purpose |
|---|---|
| `WOLFSSL_XILINX` | Enables general Xilinx platform support |
| `WOLFSSL_XILINX_CRYPT` | Enables Xilinx hardened crypto acceleration |
| `WOLFSSL_XILINX_CRYPT_VERSAL` | Enables Versal-specific hardware crypto (subset of `WOLFSSL_XILINX_CRYPT`) |
| `WOLFSSL_USER_SETTINGS` | Directs wolfSSL to use a `user_settings.h` file instead of `settings.h` macros |

### Configure Flags

No specific `./configure` flags are documented in the available source material for this platform. Xilinx targets are typically bare-metal or RTOS-based environments where the autoconf build system is not used. Configuration is instead done via `user_settings.h`.

### Recommended Build Approach

For Xilinx SDK / Vitis / PetaLinux projects, the standard approach is:

1. Add the wolfSSL source files directly to your project or as a library component.
2. Define `WOLFSSL_USER_SETTINGS` in your compiler preprocessor settings.
3. Create a `user_settings.h` file with the appropriate defines (see Section 5).

### Port Headers Location

Xilinx-specific port headers are located at:

```
wolfssl/wolfcrypt/port/xilinx/
  xil-sha3.h
  xil-versal-glue.h
  xil-versal-trng.h
```

These headers are included automatically when the relevant defines are active; you do not need to include them directly in application code.

---

## 3. Platform-Specific Features

### Hardware Cryptography

When `WOLFSSL_XILINX_CRYPT` is defined, wolfSSL routes cryptographic operations through the Xilinx secure hardware engines rather than the software implementations.

#### SHA-3 (`xil-sha3.h`)

- Activated when both `WOLFSSL_SHA3` and `WOLFSSL_XILINX_CRYPT` are defined.
- On **non-Versal** targets (e.g., Zynq UltraScale+ MPSoC), the `wc_Sha3` structure wraps the `XSecure_Sha3` hardware driver and an `XCsuDma` DMA instance. The Xilinx BSP header `<xsecure_sha.h>` is required.
- On **Versal** targets (`WOLFSSL_XILINX_CRYPT_VERSAL`), the `wc_Sha3` structure uses a `wc_Xsecure` context and communicates with the PLM security module via the Versal glue layer.

#### Versal TRNG (`xil-versal-trng.h`)

When `WOLFSSL_XILINX_CRYPT_VERSAL` is defined, wolfSSL provides access to the Versal True Random Number Generator (TRNG) through the following internal API:

```c
int wc_VersalTrngInit(byte* nonce, word32 nonceSz);
int wc_VersalTrngReset(void);
int wc_VersalTrngSelftest(void);
int wc_VersalTrngGenerate(byte *output, word32 sz);
```

These functions are marked `WOLFSSL_LOCAL` and are used internally by wolfSSL's random number subsystem. They are not intended to be called directly by application code.

#### Versal Glue Layer (`xil-versal-glue.h`)

The Versal glue layer (`WOLFSSL_XILINX_CRYPT_VERSAL`) provides:

- **Cache management macros** for DMA-coherent operation:
  - `WOLFSSL_XIL_DCACHE_INVALIDATE_RANGE(p, l)` — Invalidates a D-cache range before reading hardware output.
  - `WOLFSSL_XIL_DCACHE_FLUSH_RANGE(p, l)` — Flushes a D-cache range before passing data to hardware.
  - Both macros become no-ops when `XSECURE_CACHE_DISABLE` is defined.
- **`XIL_CAST_U64(v)`** — Casts a pointer to `u64` for use with Versal hardware interfaces.
- **`WOLFSSL_XIL_SLEEP(n)`** — Inserts a `sleep(n)` delay before debug messages to avoid interleaving with PLM console output. Active only when `DEBUG_WOLFSSL` is defined and `WOLFSSL_DEBUG_ERRORS_ONLY` / `WOLFSSL_XIL_MSG_NO_SLEEP` are not defined.
- Requires Xilinx BSP headers: `<xil_types.h>`, `<xsecure_mailbox.h>`, `<xsecure_defs.h>`.

### Threading

No threading-specific configuration is documented in the available source material for this platform. If running on a RTOS (e.g., FreeRTOS on Zynq), you will need to configure wolfSSL's mutex layer accordingly. Consult the wolfSSL Manual for RTOS threading integration details.

### Networking

No networking-specific configuration is documented in the available source material. wolfSSL's I/O layer will need to be connected to the appropriate network stack (e.g., lwIP on bare-metal Zynq). Consult the wolfSSL Manual for custom I/O callback configuration.

---

## 4. Common Issues

### Cache Coherency (Versal and UltraScale+)

Xilinx Cortex-A processors have data caches enabled by default. When passing buffers to hardware DMA engines, cache lines must be flushed before writes and invalidated after reads. The Versal glue layer provides `WOLFSSL_XIL_DCACHE_FLUSH_RANGE` and `WOLFSSL_XIL_DCACHE_INVALIDATE_RANGE` for this purpose. Failure to manage cache coherency will result in incorrect cryptographic output or hardware errors.

If your BSP is configured with `XSECURE_CACHE_DISABLE`, these macros become no-ops automatically.

### Debug Output Interleaving (Versal)

On Versal, the PLM (Platform Loader and Manager) may write to the same UART console as application code. When `DEBUG_WOLFSSL` is enabled, wolfSSL inserts a short `sleep()` before printing messages to reduce output interleaving. This behavior can be suppressed by defining `WOLFSSL_XIL_MSG_NO_SLEEP` or `WOLFSSL_DEBUG_ERRORS_ONLY`.

### BSP Header Dependencies

- Non-Versal `WOLFSSL_XILINX_CRYPT` builds require `<xsecure_sha.h>` from the Xilinx BSP.
- Versal `WOLFSSL_XILINX_CRYPT_VERSAL` builds require `<xil_types.h>`, `<xsecure_mailbox.h>`, and `<xsecure_defs.h>`.

Ensure the correct BSP libraries are included in your Vitis/SDK project and that include paths are configured to find these headers.

### Stack Size

Cryptographic operations, particularly TLS handshakes, require significant stack space. On bare-metal or RTOS configurations with limited stack, this is a common source of hard-to-diagnose failures. The wolfSSL Manual provides guidance on minimum stack requirements; check that your task/thread stack sizes are sufficient.

### Selecting the Correct Variant

Do not define both `WOLFSSL_XILINX_CRYPT` (non-Versal path) and `WOLFSSL_XILINX_CRYPT_VERSAL` for a non-Versal target. The Versal path uses a different hardware interface (IPI mailbox) that is not present on Zynq-7000 or UltraScale+ MPSoC devices.

---

## 5. Example Configuration

The following is a minimal `user_settings.h` for a Xilinx Versal target using hardened crypto. Adjust feature flags to match your application's requirements.

```c
/* user_settings.h — wolfSSL for Xilinx Versal (example) */

#ifndef WOLFSSL_USER_SETTINGS_H
#define WOLFSSL_USER_SETTINGS_H

/* ---- Platform ---- */
#define WOLFSSL_XILINX
#define WOLFSSL_XILINX_CRYPT
#define WOLFSSL_XILINX_CRYPT_VERSAL   /* Remove for non-Versal targets */

/* ---- Core TLS ---- */
#define WOLFSSL_TLS13
#define NO_OLD_TLS                    /* Disable SSLv3/TLS 1.0/1.1 */

/* ---- Algorithms ---- */
#define WOLFSSL_SHA3                  /* Enable SHA-3 (uses Xilinx HW) */
#define HAVE_AES_CBC
#define HAVE_AESGCM
#define HAVE_ECC
#define HAVE_CURVE25519
#define NO_DSA                        /* Disable DSA if not needed */
#define NO_RC4

/* ---- RNG ---- */
/* Versal TRNG is used automatically when WOLFSSL_XILINX_CRYPT_VERSAL
 * is defined. No additional define is required for the RNG. */

/* ---- Memory ---- */
/* Optionally define custom malloc/free if not using standard heap */
/* #define XMALLOC_USER */

/* ---- Debug (optional) ---- */
/* #define DEBUG_WOLFSSL */
/* #define WOLFSSL_XIL_MSG_NO_SLEEP */ /* Suppress sleep before debug msgs */

#endif /* WOLFSSL_USER_SETTINGS_H */
```

For a **non-Versal Zynq UltraScale+ MPSoC** target, remove `WOLFSSL_XILINX_CRYPT_VERSAL` and ensure your BSP provides `<xsecure_sha.h>` and the CSU DMA driver.

## 6. Additional Resources

### Vendor Documentation (Public — Excellent Availability)

#### xilsecure Library

- **AMD Adaptive Computing Wiki**: [xilinx-wiki.atlassian.net/wiki/spaces/A/pages/18842278/xilsecure+Library](https://xilinx-wiki.atlassian.net/wiki/spaces/A/pages/18842278/xilsecure+Library)
- **Covers**: SHA-3 hashing, AES-GCM encryption/decryption, RSA-4096/RSA-2048 authentication
- **Standalone Library Documentation** (full API reference PDF): [xilinx.com/support/documents/sw_manuals/xilinx2022_2/oslib_rm.pdf](https://www.xilinx.com/support/documents/sw_manuals/xilinx2022_2/oslib_rm.pdf)

#### Secure Boot & Design Tutorials

- **Embedded Design Tutorials (GitHub Pages)**: [xilinx.github.io/Embedded-Design-Tutorials/docs/2023.1/build/html/docs/Introduction/ZynqMPSoC-EDT/9-secure-boot.html](https://xilinx.github.io/Embedded-Design-Tutorials/docs/2023.1/build/html/docs/Introduction/ZynqMPSoC-EDT/9-secure-boot.html)
- **Zynq UltraScale+ MPSoC Software Developer Guide (PDF)**: [xilinx.com/support/documents/sw_manuals/xilinx2022_2/ug1137-zynq-ultrascale-mpsoc-swdev.pdf](https://www.xilinx.com/support/documents/sw_manuals/xilinx2022_2/ug1137-zynq-ultrascale-mpsoc-swdev.pdf)

#### PUF (Physically Unclonable Function)

- PUF key documentation is included in the xilsecure library wiki and the Software Developer Guide
- Enables device-unique key generation for secure boot and key storage

---

> **Further Reading:** For complete build instructions, example projects, and additional configuration options, refer to the [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/) and the `IDE/` directory within the wolfSSL source distribution. The wolfSSL team also provides commercial support for Xilinx platform integration.
