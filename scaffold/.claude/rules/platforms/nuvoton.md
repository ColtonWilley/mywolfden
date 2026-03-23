---
paths:
  - "**/nuvoton*"
  - "**/Nuvoton*"
  - "**/NPCT*"
---

# Nuvoton NPCT7xx TPM 2.0 — wolfSSL Platform Guide

## 1. Overview

Nuvoton Technology produces the NPCT7xx series of TPM 2.0 modules, which are among the most widely deployed hardware TPMs in embedded and PC platforms. wolfSSL's **wolfTPM** library provides direct, first-class support for Nuvoton NPCT75x and NPCT76x modules through the `WOLFTPM_NUVOTON` define.

wolfTPM implements the TCG TPM 2.0 specification in a portable C library and includes Nuvoton-specific vendor commands for configuration (`NTC2_PreConfig`, `NTC2_GetConfig`) and GPIO control. The Nuvoton modules communicate over SPI with wait state support and operate at up to 43 MHz.

There are no Nuvoton-specific defines in the wolfSSL `settings.h` — the integration is entirely through the wolfTPM library. wolfSSL is used by wolfTPM as the underlying cryptographic library for TLS and certificate operations.

### Nuvoton TPM Modules Supported

| Module | Description |
|---|---|
| NPCT75x | TPM 2.0 SPI module (most common variant) |
| NPCT76x | TPM 2.0 module (newer revision) |
| NPCT65x | Older TPM module (co-layout compatible with NPCT75x) |

### Vendor Documentation Available

The `examples-private/nuvoton/` repository contains extensive Nuvoton vendor documentation:

**Datasheets and Programming Guides:**
- `NPCT7xx_TPM2.0_DS_Rev1.21.pdf` / `NPCT7xx_TPM2.0_DS_Rev1.23.pdf` — NPCT7xx TPM 2.0 Datasheets
- `NPCT7xx_TPM2 0_ProgGuide_Rev.1.6.pdf` / `NPCT7xx_TPM2 0_ProgGuide_Rev.1.8.pdf` — TPM 2.0 Programming Guides
- `NPCT75x_TPM1.2_ProgGuide_Rev.1.3.pdf` — TPM 1.2 Programming Guide (legacy reference)

**Guidance and Design Documents:**
- `NPCT75xAC TPM 20 Guidance_Rev1.1.pdf` — TPM 2.0 Guidance for NPCT75xAC
- `NPCT75xxAB_D & NPCT76xxAA TPM 20 Guidance v1.5.pdf` / `v1.6.pdf` — Guidance for NPCT75xx/NPCT76xx variants
- `NPCT75x_Guidance_TPM_1_2_1.2.pdf` — Legacy TPM 1.2 guidance
- `NPCT75x_Board_Design_Guide_Rev1.3.pdf` — Hardware board design guide
- `NPCT75x_Reference_Schematics_14.pdf` — Reference schematic designs
- `NPCT65X-NPCT75X_CO-LAYOUT_11.pdf` — Co-layout guide for NPCT65x/NPCT75x migration

**Errata and Security:**
- `NPCT75x_TPM2.0_Errata_Rev2.9.pdf` / `NPCT7xx_TPM2.0_Errata_Rev2.10.pdf` — Known errata
- `NPCT75x_Errata_Samples_Rev1.2.pdf` — Sample-specific errata
- `NPCT7xx_TPM2.0_rev1.38_FIPS_Security_Policy_v1.0.5.pdf` — FIPS 140-2 Security Policy

**Evaluation Board Guides:**
- `NPCT7xx_EB_UG_SPI_Rev1.1.pdf` — Evaluation Board User Guide (SPI)
- `NPCT7xx_Raspberry-Pi_EB_UG_SPI_I2C_Rev1.0.pdf` — Raspberry Pi Evaluation Board Guide (SPI/I2C)

