# Windows TBS (TPM Base Services)

> One-line summary: TBS HRESULT error codes and service troubleshooting that wolfTPM2_GetRCString() cannot decode.

**When to read**: Integrating wolfTPM on Windows, debugging TBS HRESULT errors (0x8028xxxx), or troubleshooting TPM service issues.

---

## Build Flag

`#define WOLFTPM_WINAPI` in `user_settings.h` (or `--enable-winapi`).

## How wolfTPM Maps to TBS

wolfTPM's HAL calls TBS functions in `src/tpm2_winapi.c`:
- `Tbsi_Context_Create()` — opens context (like `/dev/tpm0` on Linux)
- `Tbsip_Submit_Command()` — sends raw TPM2 command buffer
- `Tbsi_Context_Close()` — closes context

## TBS HRESULT Error Codes

**CRITICAL**: `wolfTPM2_GetRCString()` only decodes TPM2 RC codes (0x01xx /
0x09xx), **not** TBS HRESULTs. When you see `0x8028xxxx`, look up TBS errors.

| HRESULT | Name | Meaning |
|---------|------|---------|
| `0x80280001` | `TBS_E_INTERNAL_ERROR` | TBS driver internal failure |
| `0x80280002` | `TBS_E_BAD_PARAMETER` | Invalid parameter (wrong context or buffer size) |
| `0x80280004` | `TBS_E_INVALID_CONTEXT` | Context handle invalid or closed |
| `0x80280006` | `TBS_E_INSUFFICIENT_BUFFER` | Response buffer too small — increase `MAX_RESPONSE_SIZE` |
| `0x80280007` | `TBS_E_IOERROR` | I/O error with TPM driver |
| `0x8028000B` | `TBS_E_SERVICE_NOT_RUNNING` | TBS service stopped or disabled |
| `0x8028000C` | `TBS_E_TOO_MANY_TBS_SESSIONS` | Too many open contexts — close unused ones |
| `0x80280011` | `TBS_E_COMMAND_BLOCKED` | Command blocked by Group Policy |
| `0x80284001` | `TBS_E_DEACTIVATED` | TPM deactivated in BIOS/UEFI |

## Common Issues

### TBS service not running (0x8028000B)
`services.msc` → "TPM Base Services" → set to Automatic + Start.
Also verify: BIOS has TPM enabled, `tpm.msc` recognizes the TPM.

### Insufficient buffer (0x80280006)
Default `MAX_RESPONSE_SIZE` (2048) too small for large key ops (RSA 4096).
Increase in wolfTPM build.

### Context leaks
Each `wolfTPM2_Init()` opens a TBS context. Crashes without
`wolfTPM2_Cleanup()` leak contexts until TBS service restart.

### Command blocked (0x80280011)
Group Policy blocks certain commands (`TPM2_Clear`, `TPM2_HierarchyChangeAuth`).
Check: `gpedit.msc` → Computer Configuration → Administrative Templates →
System → Trusted Platform Module Services.

## Debugging

Enable verbose output: `#define WOLFTPM_DEBUG_VERBOSE` — logs each
`Tbsip_Submit_Command` call with command code and response HRESULT.

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| `0x8028000B` at init | TBS service not running | `services.msc` → start TBS |
| `0x80280006` on RSA 4096 | Response buffer undersized | Increase `MAX_RESPONSE_SIZE` |
| `0x80280011` on `TPM2_Clear` | Group Policy blocks command | Check `gpedit.msc` TPM policy |
| `0x80280004` after crash | Leaked context from prior run | Restart TBS service |
| RC string shows hex instead of name | TBS HRESULT, not TPM2 RC | Decode via TBS error table above |

## What This File Does NOT Cover

- wolfTPM API patterns and retry logic (see `products/wolftpm.md`)
- Linux TPM device model (see `platforms/linux-tpm.md`)
- TPM key provisioning workflows
