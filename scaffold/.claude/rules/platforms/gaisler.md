---
paths:
  - "**/gaisler*"
  - "**/sparc*"
---

# Gaisler LEON3/4 SPARC — wolfSSL Platform Guide

## 1. Overview

wolfSSL supports the Gaisler LEON range of SPARC V8 processors, including LEON3 and LEON4, through the BCC2 (Bare-C Cross-Compiler) toolchain. The port is documented under `IDE/Gaisler-BCC/` and supports both bare-metal and Linux targets.

Gaisler LEON3 and LEON4 are radiation-hardened SPARC processors used primarily in space, aerospace, and high-reliability embedded applications. They are implemented as synthesizable VHDL IP cores in the GRLIB library and are available in both FPGA and ASIC form factors. The GR740 is a common quad-core LEON4 SoC used in European Space Agency missions.

wolfSSL builds for this target using standard `./configure` with SPARC cross-compilation. The only platform-specific define is `WOLFSSL_GAISLER_BCC`, which provides timer integration for the wolfCrypt benchmark.

**Port files:**
- `IDE/Gaisler-BCC/README.md` — Build instructions for bare-metal and Linux
- No dedicated port headers or source files in `wolfssl/wolfcrypt/port/`

**Note:** There are no LEON, SPARC, or GAISLER defines in `settings.h`. The `WOLFSSL_GAISLER_BCC` define is only used in `wolfcrypt/benchmark/benchmark.c` for the `current_time()` implementation using `bcc/bcc.h` timer APIs.

---

## 2. Build Configuration

### Bare-Metal (BCC2)

**Step 1:** Create a `user_settings.h` in the wolfSSL source root by copying `examples/config/user_settings_template.h` and adding:

```c
#define WOLFSSL_GAISLER_BCC
#define WOLFSSL_GENSEED_FORTEST
#define NO_ASN_TIME
```

Also uncomment (enable) `NO_MAIN_DRIVER` — the README instructs commenting out this line, meaning it should **not** be defined (allowing wolfCrypt test/benchmark to provide `main()`).

**Step 2:** Configure and build with BCC2:

```sh
export CC=/opt/sparc-bcc-2.3.1-gcc/bin/sparc-gaisler-elf-gcc
export CXX=/opt/sparc-bcc-2.3.1-gcc/bin/sparc-gaisler-elf-g++
export CFLAGS="-qbsp=gr740 -mcpu=leon3"

./configure --host=sparc --enable-usersettings --disable-examples --enable-static
make
```

Adjust `-qbsp` and `-mcpu` for your specific board and LEON version:
- `-mcpu=leon3` for LEON3 processors
- `-mcpu=leon` for older LEON2
- `-qbsp=gr740` for the GR740 quad-core board (adjust to match your BSP)

Both GCC and CLang versions of BCC2 are supported. When using CLang, add `-std=c99` to CFLAGS.

### Linux Target

For LEON running Linux, use the Gaisler GNU Linux toolchain:

```sh
export CC=/opt/sparc-gaisler-linux5.10/bin/sparc-gaisler-linux5.10-gcc
export CXX=/opt/sparc-gaisler-linux5.10/bin/sparc-gaisler-linux5.10-g++
export CFLAGS="-mcpu=leon3"

./configure --host=sparc-linux
make
```

No `user_settings.h` is needed for the Linux target — the standard configure build system handles everything.

### Key Defines

| Define | Purpose |
|--------|---------|
| `WOLFSSL_GAISLER_BCC` | Enables BCC timer for wolfCrypt benchmark `current_time()`. Uses `bcc_timer_get_us()` from `<bcc/bcc.h>`. Only needed if running the wolfCrypt benchmark. |
| `WOLFSSL_GENSEED_FORTEST` | Uses a deterministic seed for the RNG. **Required for bare-metal testing only** — NOT suitable for production. |
| `NO_ASN_TIME` | Disables ASN time validation. Needed when no RTC or time source is available. |