**EK Certificate Chain:**
- `Nuvoton_TPM_EK_Certificate_Chain_Rev1.0.pdf` / `Rev1.4.pdf` — Endorsement Key certificate chain documentation
- `NPCT75x_PB_Rev1.6.pdf` — Product brief

---

## 2. Build Configuration

### wolfTPM Build with Nuvoton Support

#### Configure Flags

```bash
# Enable Nuvoton NPCT65x/NPCT75x TPM support
./configure --enable-nuvoton

# With wolfSSL installed (required dependency)
./configure --enable-nuvoton --with-wolfssl=/usr/local
```

When `--enable-nuvoton` is passed, the build system adds `-DWOLFTPM_NUVOTON` to `AM_CFLAGS`.

If no specific TPM module is selected, wolfTPM can auto-detect the TPM at runtime (using `--enable-autodetect` or by not specifying any module). Auto-detection requires SPI wait state support and uses a safe 33 MHz SPI bus speed.

### Key Preprocessor Defines

| Define | Purpose |
|---|---|
| `WOLFTPM_NUVOTON` | Enable Nuvoton NPCT75x TPM 2.0 module support |
| `WOLFTPM_CHECK_WAIT_STATE` | Enable SPI wait state checking (auto-set for Nuvoton) |
| `TPM2_SPI_MAX_HZ` | SPI bus frequency limit (default: 43 MHz for Nuvoton) |
| `TPM_GPIO_COUNT` | Number of user-controllable GPIO pins (default: 2, max: 2) |
| `WOLFTPM_AUTODETECT` | Enable runtime TPM module auto-detection |

### SPI Configuration

When `WOLFTPM_NUVOTON` is defined, the following defaults are applied automatically in `wolftpm/tpm2_types.h`:

```c
/* SPI wait state checking is required */
#define WOLFTPM_CHECK_WAIT_STATE

/* Maximum SPI clock: 43 MHz */
#define TPM2_SPI_MAX_HZ_NUVOTON 43000000
#define TPM2_SPI_MAX_HZ          TPM2_SPI_MAX_HZ_NUVOTON
```

On Linux with SPI device access, the Nuvoton module uses chip select CE0:

```c
#define TPM2_SPI_DEV_CS "0"  /* /dev/spidev0.0 */
```

### wolfSSL Dependency

wolfTPM requires wolfSSL as a cryptographic backend. Build wolfSSL first with at minimum:

```bash
cd wolfssl
./configure --enable-wolftpm
make && sudo make install
```

---

## 3. Platform-Specific Features

### Nuvoton Vendor Commands (NTC2)

wolfTPM implements two Nuvoton-specific vendor commands for module configuration:

#### `TPM2_NTC2_GetConfig()`

Retrieves the current NPCT7xx module configuration as a `CFG_STRUCT`:

```c
NTC2_GetConfig_Out getConfig;
int rc = TPM2_NTC2_GetConfig(&getConfig);
```

The `CFG_STRUCT` contains GPIO configuration, I2C address, and various module-specific parameters (`Cfg_A` through `Cfg_J`), plus validity and lock status flags.

#### `TPM2_NTC2_PreConfig()`

Writes a new configuration to the NPCT7xx module. Requires platform hierarchy authorization:

```c
NTC2_PreConfig_In preConfig;
preConfig.authHandle = TPM_RH_PLATFORM;
preConfig.preConfig = newConfig; /* Modified CFG_STRUCT */
int rc = TPM2_NTC2_PreConfig(&preConfig);
```

These commands use vendor-specific command codes:
- `TPM_CC_NTC2_PreConfig` = `CC_VEND + 0x0211`
- `TPM_CC_NTC2_GetConfig` = `CC_VEND + 0x0213`

### GPIO Support

The NPCT7xx supports 2 user-controllable GPIO pins (GPIO 3 and GPIO 4 on the NPCT75xx — numbering starts at 3). wolfTPM provides GPIO configuration, read, and set examples:

#### GPIO Modes (Nuvoton-specific)

