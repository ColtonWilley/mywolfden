---
paths:
  - "**/IDE/Renesas/**"
  - "**/renesas*"
  - "**/Renesas*"
---

# Renesas (RX / RA / RZ) — wolfSSL Platform Guide

## 1. Overview

wolfSSL supports several Renesas microcontroller families, including the RX, RA, and RZ series. Integration is provided through dedicated hardware abstraction layers that allow wolfSSL to offload cryptographic operations to Renesas security hardware where available.

Three primary hardware security interfaces are supported:

| Define | Hardware / Module | Typical Target |
|---|---|---|
| `WOLFSSL_RENESAS_TSIP` | Trusted Secure IP (TSIP) | RX65N and related RX series |
| `WOLFSSL_RENESAS_SCEPROTECT` | SCE Protected Mode (SCE) | RA6M4 and related RA series |
| `WOLFSSL_RENESAS_FSPSM` | FSP Security Module (FSP SM) | RA series via Renesas FSP |

An additional define, `WOLFSSL_RENESAS_RX64_HASH`, enables hardware-accelerated SHA operations on RX64 series devices (contributed by Johnson Controls Tyco IP Holdings LLP).

Port header files are located under:
```
wolfssl/wolfcrypt/port/Renesas/
```

IDE project files are provided under:
```
IDE/Renesas/cs+
IDE/Renesas/e2studio
```

---

## 2. Build Configuration

### Key Defines

All Renesas-specific defines are commented out by default in `settings.h` and must be explicitly enabled, either in `settings.h` or in a `user_settings.h` file.

```c
/* Enable TSIP hardware acceleration (e.g., RX65N) */
#define WOLFSSL_RENESAS_TSIP

/* Enable SCE Protected Mode (e.g., RA6M4) */
#define WOLFSSL_RENESAS_SCEPROTECT

/* Enable FSP Security Module */
/* (typically set indirectly via WOLFSSL_RENESAS_SCEPROTECT or RSIP) */
/* #define WOLFSSL_RENESAS_FSPSM */

/* Enable RX64 hardware SHA acceleration */
#define WOLFSSL_RENESAS_RX64_HASH

/* Identify the specific board/device */
#define WOLFSSL_RENESAS_RX65N   /* for RX65N */
#define WOLFSSL_RENESAS_RA6M4   /* for RA6M4 */
```

> **Note:** `WOLFSSL_RENESAS_FSPSM` is the internal FSP Security Module abstraction layer. It is activated by the type-mapping headers when `WOLFSSL_RENESAS_SCEPROTECT` or related defines are set. Check `renesas-fspsm-types.h` for the exact mapping logic.

### user_settings.h

wolfSSL on Renesas platforms is typically built using `WOLFSSL_USER_SETTINGS`, which causes wolfSSL to read configuration from a `user_settings.h` file rather than relying on `./configure` flags. This is the recommended approach for IDE-based builds.

```c
#define WOLFSSL_USER_SETTINGS
```

### Configure Flags

No specific `./configure` flags are documented in the available source material for these platforms. IDE-based builds (e2studio, CS+) are the primary supported build method. Refer to the wolfSSL manual or the `IDE/Renesas/` project files for the authoritative build setup.

### IDE Projects

Two IDE environments are supported with pre-configured project files:

- **e2studio** — Renesas e² studio (Eclipse-based): `IDE/Renesas/e2studio/`
- **CS+** — Renesas CS+: `IDE/Renesas/cs+/`

---

## 3. Platform-Specific Features

### Hardware Cryptography

#### TSIP (Trusted Secure IP) — `WOLFSSL_RENESAS_TSIP`

Enabled via `WOLFSSL_RENESAS_TSIP`. Relevant headers:

```
wolfssl/wolfcrypt/port/Renesas/renesas-tsip-crypt.h
wolfssl/wolfcrypt/port/Renesas/renesas_tsip_internal.h
wolfssl/wolfcrypt/port/Renesas/renesas_tsip_types.h
```

#### SCE Protected Mode — `WOLFSSL_RENESAS_SCEPROTECT`

Enabled via `WOLFSSL_RENESAS_SCEPROTECT`. When this define is active, the FSP SM abstraction layer maps to the SCE API:

- Includes `r_sce.h`
- Maps hardware instance control to `sce_instance_ctrl_t` / `sce_ctrl`
- Maps open/close to `R_SCE_Open` / `R_SCE_Close`
- Maps random number generation to `R_SCE_RandomNumberGenerate`
- Supports RSA 2048-bit root certificate installation via `R_SCE_TLS_RootCertificateRSA2048PublicKeyInstall`