---

## 3. Platform-Specific Features

### No Hardware Crypto Acceleration

wolfSSL does not provide hardware-accelerated cryptography for LEON processors. All cryptographic operations use software implementations. The SPARC V8 architecture does not include crypto instructions, so SP math or fast math with standard C implementations is the typical configuration.

### Benchmark Timer

The `WOLFSSL_GAISLER_BCC` define provides a `current_time()` implementation using the BCC timer:

```c
#include <bcc/bcc.h>
double current_time(int reset) {
    (void)reset;
    uint32_t us = bcc_timer_get_us();
    return (double)us / 1000000.0;
}
```

This is only relevant for running the wolfCrypt benchmark application.

### Entropy / RNG

Most Gaisler LEON processors do not include a hardware TRNG. For bare-metal targets, `WOLFSSL_GENSEED_FORTEST` provides a deterministic seed suitable for testing only. **For production deployments, an external entropy source must be provided.** Options include:

- External hardware RNG connected via a GRLIB peripheral
- Network-based entropy (NTP jitter, etc.) if running Linux
- Custom `CUSTOM_RAND_GENERATE_BLOCK` implementation connected to your entropy source

### Cross-Compilation Notes

The SPARC V8 architecture is 32-bit big-endian. wolfSSL's configure system correctly detects this when `--host=sparc` is used. Key characteristics:

- Big-endian byte order (affects AES, SHA implementations)
- 32-bit `long`, 64-bit `long long`
- No hardware floating point on most LEON variants (though GRFPU is available on some)
- Stack grows downward, standard SPARC register windowing

---

## 4. Common Issues

### No Entropy Source for Production

**Issue:** `WOLFSSL_GENSEED_FORTEST` is defined in the test configuration, but this produces deterministic (insecure) random numbers.
**Resolution:** For production, remove `WOLFSSL_GENSEED_FORTEST` and provide a proper entropy source via `CUSTOM_RAND_GENERATE_BLOCK` or a hardware RNG peripheral. This is the most critical issue for space/aerospace deployments where cryptographic randomness is essential.

### Missing BSP for Board

**Issue:** Build fails with linker errors about missing BSP symbols.
**Resolution:** Ensure `-qbsp=<board>` matches your actual board. Available BSPs are listed in the BCC2 installation under the BSP directory. Common values include `gr740`, `gr712rc`, and `leon3`.

### Time Source for Certificate Validation

**Issue:** TLS certificate validation fails because no real-time clock is available.
**Resolution:** For bare-metal, define `NO_ASN_TIME` to disable time-based certificate checks. For Linux targets, the kernel's timekeeping handles this automatically. If a mission time source is available, implement `XTIME` to provide epoch-based timestamps.

### CLang Mode Requires C99

**Issue:** Build errors with the CLang version of BCC2.
**Resolution:** Add `-std=c99` to CFLAGS. The CLang-based BCC2 defaults to a stricter C standard mode than GCC.

### Stack Size on Bare-Metal

**Issue:** Stack overflow during TLS handshake or cryptographic operations.
**Resolution:** LEON bare-metal BSPs often have limited default stack sizes. wolfSSL TLS operations typically require 4-8 KB of stack. If using `WOLFSSL_SMALL_STACK`, large temporaries are moved to heap, reducing stack requirements. Adjust the linker script or BSP configuration to provide adequate stack.

### 32-bit Math Performance

**Issue:** RSA and DH operations are slow on LEON3.
**Resolution:** SPARC V8 is 32-bit without hardware multiply for large operands on some variants. Use SP math (`WOLFSSL_SP_MATH_ALL` with `WOLFSSL_SP_SMALL`) for best performance on constrained SPARC targets. ECC with P-256 is significantly faster than RSA-2048 on this architecture.

---

## 5. Example Configuration

### Bare-Metal (Testing)

