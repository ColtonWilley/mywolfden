---
paths:
  - "repos/wolfssh/**"
---

# OpenSSH, BIND9, MariaDB, Mosquitto, strongSwan + wolfSSL — wolfSSL Platform Guide

## 1. Overview

wolfSSL provides OpenSSL compatibility layer support for a range of widely deployed open-source projects, including OpenSSH, BIND9 (DNS), MariaDB, Mosquitto (MQTT broker), and strongSwan (IPsec VPN). Each of these projects can be configured to use wolfSSL as a drop-in replacement for OpenSSL through wolfSSL's compatibility layer, which exposes a subset of the OpenSSL API backed by wolfSSL's native cryptographic implementations.

Each project has a corresponding configure flag and, where applicable, a preprocessor define that activates project-specific compatibility shims within wolfSSL:

| Project    | Configure Flag          | Preprocessor Define  |
|------------|-------------------------|----------------------|
| OpenSSH    | `--enable-openssh`      | `WOLFSSL_OPENSSH`    |
| BIND9      | `--enable-bind`         | `WOLFSSL_BIND`       |
| MariaDB    | `--enable-mariadb`      | *(see notes below)*  |
| Mosquitto  | `--enable-mosquitto`    | `HAVE_MOSQUITTO`     |
| strongSwan | `--enable-strongswan`   | *(see notes below)*  |

> **Note:** The source material available for this guide covers OpenSSH, BIND9, Mosquitto, and strongSwan configure flags explicitly. MariaDB is listed as a supported project in wolfSSL's compatibility layer ecosystem. For full details on MariaDB-specific defines and strongSwan-specific defines, consult the [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/) and the wolfSSL GitHub repository.

---

## 2. Build Configuration

### Configure Flags

wolfSSL must be built with the appropriate compatibility flag(s) before the target application is built against it. Each flag enables the OpenSSL compatibility layer tuned for that specific project.

**Single project example:**
```bash
./configure --enable-openssh
make
sudo make install
```

**Multiple projects (combined build):**
```bash
./configure \
  --enable-openssh \
  --enable-bind \
  --enable-mariadb \
  --enable-mosquitto \
  --enable-strongswan
make
sudo make install
```

> **Important:** Enabling multiple compatibility targets simultaneously in a single wolfSSL build is possible at the configure level, but it is generally recommended to build separate wolfSSL installations for each project to avoid conflicts between the different API shim requirements of each application. Test thoroughly if combining flags.

### Preprocessor Defines

When the configure flags are used, the following defines are set automatically by the build system:

- `WOLFSSL_OPENSSH` — Activates OpenSSH-specific OpenSSL compatibility shims.
- `WOLFSSL_BIND` — Activates BIND DNS-specific compatibility shims.
- `HAVE_MOSQUITTO` — Activates Mosquitto MQTT broker compatibility shims.

If you are building wolfSSL without autoconf (e.g., using a custom `user_settings.h`), these defines must be added manually.

### IDE / Manual Builds

For environments without autoconf support, add the relevant defines to your `user_settings.h` file (see Section 5 for an example). wolfSSL's OpenSSL compatibility layer is activated by `OPENSSL_EXTRA` or `OPENSSL_ALL`, which the project-specific flags typically imply. Check the wolfSSL manual for the exact set of defines pulled in by each project flag.

---

## 3. Platform-Specific Features

### OpenSSL Compatibility Layer

All five projects rely on wolfSSL's OpenSSL compatibility layer. This layer provides API-level compatibility so that applications written against OpenSSL can link against wolfSSL with minimal or no source changes. The compatibility layer does not guarantee 100% API coverage; only the subset required by each supported project is implemented.

### Cryptographic Backend

wolfSSL uses its own native cryptographic implementations by default. Hardware acceleration (e.g., AES-NI on x86, hardware RNG) can be enabled independently of the project compatibility flags and will benefit all projects built on top of wolfSSL.

### Threading

wolfSSL supports multi-threaded use. If the target application is multi-threaded (as is the case for OpenSSH, BIND9, MariaDB, and strongSwan), ensure wolfSSL is built with threading support enabled. On POSIX systems this is typically automatic; verify with:
```bash
./configure --enable-openssh --enable-threadlocal
```
Consult the wolfSSL manual for threading model details specific to your platform.

### Networking

wolfSSL itself is network-stack agnostic. The compatibility layer handles the TLS/SSL API surface; the underlying network I/O is managed by the application. No special wolfSSL networking flags are required beyond the project-specific enable flags listed above.

