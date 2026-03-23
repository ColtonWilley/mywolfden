---
paths:
  - "**/nxp*"
  - "**/NXP*"
  - "**/CSE*"
  - "**/HSE*"
---

# NXP (i.MX, CAAM, SE050) — wolfSSL Platform Guide

## 1. Overview

NXP produces a family of processors and secure elements that wolfSSL supports through dedicated port layers. The primary targets covered in this guide are:

- **i.MX processors** (i.MX6, i.MX8, and variants) running Linux, QNX, or INTEGRITY, with access to the on-chip **CAAM** (Cryptographic Acceleration and Assurance Module)
- **SE050** — NXP's EdgeLock secure element, connected via I2C, providing hardware-backed key storage and cryptographic operations
- **DCP** (Data Co-Processor) and **LTC** (Low-power Trusted Cryptography) peripherals available on some Kinetis/i.MX RT devices, supported via the KSDK port layer

wolfSSL provides dedicated port headers under `wolfssl/wolfcrypt/port/caam/` and `wolfssl/wolfcrypt/port/nxp/` for these targets.

---

## 2. Build Configuration

### 2.1 Key Preprocessor Defines

| Define | Purpose |
|---|---|
| `WOLFSSL_CAAM` | Master enable for CAAM hardware acceleration |
| `WOLFSSL_IMX6_CAAM` | Enable CAAM support on i.MX6 targets |
| `WOLFSSL_CAAM_IMX6Q` | Selects i.MX6Q-specific CAAM base addresses |
| `WOLFSSL_QNX_CAAM` | CAAM support under QNX OS |
| `WOLFSSL_SECO_CAAM` | Enable CAAM via NXP SECO (Security Controller) |
| `WOLFSSL_SECO` | Alias/companion define for SECO-based CAAM |
| `WOLFSSL_SE050` | Enable NXP SE050 secure element support |
| `WOLFSSL_SE050_HASH` | Offload hash operations to SE050 |
| `WOLFSSL_CAAM_BLOB` | Enable CAAM black key / blob support (optional) |
| `WOLFSSL_LP_ONLY_CAAM_AES` | Restrict to low-power AES module only (no GCM) |
| `WOLFSSL_NO_CAAM_ECC` | Disable CAAM ECC (required when hardware lacks it) |
| `WOLFSSL_NO_CAAM_BLOB` | Disable CAAM blob support (required for SECO) |
| `WOLFSSL_HASH_KEEP` | Keep hash data for SECO CAAM (required for SECO) |

> **Note:** `WOLFSSL_CAAM_BLOB` and `WOLFSSL_CAAM` are commented out in `settings.h` as optional — they must be explicitly enabled for `WOLFSSL_IMX6_CAAM` or `WOLFSSL_QNX_CAAM` builds.

### 2.2 Configure Flags

```bash
# Enable CAAM (generic)
./configure --enable-caam

# Enable CAAM for specific targets (comma-separated variants)
./configure --enable-caam=qnx
./configure --enable-caam=imx6q

# Enable SE050 secure element
./configure --enable-se050
```

When `--enable-caam` is passed, the build system adds `-DWOLFSSL_CAAM` to `AM_CFLAGS`. Sub-variants such as `qnx` add `-DWOLFSSL_QNX_CAAM` and `imx6q` adds `-DWOLFSSL_IMX6Q_CAAM`.

### 2.3 CAAM Base Addresses (from `caam_driver.h`)

wolfSSL selects CAAM memory-mapped base addresses automatically based on the target:

| Target | `CAAM_BASE` | `CAAM_PAGE` |
|---|---|---|
| INTEGRITY / i.MX (32-bit default) | `0xf2100000` | `0xf0100000` |
| AArch64 (assumed i.MX8 QXP) | `0x31400000` | `0x31800000` |
| i.MX6Q (`WOLFSSL_CAAM_IMX6Q`) | `0x02100000` | `0x00100000` |
| i.MX6UL (default 32-bit) | `0x02140000` | `0x00100000` |