Relevant TLS buffer size constants defined when this mode is active:

```c
#define FSPSM_TLS_CLIENTRANDOM_SZ           36  /* bytes */
#define FSPSM_TLS_SERVERRANDOM_SZ           36  /* bytes */
#define FSPSM_TLS_ENCRYPTED_ECCPUBKEY_SZ    96  /* bytes */
```

#### FSP Security Module (FSPSM) — `WOLFSSL_RENESAS_FSPSM`

The FSPSM layer provides a unified abstraction over SCE and RSIP hardware. It supports:

- **AES**: 128-bit and 256-bit wrapped key operations
- **RSA**: 1024-bit and 2048-bit wrapped key operations (when `WOLFSSL_RENESAS_FSPSM_CRYPTONLY` is defined)
- **ECC**: Enabled via `WOLFSSL_RENESAS_FSPSM_ECC`, which also activates `HAVE_PK_CALLBACKS`

Relevant headers:

```
wolfssl/wolfcrypt/port/Renesas/renesas-fspsm-crypt.h
wolfssl/wolfcrypt/port/Renesas/renesas-fspsm-types.h
wolfssl/wolfcrypt/port/Renesas/renesas_fspsm_internal.h
```

The `FSPSM_tag_ST` structure tracks per-session state including a device ID and wrapped key handles for AES and RSA operations.

#### RX64 Hardware SHA — `WOLFSSL_RENESAS_RX64_HASH`

Provides hardware-accelerated SHA-1, SHA-224, and SHA-256 on RX64 series devices. Requires the Renesas SHA driver header:

```c
#include <renesas/security/sha/r_sha.h>
```

Supported hash types:

```c
RX64_SHA1    = 0
RX64_SHA224  = 1
RX64_SHA256  = 2
```

The hardware hash context (`wolfssl_RX64_HW_Hash`) is typedef'd directly to `wc_Sha`, `wc_Sha256`, and `wc_Sha224` when the respective algorithms are enabled.

Hardware access is protected by lock/unlock functions:

```c
int  rx64_hw_Open(void);
void rx64_hw_Close(void);
int  rx64_hw_lock(void);
void rx64_hw_unlock(void);
```

### PK Callbacks

When `WOLFSSL_RENESAS_FSPSM_ECC` is defined, `HAVE_PK_CALLBACKS` is automatically enabled. This allows the FSP SM layer to intercept public-key operations and redirect them to hardware.

### Common Synchronization Header

```
wolfssl/wolfcrypt/port/Renesas/renesas_sync.h
wolfssl/wolfcrypt/port/Renesas/renesas_cmn.h
```

These headers provide common synchronization and shared utility functions across the Renesas port. Details beyond their existence are not available in the current source material; consult the wolfSSL manual for usage.

---

## 4. Common Issues

### Wrapped Keys

The FSPSM and SCE layers use **wrapped keys** — keys encrypted by the hardware security module. Plain-text key material is not used directly. Ensure that key installation procedures (e.g., `R_SCE_TLS_RootCertificateRSA2048PublicKeyInstall`) are called before initiating TLS sessions.

### Hardware Instance Initialization

The SCE/FSP hardware instance must be opened before use:

```c
R_SCE_Open(&sce_ctrl, &sce_cfg);
```

Failure to initialize the hardware instance before wolfSSL operations will result in errors. Ensure `FSPSM_OPEN` is called during system startup.

### `WOLFSSL_RENESAS_FSPSM_CRYPTONLY`

RSA wrapped key support in the FSPSM layer is only compiled in when `WOLFSSL_RENESAS_FSPSM_CRYPTONLY` is defined. If RSA hardware acceleration is needed outside of TLS, this define must be set explicitly.

### `WOLFSSL_RENESAS_FSPSM_ECC` and PK Callbacks

Enabling `WOLFSSL_RENESAS_FSPSM_ECC` automatically defines `HAVE_PK_CALLBACKS`. If your application also manually configures PK callbacks, ensure there are no conflicts. A debug option `DEBUG_PK_CB` is available (commented out by default in the source).

### Stack Size

Renesas embedded targets typically have constrained stack sizes. wolfSSL TLS operations can require significant stack depth. The wolfSSL manual recommends reviewing stack allocation for your specific RTOS or bare-metal configuration. No specific minimum stack size is documented in the available source material — consult the wolfSSL manual and Renesas application notes for guidance.

### Board-Specific Defines

The board/device identification defines (`WOLFSSL_RENESAS_RX65N`, `WOLFSSL_RENESAS_RA6M4`) are separate from the hardware module defines (`WOLFSSL_RENESAS_TSIP`, `WOLFSSL_RENESAS_SCEPROTECT`). Both may need to be set depending on the port code paths used.

