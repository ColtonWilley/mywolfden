---
paths:
  - "**/tpmrm*"
  - "**/tpm0*"
  - "repos/wolftpm/**"
---

# Linux TPM Device Model — wolfTPM Integration

## Device Nodes

Linux exposes two TPM device nodes:

| Device | Mode | Use case |
|--------|------|----------|
| `/dev/tpm0` | Direct, single-user | Exclusive access; only one process at a time. Used for low-level TPM testing or when the application manages its own session/handle lifecycle. |
| `/dev/tpmrm0` | Kernel resource manager | Multi-process safe. The kernel handles context save/restore and handle virtualization. **Recommended for production.** |

**wolfTPM build flags:**
- `--enable-devtpm` → uses `/dev/tpm0` (direct)
- `--enable-devtpm` is also used for `/dev/tpmrm0` — select the device at runtime:
  ```c
  rc = wolfTPM2_Init(&dev, TPM2_IoCb, "/dev/tpmrm0");
  ```

## Permissions

TPM devices are owned by `root:tpm` with mode `0660` by default.

**Fix permission denied errors:**
1. Add user to `tpm` group: `sudo usermod -aG tpm $USER` (then re-login)
2. Or use a udev rule for broader access:
   ```
   # /etc/udev/rules.d/80-tpm.rules
   SUBSYSTEM=="tpm", MODE="0666"
   ```
3. Verify: `ls -la /dev/tpm*` should show the correct group/permissions

## Common Error Patterns

### EBUSY on /dev/tpm0
**Symptom**: `open("/dev/tpm0"): Device or resource busy`
**Cause**: Another process has `/dev/tpm0` open (only one user at a time).
Common culprits: `tpm2-abrmd` (userspace resource manager), `trousers` (tcsd).
**Fix**: Either stop the conflicting service, or switch to `/dev/tpmrm0` (kernel RM).

### EPERM / EACCES
**Symptom**: `open("/dev/tpmrm0"): Permission denied`
**Fix**: Add user to `tpm` group (see Permissions above).

### Resource manager conflicts
If `tpm2-abrmd` is running, it opens `/dev/tpm0` exclusively. You must either:
1. Talk to `tpm2-abrmd` via its D-Bus interface (wolfTPM doesn't support this), or
2. Stop `tpm2-abrmd` and use `/dev/tpmrm0` (kernel RM) directly — **this is the recommended approach with wolfTPM**.

Check: `systemctl status tpm2-abrmd`

### TPM device not found
**Symptom**: `/dev/tpm0` doesn't exist
**Checklist**:
- Is TPM enabled in BIOS/UEFI?
- Is the TPM kernel module loaded? `lsmod | grep tpm` (look for `tpm_tis`, `tpm_crb`, `tpm_tis_spi`)
- Check kernel log: `dmesg | grep -i tpm`

## Software TPM (swtpm) for Development

wolfTPM can connect to a software TPM simulator for development/testing:
- **Build flag**: `--enable-swtpm`
- Default connection: TCP `localhost:2321` (command port) and `2322` (platform port)
- Popular simulator: [swtpm](https://github.com/stefanberger/swtpm) or IBM's TPM2 simulator

## AF_ALG Crypto Offload (wolfSSL)

Separate from TPM — Linux AF_ALG allows wolfSSL to offload crypto to kernel drivers:
- Socket family `AF_ALG` provides access to kernel crypto API
- Useful when hardware has crypto accelerator with a kernel driver but no userspace SDK
- wolfSSL support: `--enable-afalg`
- Check available algorithms: `cat /proc/crypto`
- Requires: `CONFIG_CRYPTO_USER_API_HASH`, `CONFIG_CRYPTO_USER_API_SKCIPHER`, `CONFIG_CRYPTO_USER_API_AEAD` in kernel config