| Mode | Value | Description |
|---|---|---|
| `TPM_GPIO_MODE_PUSHPULL` | 1 | Output, push-pull configuration |
| `TPM_GPIO_MODE_OPENDRAIN` | 2 | Output, open drain configuration |
| `TPM_GPIO_MODE_PULLUP` | 3 | Output, open drain with pull-up enabled |
| `TPM_GPIO_MODE_UNCONFIG` | 4 | Unconfigure (delete NV index) |

GPIO configuration on Nuvoton uses NV space at `TPM_NV_GPIO_SPACE = 0x01C40003` and requires platform hierarchy authorization (`TPM_RH_PLATFORM`). NV attributes must include `TPMA_NV_PLATFORMCREATE` and `TPMA_NV_POLICY_DELETE`.

Nuvoton GPIO differs from STM ST33 GPIO: Nuvoton can reconfigure any GPIO without first deleting the NV index.

### Vendor Identification

wolfTPM identifies Nuvoton TPMs by vendor ID:

```c
TPM_VENDOR_NUVOTON = 0x1050
```

This is used by the auto-detection logic and GPIO examples to verify the correct TPM module is present before executing vendor-specific commands.

### SPI Wait State Handling

Nuvoton NPCT7xx modules require SPI wait state support (`WOLFTPM_CHECK_WAIT_STATE`). This means the SPI driver must handle the TPM inserting wait cycles during SPI transactions. The wolfTPM HAL layer handles this automatically on supported platforms (Linux spidev, STM32, etc.).

---

## 4. Common Issues

### SPI Wait States Required

The NPCT7xx requires SPI wait state support. If `WOLFTPM_CHECK_WAIT_STATE` is not enabled, SPI communication will fail with corrupted responses. This is automatically set when `WOLFTPM_NUVOTON` is defined, but must be manually configured if using a custom HAL.

### GPIO Numbering Starts at 3

NPCT75xx GPIO pins start at number 3 (`TPM_GPIO_A = 3`), not 0 or 1. The maximum GPIO count is 2, so valid GPIO numbers are 3 and 4. Attempting to use GPIO numbers outside this range will fail.

### GPIO Requires FW-US Version 7.2.3.0 or Later

GPIO support on Nuvoton NPCT750 requires firmware version 7.2.3.0 or later. Earlier firmware revisions do not support the GPIO configuration NV space. Check the firmware version via `TPM2_GetCapability()` before attempting GPIO operations.

### Platform Hierarchy Authorization

Nuvoton vendor commands (`NTC2_PreConfig`, `NTC2_GetConfig`) and GPIO configuration require platform hierarchy authorization (`TPM_RH_PLATFORM`). This hierarchy may be disabled or locked in production firmware. If platform hierarchy is not available, vendor configuration commands will return authorization errors.

### SPI Clock Speed

While the Nuvoton NPCT75x supports up to 43 MHz SPI, some host platforms or wiring configurations may require lower speeds for reliability. If you experience SPI communication errors, reduce `TPM2_SPI_MAX_HZ` to 33 MHz or lower.

### Auto-Detection vs. Explicit Module Selection

When using `WOLFTPM_AUTODETECT` instead of `WOLFTPM_NUVOTON`, the SPI speed is capped at 33 MHz (the safe minimum across all supported modules). For optimal performance with a known Nuvoton module, use `--enable-nuvoton` explicitly to get the full 43 MHz SPI speed.

### Errata

Consult the Nuvoton errata documents (`NPCT75x_TPM2.0_Errata_Rev2.9.pdf`, `NPCT7xx_TPM2.0_Errata_Rev2.10.pdf`) for known silicon issues. These cover edge cases in TPM command handling, power sequencing, and SPI timing that may affect specific firmware revisions.

### EK Certificate Chain Provisioning