---

## 4. Common Issues

### Incomplete OpenSSL API Coverage

The OpenSSL compatibility layer covers the API surface needed by each supported project, but it is not a complete OpenSSL replacement. If a project uses OpenSSL APIs not covered by wolfSSL's shim for that project, build or runtime errors will occur. Check wolfSSL release notes and the compatibility layer source (`wolfssl/openssl/`) for coverage details.

### Combining Multiple Enable Flags

Enabling multiple project flags (e.g., `--enable-openssh --enable-bind`) in a single build may cause define conflicts or unexpected behavior if the projects have overlapping but incompatible API requirements. This is a known risk when combining compatibility targets. Where possible, use separate wolfSSL builds per project.

### MariaDB and strongSwan Defines

The source material available for this guide does not explicitly list the preprocessor defines for MariaDB and strongSwan (unlike `WOLFSSL_OPENSSH`, `WOLFSSL_BIND`, and `HAVE_MOSQUITTO`). These may be set implicitly by the configure system or may require additional flags. Verify by inspecting `configure.ac` in the wolfSSL source tree or by running:
```bash
./configure --enable-mariadb --enable-strongswan
grep -E "MARIADB|STRONGSWAN" config.h
```

### Version Compatibility

Each supported project may require a specific version of wolfSSL. Always check the wolfSSL documentation or the project's own integration notes for minimum version requirements before upgrading wolfSSL.

### Stack Size

Some of these applications (particularly strongSwan and OpenSSH) operate in environments with constrained or configurable stack sizes. wolfSSL's cryptographic operations can require significant stack space depending on the algorithms in use. If stack overflows are observed, increase the thread/task stack size for the affected component. Refer to the wolfSSL manual's section on stack usage for algorithm-specific guidance.

### Header Conflicts

When building the target application against wolfSSL's compatibility headers, ensure that OpenSSL's own headers are not also present in the include path. Mixed headers will cause compilation failures.

---

## 5. Example Configuration

### Minimal `configure` Command

The following example builds wolfSSL with compatibility support for all five projects:

```bash
./configure \
  --enable-openssh \
  --enable-bind \
  --enable-mariadb \
  --enable-mosquitto \
  --enable-strongswan
make
sudo make install
```

### Minimal `user_settings.h` (Manual / IDE Builds)

If you are not using autoconf, the following `user_settings.h` provides a starting point. Add or remove defines based on which projects you are supporting:

```c
/* user_settings.h — wolfSSL manual build for OpenSSH, BIND9,
   MariaDB, Mosquitto, strongSwan compatibility */

/* Enable OpenSSL compatibility layer (required for all five projects) */
#define OPENSSL_EXTRA
#define OPENSSL_ALL

/* Project-specific compatibility defines */
#define WOLFSSL_OPENSSH      /* OpenSSH */
#define WOLFSSL_BIND         /* BIND9 DNS */
/* MariaDB define — verify correct name in wolfSSL source */
/* #define WOLFSSL_MARIADB */
#define HAVE_MOSQUITTO       /* Mosquitto MQTT */
/* strongSwan define — verify correct name in wolfSSL source */
/* #define WOLFSSL_STRONGSWAN */

/* Standard algorithm support */
#define HAVE_TLS_EXTENSIONS
#define HAVE_SUPPORTED_CURVES
#define HAVE_EXTENDED_MASTER
#define WOLFSSL_TLS13

/* Threading (POSIX) */
#define HAVE_PTHREAD

/* Optional: enable hardware RNG if available */
/* #define HAVE_HASHDRBG */
```

> **Note:** The defines for MariaDB and strongSwan are commented out above because the exact define names are not confirmed in the available source material. Inspect `configure.ac` in the wolfSSL source tree or the wolfSSL manual for the authoritative define names before using a manual build for those projects.

---

## Further Reading

- [wolfSSL Manual](https://www.wolfssl.com/documentation/manuals/wolfssl/)
- [wolfSSL GitHub — configure.ac](https://github.com/wolfSSL/wolfssl/blob/master/configure.ac)
- wolfSSL example ports: `wolfssl-examples` repository on GitHub
- For project-specific integration guides (e.g., patching OpenSSH or BIND9 to use wolfSSL), see the wolfSSL documentation portal and any `INSTALL` or `README` files in the wolfSSL source under `IDE/` or `examples/`.
