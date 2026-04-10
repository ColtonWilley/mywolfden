# Linux TPM Device Model

> One-line summary: Linux TPM device nodes, permissions, and resource manager conflicts that cause silent failures in wolfTPM.

**When to read**: Integrating wolfTPM on Linux, debugging `/dev/tpm0` access errors, or setting up swtpm for development.

---

## Device Nodes

| Device | Mode | When to use |
|--------|------|-------------|
| `/dev/tpm0` | Direct, exclusive | Single-process, low-level testing only |
| `/dev/tpmrm0` | Kernel resource manager | **Production** — multi-process safe, handles context save/restore |

wolfTPM build flag: `--enable-devtpm`. Select device at runtime:
```c
rc = wolfTPM2_Init(&dev, TPM2_IoCb, "/dev/tpmrm0");
```

## Permissions

TPM devices are `root:tpm` mode `0660`. Fix permission denied:
1. Add user to `tpm` group: `sudo usermod -aG tpm $USER` (re-login required)
2. Or udev rule: `SUBSYSTEM=="tpm", MODE="0666"` in `/etc/udev/rules.d/80-tpm.rules`

## tpm2-abrmd Conflict

If `tpm2-abrmd` (userspace resource manager) is running, it holds `/dev/tpm0`
exclusively. wolfTPM does **not** support its D-Bus interface.

**Resolution**: Stop `tpm2-abrmd` and use `/dev/tpmrm0` (kernel RM) directly.
Check: `systemctl status tpm2-abrmd`

## Software TPM for Development

Build flag: `--enable-swtpm`. Connects to TCP `localhost:2321` (command) /
`2322` (platform). Use [swtpm](https://github.com/stefanberger/swtpm) or
IBM's TPM2 simulator.

## AF_ALG Crypto Offload (Separate from TPM)

Linux `AF_ALG` offloads crypto to kernel drivers (useful when hardware has
a kernel crypto driver but no userspace SDK). wolfSSL flag: `--enable-afalg`.
Requires `CONFIG_CRYPTO_USER_API_HASH`, `_SKCIPHER`, `_AEAD` in kernel config.
Check available algorithms: `cat /proc/crypto`.

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| `EBUSY` on `/dev/tpm0` | Another process (often `tpm2-abrmd`) has exclusive lock | Stop conflicting service or use `/dev/tpmrm0` |
| `EPERM` / `EACCES` on `/dev/tpmrm0` | User not in `tpm` group | `usermod -aG tpm $USER` + re-login |
| `/dev/tpm0` doesn't exist | TPM disabled in BIOS, or kernel module not loaded | Check BIOS, `lsmod \| grep tpm`, `dmesg \| grep -i tpm` |
| wolfTPM connects but commands fail | Using `/dev/tpm0` while `tpm2-abrmd` intercepts | Stop abrmd, switch to `/dev/tpmrm0` |

## What This File Does NOT Cover

- wolfTPM API patterns and retry logic (see `products/wolftpm.md`)
- Windows TBS integration (see `platforms/windows-tbs.md`)
- TPM key provisioning and attestation workflows