These can be overridden by defining `CAAM_BASE` before including the driver header.

### 2.4 Port Header Locations

```
wolfssl/wolfcrypt/port/caam/
    caam_driver.h       # Low-level CAAM driver, base addresses, job ring
    caam_error.h        # CAAM error parsing functions
    caam_qnx.h          # QNX-specific CAAM register access and mutex wrappers
    wolfcaam.h          # Top-level CAAM wolfSSL integration
    wolfcaam_aes.h      # AES via CAAM
    wolfcaam_cmac.h     # CMAC via CAAM
    wolfcaam_ecdsa.h    # ECDSA via CAAM
    wolfcaam_fsl_nxp.h  # FSL/NXP-specific CAAM integration
    wolfcaam_hash.h     # Hash via CAAM
    wolfcaam_rsa.h      # RSA via CAAM
    wolfcaam_seco.h     # SECO-specific CAAM integration
    wolfcaam_sha.h      # SHA via CAAM
    wolfcaam_x25519.h   # X25519 via CAAM

wolfssl/wolfcrypt/port/nxp/
    dcp_port.h          # DCP (Data Co-Processor) AES and SHA acceleration
    ksdk_port.h         # Kinetis SDK port (LTC, ECC, Curve25519, Ed25519)
    se050_port.h        # SE050 secure element port
```

---

## 3. Platform-Specific Features

### 3.1 CAAM Hardware Acceleration

The CAAM module on i.MX processors provides hardware acceleration for:

- **AES** (CBC, ECB; GCM availability depends on variant — see notes below)
- **CMAC**
- **ECDSA**
- **RSA**
- **SHA / Hash operations**
- **X25519**
- **Black key / Blob encapsulation** (when `WOLFSSL_CAAM_BLOB` is defined)

The CAAM driver uses a job ring model. The default job ring size is 1 (`CAAM_JOBRING_SIZE`), which can be overridden. The maximum CAAM descriptor size is 256 bytes (`CAAM_DESC_MAX`).

#### SECO CAAM Restrictions

When building with `WOLFSSL_SECO_CAAM`:

- `WOLFSSL_HASH_KEEP` is automatically defined (required for SECO hash operations)
- `WOLFSSL_NO_CAAM_BLOB` is automatically defined (SECO does not support blob operations)
- `WOLFSSL_CAAM` is automatically defined

#### Low-Power AES Restriction

When `WOLFSSL_LP_ONLY_CAAM_AES` is defined (e.g., on hardware with only the low-power AES module):

- AES-GCM via CAAM is disabled
- CAAM ECC is disabled (`WOLFSSL_NO_CAAM_ECC`)

### 3.2 SE050 Secure Element

The SE050 port (`wolfssl/wolfcrypt/port/nxp/se050_port.h`) integrates with NXP's SSS (Secure Service Stack) APIs:

- Requires `fsl_sss_se05x_types.h`, `fsl_sss_se05x_apis.h`, and `se05x_APDU.h` from the NXP SE05x middleware
- Provides hardware-backed key storage with default key slot IDs:

| Key Type | Default Key ID |
|---|---|
| AES | 55 |
| Ed25519 | 58 |
| Curve25519 | 59 |
| ECC | 60 |

These defaults can be overridden by defining the corresponding macros before including `se050_port.h`.

#### SE050 Hash Limitations

When `WOLFSSL_SE050` and `WOLFSSL_SE050_HASH` are both defined:

- `WOLFSSL_NOSHA512_224` is automatically defined
- `WOLFSSL_NOSHA512_256` is automatically defined
- `WOLFSSL_NO_HASH_RAW` is unconditionally defined

This means SHA-512/224 and SHA-512/256 truncated variants are not supported through the SE050 hash offload path.

#### SE050 ECC Compatibility

