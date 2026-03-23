---
paths:
  - "**/meta-*/**"
  - "**/*.bb"
  - "**/*.bbappend"
  - "repos/meta-wolfssl/**"
---

# Yocto / OpenEmbedded Integration (meta-wolfssl)

## Layer Setup

The `meta-wolfssl` layer is the official wolfSSL Yocto/OpenEmbedded layer (`github.com/wolfSSL/meta-wolfssl`).

1. Clone into your layers directory: `git clone https://github.com/wolfSSL/meta-wolfssl.git`
2. Add to `bblayers.conf`: `BBLAYERS += "/path/to/meta-wolfssl"`
3. Add wolfSSL products to `local.conf` via `IMAGE_INSTALL`:
   ```
   IMAGE_INSTALL:append = " wolfssl wolfssh wolftpm wolfmqtt wolfclu wolfpkcs11"
   ```
4. Version compatibility: tested against Sumo, Thud, Warrior, Zeus, Hardknott, Gatesgarth, Dunfell, Kirkstone, Nanbield, Langdale, and Scarthgap releases.

## Available Recipes (`recipes-wolfssl/`)

| Recipe | Description |
|--------|-------------|
| `wolfssl` | Core wolfSSL/wolfCrypt TLS library |
| `wolfssh` | SSH library built on wolfCrypt |
| `wolftpm` | TPM 2.0 portable library |
| `wolfmqtt` | MQTT client library |
| `wolfclu` | wolfSSL command-line utility (OpenSSL CLI replacement) |
| `wolfpkcs11` | PKCS#11 provider backed by wolfCrypt |
| `wolfengine` | OpenSSL 1.x engine wrapping wolfCrypt |
| `wolfprovider` | OpenSSL 3.x provider wrapping wolfCrypt |
| `wolfssl-py` | Python bindings for wolfSSL |
| `wolfcrypt-py` | Python bindings for wolfCrypt |
| `wolfssl-linuxkm` | Linux kernel module for in-kernel wolfCrypt |

## Third-Party Integration (bbappend files)

meta-wolfssl provides `bbappend` files that patch third-party packages to use wolfSSL instead of OpenSSL. Each integration requires uncommenting the relevant `BBFILES` line in `conf/layer.conf`:

- **curl** (`recipes-support/curl/`) — TLS via wolfSSL; also supports wolfProvider FIPS path
- **OpenSSH** (`recipes-connectivity/openssh/`) — SSH with wolfSSL crypto backend
- **strongSwan** (`recipes-support/strongswan/`) — IPsec/IKE VPN with wolfSSL
- **libssh2** (`recipes-support/libssh2/`) — SSH2 client library with wolfSSL
- **BIND** (`recipes-connectivity/bind/`) — DNS server with wolfSSL TLS
- **socat** (`recipes-connectivity/socat/`) — relay tool with wolfSSL TLS (1.7.x and 1.8.x)
- **rsyslog** (`recipes-extended/rsyslog/`) — logging daemon with wolfSSL TLS; FIPS crypto variant
- **net-snmp** (`recipes-protocols/net-snmp/`) — SNMP with wolfSSL
- **tcpdump** (`recipes-support/tcpdump/`) — packet capture with wolfSSL
- **GnuTLS** (`recipes-support/gnutls/`) — wolfSSL-backed GnuTLS wrapper (`wolfssl-gnutls-wrapper`)
- **libgcrypt** (`recipes-support/libgcrypt/`) — wolfSSL-backed libgcrypt; FIPS variant available

To enable, uncomment the appropriate `BBFILES +=` line in `conf/layer.conf` and rebuild.

## FIPS Configuration

### Build Types
Set `WOLFSSL_TYPE` in `local.conf`:
- `"fips"` — FIPS 140-2/140-3 validated build (requires commercial license + FIPS bundle)
- `"fips-ready"` — FIPS-ready build (uses open-source code with FIPS-equivalent config)
- `"commercial"` — commercial licensed build (non-FIPS)

### Virtual Provider Mechanism
`PREFERRED_PROVIDER_virtual/wolfssl` defaults to `"wolfssl"`. For FIPS builds, the `wolfssl-fips.bb` recipe provides `virtual/wolfssl` so all dependent recipes automatically link against the FIPS-validated library.