Nuvoton TPMs come with factory-provisioned Endorsement Key (EK) certificates. The certificate chain structure is documented in `Nuvoton_TPM_EK_Certificate_Chain_Rev1.4.pdf`. When validating EK certificates, ensure you have the correct Nuvoton root CA certificate for your module revision.

---

## 5. Example Configuration

### Configure Command — Nuvoton with wolfSSL

```bash
# Build wolfSSL with wolfTPM support
cd wolfssl
./configure --enable-wolftpm
make && sudo make install

# Build wolfTPM for Nuvoton
cd wolftpm
./configure --enable-nuvoton
make
```

### Configure Command — Nuvoton on Raspberry Pi

```bash
# wolfTPM for Nuvoton NPCT75x on Raspberry Pi via SPI
cd wolftpm
./configure --enable-nuvoton --enable-devtpm=no
make

# Run the TPM test
sudo ./examples/wrap/wrap_test
```

### Configure Command — Auto-Detection

```bash
# Let wolfTPM auto-detect the TPM module at runtime
cd wolftpm
./configure --enable-autodetect
make
```

### GPIO Configuration Example

```bash
# Build with Nuvoton support for GPIO
cd wolftpm
./configure --enable-nuvoton
make

# Configure GPIO 3 as push-pull output
sudo ./examples/gpio/gpio_config 3 pushpull

# Set GPIO 3 high
sudo ./examples/gpio/gpio_set 3 1

# Read GPIO 3 state
sudo ./examples/gpio/gpio_read 3
```

### Minimal wolfTPM User Settings (Bare-Metal)

```c
/* user_settings.h — wolfTPM for Nuvoton NPCT75x */

#ifndef WOLFTPM_USER_SETTINGS_H
#define WOLFTPM_USER_SETTINGS_H

/* Select Nuvoton TPM module */
#define WOLFTPM_NUVOTON

/* SPI configuration (auto-set by WOLFTPM_NUVOTON, shown for reference) */
/* #define WOLFTPM_CHECK_WAIT_STATE */
/* #define TPM2_SPI_MAX_HZ 43000000 */

/* If using a custom SPI HAL */
/* #define WOLFTPM_ADV_IO */

/* Enable wolfTPM wrapper API */
/* #define WOLFTPM2_NO_WRAPPER */  /* Define to disable wrapper for minimal size */

#endif /* WOLFTPM_USER_SETTINGS_H */
```

---

## 6. Additional Resources

### wolfSSL / wolfTPM References

- **wolfTPM repository**: github.com/wolfSSL/wolfTPM — full source with examples
- **wolfTPM GPIO examples**: `wolftpm/examples/gpio/` — `gpio_config.c`, `gpio_read.c`, `gpio_set.c` (support Nuvoton and STM ST33)
- **wolfTPM HAL for Linux SPI**: `wolftpm/hal/tpm_io_linux.c` — includes Nuvoton SPI chip select configuration
- **wolfssl-examples TPM**: `wolfssl-examples/tpm/` — additional TPM usage examples with wolfSSL
- **wolfTPM Manual**: wolfssl.com/documentation/manuals/wolftpm/ — API reference and integration guide

### Internal Documentation

- **examples-private/nuvoton/**: Contains 20+ Nuvoton vendor PDFs including datasheets, programming guides, errata, board design guides, FIPS security policy, EK certificate chain documentation, evaluation board user guides, and reference schematics. These are vendor-provided documents covering the NPCT65x, NPCT75x, and NPCT76x module families.

### Nuvoton TPM Resources

- **Nuvoton TPM product page**: nuvoton.com — search for NPCT75x or TPM 2.0
- **TCG TPM 2.0 Specification**: trustedcomputinggroup.org/resource/tpm-library-specification/ — the underlying standard implemented by wolfTPM
- **Nuvoton Raspberry Pi Evaluation Board**: Documented in `NPCT7xx_Raspberry-Pi_EB_UG_SPI_I2C_Rev1.0.pdf` — supports both SPI and I2C interfaces