---

## 5. Example Configuration

### Minimal `user_settings.h` for RX65N with TSIP

```c
/* user_settings.h — RX65N + TSIP */

/* Identify platform */
#define WOLFSSL_RENESAS_RX65N

/* Enable TSIP hardware acceleration */
#define WOLFSSL_RENESAS_TSIP

/* Use user_settings.h for all configuration */
#define WOLFSSL_USER_SETTINGS

/* TLS 1.2 */
#define WOLFSSL_TLS13
#define NO_OLD_TLS

/* Disable algorithms not supported or needed */
#define NO_DES3
#define NO_RC4
#define NO_MD4

/* ECC support */
#define HAVE_ECC

/* Use hardware RNG if available */
/* (configure as needed for your BSP) */
```

### Minimal `user_settings.h` for RA6M4 with SCE Protected Mode

```c
/* user_settings.h — RA6M4 + SCE Protected Mode */

/* Identify platform and hardware module */
#define WOLFSSL_RENESAS_RA6M4
#define WOLFSSL_RENESAS_SCEPROTECT

/* Use user_settings.h for all configuration */
#define WOLFSSL_USER_SETTINGS

/* Enable ECC hardware offload via FSP SM */
#define WOLFSSL_RENESAS_FSPSM_ECC
/* HAVE_PK_CALLBACKS is set automatically by WOLFSSL_RENESAS_FSPSM_ECC */

/* TLS */
#define WOLFSSL_TLS13
#define NO_OLD_TLS

/* Disable unneeded algorithms */
#define NO_DES3
#define NO_RC4
#define NO_MD4

/* ECC */
#define HAVE_ECC
```

### Minimal `user_settings.h` for RX64 with Hardware SHA

```c
/* user_settings.h — RX64 + hardware SHA */

/* Enable RX64 hardware hash acceleration */
#define WOLFSSL_RENESAS_RX64_HASH

/* Use user_settings.h */
#define WOLFSSL_USER_SETTINGS

/* SHA algorithms (hardware-backed) */
/* NO_SHA, NO_SHA256 must NOT be defined if hardware SHA is desired */

/* Disable unneeded features */
#define NO_DES3
#define NO_RC4
```

---

## 6. Additional Resources

### Vendor Documentation (Public — NDA Explicitly Not Required)

Renesas has among the best public documentation availability of any embedded silicon vendor. They explicitly state "NDA is not required" for TSIP documentation.

#### FSP (Flexible Software Package) — GitHub BSD-3-Clause

- **Full source**: [github.com/renesas/fsp](https://github.com/renesas/fsp) — includes `ra/fsp/src/r_sce/` for SCE crypto
- **API Reference**: [renesas.github.io/fsp/modules.html](https://renesas.github.io/fsp/modules.html)
- **SCE Protected Mode API**: [renesas.github.io/fsp/group___s_c_e___p_r_o_t_e_c_t_e_d.html](https://renesas.github.io/fsp/group___s_c_e___p_r_o_t_e_c_t_e_d.html) — covers AES-128/256, RSA-1024-4096, ECC P-192 through P-384, SHA-256, HMAC, CMAC, key wrap, TLS
- **Key Injection docs**: [renesas.github.io/fsp/group___s_c_e___k_e_y___i_n_j_e_c_t_i_o_n.html](https://renesas.github.io/fsp/group___s_c_e___k_e_y___i_n_j_e_c_t_i_o_n.html)

#### TSIP (Trusted Secure IP — RX family)

- **Download page**: [renesas.com/en/software-tool/trusted-secure-ip-driver](https://www.renesas.com/en/software-tool/trusted-secure-ip-driver) — public download
- **Application Note (~450 pages)**: [renesas.com/en/document/apn/rx-family-tsiptrusted-secure-ip-module-firmware-integration-technology](https://www.renesas.com/en/document/apn/rx-family-tsiptrusted-secure-ip-module-firmware-integration-technology)

#### wolfSSL/Renesas Integration

- **Dedicated integration repo**: [github.com/wolfSSL/Renesas](https://github.com/wolfSSL/Renesas)
- **wolfSSL examples**: `wolfssl-examples/Renesas/` (CS+ IDE project files)

---

> **Further Reading:** The available source material covers the define names, header structure, and hardware API mappings. For complete integration steps, RTOS threading configuration, networking layer setup, and example project walkthroughs, consult the [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/) and the pre-built project files in `IDE/Renesas/e2studio/` and `IDE/Renesas/cs+/`.