### FIPS Hash Verification (Two-Pass Build)
FIPS builds require a two-pass process:
1. First build: generates the `verifyCore` hash
2. Extract the hash from the build log or test output
3. Set the hash in the FIPS configuration and rebuild
4. Second build embeds the correct hash for runtime integrity verification

**Common issue**: Hash mismatch at runtime means the binary was modified after hash extraction. Ensure no strip/debug operations occur between hash extraction and final image assembly.

## BitBake Classes

| Class | Purpose |
|-------|---------|
| `wolfssl-helper` | Common wolfSSL build configuration helpers |
| `wolfssl-fips-helper` | FIPS-specific build configuration and hash management |
| `wolfssl-commercial` | Commercial license configuration (SRC_URI override to private repo) |
| `wolfssl-osp-support` | Open-source package (OSP) integration support |
| `wolfssl-kernel-random` | Kernel random number generator configuration for wolfCrypt |
| `wolfssl-initramfs` | initramfs integration for early-boot wolfCrypt |
| `wolfssl-compatibility` | Legacy/modern BitBake syntax compatibility (handles `:append` vs `_append`) |

## Linux Kernel Module (`wolfssl-linuxkm`)

The `wolfssl-linuxkm` recipe builds wolfCrypt as a loadable kernel module:
- Enables in-kernel cryptographic operations using wolfCrypt
- FIPS variant available via `wolfssl-linuxkm-fips.bb`
- Requires kernel headers; integrated via standard module build infrastructure
- Use case: FIPS-validated crypto for kernel-level VPN (e.g., wolfGuard/WireGuard-FIPS)

## Demo Images (`recipes-core/images/`)

Enable via `WOLFSSL_DEMOS` in `local.conf`:
- `wolfssl-image-minimal` — base wolfSSL
- `wolfssl-combined-image-minimal` — wolfSSL + wolfSSH + wolfTPM + wolfMQTT + wolfCLU
- `wolfclu-image-minimal` / `wolfclu-combined-image-minimal` — wolfCLU-focused
- `wolftpm-image-minimal` — wolfTPM testing
- `wolfssl-py-image-minimal` — Python bindings testing
- `wolfprovider-image-minimal` — wolfProvider (OpenSSL 3.x)
- `wolfprovider-replace-default-image-minimal` — wolfProvider as default OpenSSL provider
- `fips-image-minimal` — FIPS-validated configuration
- `libgcrypt-image-minimal` / `gnutls-image-minimal` — GnuTLS/libgcrypt with wolfSSL backend

## Common Issues

### Layer Priority Conflicts
meta-wolfssl uses priority 5. If another layer provides conflicting `bbappend` files for the same packages, adjust `BBFILE_PRIORITY_wolfssl` in `layer.conf` or use `PREFERRED_PROVIDER` overrides.

### OpenSSL Replacement Gotchas
When using wolfEngine (OpenSSL 1.x) or wolfProvider (OpenSSL 3.x) as a drop-in replacement:
- The `openssl_1.%.bbappend` / `openssl_3.%.bbappend` files are conditionally included only when wolfengine/wolfprovider is in `IMAGE_INSTALL` or `WOLFSSL_FEATURES`
- Ensure the correct OpenSSL version recipe matches your Yocto release
- wolfProvider can be set as the default provider, replacing OpenSSL's built-in crypto entirely

### Commercial/Private Source Configuration
For commercial or FIPS builds, set the appropriate `*_TYPE` variable (`WOLFSSL_TYPE`, `WOLFSSH_TYPE`, `WOLFMQTT_TYPE`, etc.) to `"commercial"`. This activates `bbappend` files that override `SRC_URI` to point to wolfSSL's private repositories (requires license).

### Inc Files (Legacy vs Modern Syntax)
Each `.inc` file in the `inc/` directory has three variants:
- `*-legacy.inc` — uses `_append` syntax (pre-Kirkstone)
- `*-modern.inc` — uses `:append` syntax (Kirkstone+)
- `*.inc` — auto-selects based on `WOLFSSL_LAYERDIR` variable and OE version detection