```c
/* user_settings.h — wolfSSL for Gaisler LEON3/4 bare-metal */

#ifndef WOLFSSL_USER_SETTINGS_H
#define WOLFSSL_USER_SETTINGS_H

/* ---- Platform ---- */
#define WOLFSSL_GAISLER_BCC            /* BCC timer for benchmark */
#define SINGLE_THREADED                /* No RTOS on bare-metal */
#define NO_FILESYSTEM
#define NO_WRITEV

/* ---- RNG ---- */
#define WOLFSSL_GENSEED_FORTEST        /* TESTING ONLY — replace for production */
/* For production, remove above and define:
 * #define CUSTOM_RAND_TYPE unsigned int
 * #define CUSTOM_RAND_GENERATE_BLOCK my_hw_rng_block
 */

/* ---- Time ---- */
#define NO_ASN_TIME                    /* No RTC available */
/* #define USER_TIME */                /* Or provide custom time() */

/* ---- Math ---- */
#define WOLFSSL_SP_MATH_ALL
#define WOLFSSL_SP_SMALL               /* Smaller code, acceptable speed */

/* ---- Cryptography ---- */
#define HAVE_ECC
#define ECC_TIMING_RESISTANT
#define HAVE_AES_CBC
#define HAVE_AESGCM
#define GCM_SMALL
#define WC_RSA_BLINDING

/* ---- Hashing ---- */
/* SHA-1, SHA-256 enabled by default */
#define HAVE_HKDF

/* ---- Reduce footprint ---- */
#define WOLFSSL_SMALL_STACK
#define NO_DES3
#define NO_RC4
#define NO_MD4
#define NO_PSK
#define NO_DSA

/* ---- Testing ---- */
#define BENCH_EMBEDDED
#define USE_CERT_BUFFERS_256
#define USE_CERT_BUFFERS_2048

#endif /* WOLFSSL_USER_SETTINGS_H */
```

### Linux Target

No `user_settings.h` needed. Use the standard configure build:

```sh
export CC=/opt/sparc-gaisler-linux5.10/bin/sparc-gaisler-linux5.10-gcc
export CFLAGS="-mcpu=leon3"
./configure --host=sparc-linux \
    --enable-ecc --enable-aesgcm --enable-tls13 \
    --disable-des3 --disable-oldtls
make
```

---

## 6. Additional Resources

- wolfSSL Gaisler BCC README: `IDE/Gaisler-BCC/README.md`
- wolfSSL documentation: [https://www.wolfssl.com/documentation/](https://www.wolfssl.com/documentation/)

**Gaisler / Cobham Documentation (Public -- no authentication required):**
- BCC2 compiler user's manual: [https://download.gaisler.com/anonftp/bcc/doc/bcc.pdf](https://download.gaisler.com/anonftp/bcc/doc/bcc.pdf)
- BCC2 compiler downloads: [https://www.gaisler.com/index.php/downloads/compilers](https://www.gaisler.com/index.php/downloads/compilers)
- GNU Linux toolchains for LEON/NOEL: [https://www.gaisler.com/index.php/downloads/linux](https://www.gaisler.com/index.php/downloads/linux)
- GRLIB VHDL IP Core Library Guide: [https://gaisler.com/products/grlib/guide.pdf](https://gaisler.com/products/grlib/guide.pdf) (updated October 2025)
- LEON3 product page: [https://gaisler.com/products/leon3](https://gaisler.com/products/leon3)

**Community Resources:**
- GRLIB community mirror: [https://github.com/trondd/grlib](https://github.com/trondd/grlib)
- GRLIB IP cores require a license for commercial use, but documentation is freely available

**Architecture Notes:**
- LEON3/4 are SPARC V8 (32-bit, big-endian)
- Radiation-hardened variants available for space qualification (ESA ECSS standards)
- GR740 is a quad-core LEON4 SoC commonly used in European space missions
- GRFPU (hardware floating point) is optional and varies by implementation
