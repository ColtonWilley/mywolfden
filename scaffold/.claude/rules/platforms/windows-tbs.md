---
paths:
  - "**/tbs.h"
  - "**/IDE/WIN*/**"
  - "repos/wolftpm/**"
---

# Windows TBS (TPM Base Services) — wolfTPM Integration

## Overview

wolfTPM on Windows uses the TBS (TPM Base Services) API when built with `WOLFTPM_WINAPI`.
TBS is the Windows kernel-mode driver interface to the TPM — all TPM access on Windows goes through it.

**Build flag**: `#define WOLFTPM_WINAPI` in user_settings.h (or `--enable-winapi` with autotools)

## How wolfTPM Maps to TBS

wolfTPM's HAL layer calls these TBS functions:
- `Tbsi_Context_Create()` — opens a TBS context (like `/dev/tpm0` on Linux)
- `Tbsip_Submit_Command()` — sends a raw TPM2 command buffer and receives the response
- `Tbsi_Context_Close()` — closes the TBS context

The mapping is in `src/tpm2_winapi.c`. wolfTPM sends the same TPM2 command bytes it would
send over SPI/I2C, but TBS handles the transport.

## TBS HRESULT Error Codes

TBS errors use facility code `0x8028xxxx` (FACILITY_TPM_BASE = 0x28).

**CRITICAL**: wolfTPM returns raw TBS HRESULTs on failure. `wolfTPM2_GetRCString()` only decodes
TPM2 RC codes (0x01xx / 0x09xx), not TBS HRESULTs. When you see `0x8028xxxx`, look up the
TBS error, not the TPM2 response code table.

| HRESULT | Name | Meaning |
|---------|------|---------|
| `0x80280001` | TBS_E_INTERNAL_ERROR | TBS driver internal failure |
| `0x80280002` | TBS_E_BAD_PARAMETER | Invalid parameter to TBS call (often wrong context or buffer size) |
| `0x80280003` | TBS_E_INVALID_OUTPUT_POINTER | NULL output pointer passed |
| `0x80280004` | TBS_E_INVALID_CONTEXT | TBS context handle is invalid or was closed |
| `0x80280006` | TBS_E_INSUFFICIENT_BUFFER | Response buffer too small — increase `MAX_RESPONSE_SIZE` |
| `0x80280007` | TBS_E_IOERROR | I/O error communicating with TPM driver |
| `0x80280009` | TBS_E_INVALID_CONTEXT_PARAM | Invalid parameter in `TBS_CONTEXT_PARAMS` |
| `0x8028000B` | TBS_E_SERVICE_NOT_RUNNING | TPM Base Services service is stopped or disabled |
| `0x8028000C` | TBS_E_TOO_MANY_TBS_SESSIONS | Too many TBS contexts open — close unused ones |
| `0x80280011` | TBS_E_COMMAND_BLOCKED | Command blocked by TBS policy (e.g., `TPM2_Clear` blocked in production) |
| `0x80280012` | TBS_E_INVALID_RESOURCE | Resource handle not recognized by TBS |
| `0x80280015` | TBS_E_NOTHING_TO_UNLOAD | Attempted to unload a resource that isn't loaded |
| `0x80284001` | TBS_E_DEACTIVATED | TPM is deactivated in BIOS/UEFI settings |
| `0x80284002` | TBS_E_OWNER_AUTH_NOT_FOUND | Owner auth not set; some operations require `TPM2_TakeOwnership` first |

## Common Troubleshooting

### TBS service not running
**Symptom**: `TBS_E_SERVICE_NOT_RUNNING` (0x8028000B)
**Fix**: Run `services.msc` → find "TPM Base Services" → set to Automatic and Start.
Also check: BIOS must have TPM enabled; Windows must recognize the TPM in `tpm.msc`.

### Insufficient buffer
**Symptom**: `TBS_E_INSUFFICIENT_BUFFER` (0x80280006)
**Cause**: wolfTPM's response buffer is smaller than the TPM response.
**Fix**: Increase `MAX_RESPONSE_SIZE` in wolfTPM build (default 2048 may be too small for
large key operations like RSA 4096).

### Context limits
TBS allows a limited number of concurrent contexts. Each `wolfTPM2_Init()` call opens one.
If a program crashes without calling `wolfTPM2_Cleanup()`, the context leaks until the
TBS service is restarted.

### Command blocked
**Symptom**: `TBS_E_COMMAND_BLOCKED` (0x80280011)
**Cause**: Windows Group Policy or TBS configuration blocks certain TPM commands (often
`TPM2_Clear`, `TPM2_HierarchyChangeAuth`) for security.
**Fix**: Check `gpedit.msc` → Computer Configuration → Administrative Templates →
System → Trusted Platform Module Services.

## Debugging

Enable verbose wolfTPM debug output to see the raw TBS call flow:
```c
#define WOLFTPM_DEBUG_VERBOSE
```
This logs each `Tbsip_Submit_Command` call with the command code and response HRESULT.