When `WOLFSSL_SE050` is defined, `USE_ECC_B_PARAM` is **not** automatically enabled (it is explicitly excluded from the OpenSSL-extra ECC B-parameter logic). Verify ECC curve compatibility with your SE050 firmware version.

### 3.3 DCP (Data Co-Processor)

Available on select i.MX RT and Kinetis devices. Provides:

- AES-CBC encrypt/decrypt (`DCPAesCbcEncrypt`, `DCPAesCbcDecrypt`)
- AES-ECB encrypt/decrypt (when `HAVE_AES_ECB` is defined)
- SHA-256 (`DCPSha256Free`)
- SHA-1 (`DCPShaFree`)

Requires `fsl_dcp.h` from the NXP SDK. Initialize with `wc_dcp_init()`.

### 3.4 KSDK Port (LTC / Kinetis)

The KSDK port (`ksdk_port.h`) supports:

- LTC-accelerated big-integer math (`FREESCALE_LTC_TFM`): `mp_mul`, `mp_mod`, `mp_mulmod`, `mp_invmod`, `mp_exptmod`
- LTC-accelerated ECC (`FREESCALE_LTC_ECC`) using Weierstrass coordinates via `fsl_ltc.h`
- Curve25519 and Ed25519 hardware support

Initialize with `ksdk_port_init()`.

### 3.5 Threading (QNX CAAM)

On QNX, the CAAM driver uses POSIX pthreads for mutual exclusion:

```c
#define CAAM_MUTEX          pthread_mutex_t
#define CAAM_INIT_MUTEX(x)  pthread_mutex_init((x), NULL)
#define CAAM_FREE_MUTEX(x)  pthread_mutex_destroy((x))
#define CAAM_LOCK_MUTEX(x)  pthread_mutex_lock((x))
#define CAAM_UNLOCK_MUTEX(x) pthread_mutex_unlock((x))
```

The QNX CAAM layer also calls `sched_yield()` (`CAAM_CPU_CHILL()`) to yield to same-priority threads while waiting on the hardware.

---

## 4. Common Issues

### 4.1 CAAM_BLOB / WOLFSSL_CAAM Not Enabled by Default

In `settings.h`, both `WOLFSSL_CAAM` and `WOLFSSL_CAAM_BLOB` are commented out under the `WOLFSSL_IMX6_CAAM` / `WOLFSSL_QNX_CAAM` section. You must explicitly define these in your build system or `user_settings.h` if blob/black key support is needed.

### 4.2 SECO Incompatibility with Blob Operations

`WOLFSSL_SECO_CAAM` automatically sets `WOLFSSL_NO_CAAM_BLOB`. Do not attempt to use CAAM blob operations when targeting SECO — they are not supported by the SECO security controller.

### 4.3 AES-GCM Unavailable on Low-Power CAAM

If your i.MX variant only has the low-power AES module, `WOLFSSL_LP_ONLY_CAAM_AES` must be defined. This disables AES-GCM and ECC through CAAM. Software fallback will be used for these operations if the software implementations are not also disabled.

### 4.4 SE050 SHA-512 Truncated Variants

SHA-512/224 and SHA-512/256 are automatically disabled when using SE050 hash offload. If your application requires these variants, do not define `WOLFSSL_SE050_HASH`, or handle them in software separately.

### 4.5 SE050 Raw Hash Disabled

`WOLFSSL_NO_HASH_RAW` is unconditionally defined in `se050_port.h`. Any wolfSSL feature that depends on raw (non-finalized) hash access will not be available when the SE050 port header is included.

### 4.6 i.MX8 AArch64 Assumptions

The CAAM driver assumes that any AArch64 system is an i.MX8 QXP and uses job ring 2 memory (`CAAM_BASE 0x31400000`). If you are targeting a different AArch64 i.MX8 variant, override `CAAM_BASE` and `CAAM_PAGE` explicitly in your build configuration.

### 4.7 SE050 Middleware Dependency

The SE050 port requires NXP's SE05x middleware headers (`fsl_sss_se05x_types.h`, `fsl_sss_se05x_apis.h`, `se05x_APDU.h`). These are not included with wolfSSL and must be obtained separately from NXP's SE05x SDK. The `SSS_HAVE_SSS` macro controls inclusion of the generic SSS API layer.

### 4.8 CAAM Job Ring Size

The default `CAAM_JOBRING_SIZE` is 1. For higher-throughput applications, this may be a bottleneck. Override this define in your build if your platform and OS support larger job rings.

---

## 5. Example Configuration

### 5.1 Configure Command — i.MX6 with CAAM

```bash
./configure \
    --enable-caam=imx6q \
    --enable-cmac \
    CFLAGS="-DWOLFSSL_IMX6_CAAM -DWOLFSSL_CAAM -DWOLFSSL_CAAM_BLOB"
```

### 5.2 Configure Command — SE050

```bash
./configure \
    --enable-se050 \
    --enable-ecc \
    CFLAGS="-DWOLFSSL_SE050"
```

### 5.3 Minimal `user_settings.h` — i.MX6Q CAAM

```c
/* user_settings.h — i.MX6Q CAAM example */

/* Platform */
#define WOLFSSL_IMX6_CAAM
#define WOLFSSL_CAAM_IMX6Q

/* Enable CAAM hardware acceleration */
#define WOLFSSL_CAAM
/* Optional: enable black key / blob support */
/* #define WOLFSSL_CAAM_BLOB */

/* Algorithms to accelerate via CAAM */
#define HAVE_AES_CBC
#define WOLFSSL_CMAC
#define HAVE_ECC
#define WOLFSSL_AES_SIV

/* Additional options from settings.h defaults for this platform */
#define WOLFSSL_CERT_PIV
#define HAVE_X963_KDF
```

### 5.4 Minimal `user_settings.h` — SE050

```c
/* user_settings.h — SE050 example */

/* Enable SE050 secure element */
#define WOLFSSL_SE050

/* Enable SE050 hash offload (optional — disables SHA-512/224 and SHA-512/256) */
/* #define WOLFSSL_SE050_HASH */

/* ECC support (required for SE050 ECC key operations) */
#define HAVE_ECC

/* Ed25519 / Curve25519 if needed */
#define HAVE_ED25519
#define HAVE_CURVE25519

/* Override default SE050 key slot IDs if needed */
/* #define SE050_KEYSTOREID_ECC     60 */
/* #define SE050_KEYSTOREID_ED25519 58 */
```

---

## 6. Additional Resources

### Vendor Documentation (Public)

**SE050 (Public — GitHub BSD-3-Clause)**:
- NXP Plug and Trust middleware: github.com/NXP/plug-and-trust — full SE050 APIs, SSS APIs, protocol stack
- APDU specification: nxp.com/docs/en/application-note/AN12413.pdf
- Nano package: github.com/NXPPlugNTrust/nano-package
- wolfSSL SE050 examples: see wolfssl-examples/SE050/ in the wolfSSL examples repository

**CAAM SDK-level Documentation (Public)**:
- MCUXpresso CAAM API docs (no registration): mcuxpresso.nxp.com/api_doc — covers Init, AES, DES, HASH, RNG, PKHA drivers
- Linux kernel CAAM driver source: drivers/crypto/caam/ in mainline Linux
- Key blob utilities: github.com/usbarmory/caam-keyblob

**CAAM Deep Documentation (NDA Required)**:
- i.MX Security Reference Manuals (register-level CAAM, SNVS, secure boot fuse maps) require NDA via NXP FAE or distributor
- The MCUXpresso SDK API and Linux kernel source effectively document most practical register interfaces
- Older i.MX6 SRMs have appeared on community forums

**Internal wolfSSL Integration Code**:
- examples-private contains NXP CSE (Cryptographic Services Engine) and HSE-B (Hardware Security Engine) integration code with READMEs, test benchmarks, and source
