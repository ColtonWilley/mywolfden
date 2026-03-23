---
paths:
  - "**/IDE/WIN*/**"
  - "**/visual*studio*/**"
  - "**/*.sln"
  - "**/*.vcxproj"
---

# Windows Platform Patterns

## Build Methods
1. **Visual Studio solution**: `wolfssl.sln` in root or `IDE/WIN/` — builds static lib or DLL
2. **CMake**: `cmake -G "Visual Studio 17 2022" -DWOLFSSL_TLS13=yes ..`
3. **vcpkg**: `vcpkg install wolfssl` — installs prebuilt
4. **NuGet**: available as NuGet package for Visual Studio projects

## Common Windows Issues

### Winsock Initialization
**Symptom**: `wolfSSL_connect()` fails immediately with error -308.
**Root cause**: `WSAStartup()` not called before any socket/wolfSSL operations.
**Fix**: Call `WSAStartup(MAKEWORD(2,2), &wsaData)` at program start.

### DLL vs Static Library
- Static lib: define `WOLFSSL_LIB` in consuming project
- DLL: define `WOLFSSL_DLL` in consuming project
- **Common error**: "LNK2019: unresolved external symbol" — wrong define for lib type
- DLL exports controlled by `WOLFSSL_API` macro

### Visual Studio Compiler Settings
- `/MT` vs `/MD` — must match between wolfSSL lib and consuming project
- Debug vs Release builds — don't mix (different CRT)
- x86 vs x64 — must match architecture
- Incremental linking may cause issues with FIPS integrity check

### SChannel Interop
- wolfSSL can replace SChannel as Windows TLS provider
- Custom I/O callbacks may be needed for Winsock integration
- Certificate store: wolfSSL doesn't read Windows cert store by default
  - Load system CAs: export from Windows cert store → load via `wolfSSL_CTX_load_verify_buffer()`
  - Or use `--enable-sys-ca-certs` for automatic system CA loading

### Windows CE / Compact
- Limited API surface — some POSIX functions missing
- Define `WOLFSSL_WINCE` in user_settings.h
- Threading: use Windows threading (`WOLFSSL_USER_THREADING`)
- Time: implement `time()` using system tick or RTC

## Common Build Errors on Windows
- `C4996` warnings: POSIX function deprecation — define `_CRT_SECURE_NO_WARNINGS`
- `LNK2005` duplicate symbols: conflicting CRT settings between lib and app
- Missing `sys/socket.h`: normal on Windows, wolfSSL uses Winsock headers
- `error C2065: 'ssize_t'`: define in user_settings.h or use `WOLF_SSIZE_T`

## Windows CryptoAPI / CNG Integration

- wolfSSL does **not** use Windows CryptoAPI or CNG internally — it has its own crypto
- Common customer pattern: need to access Windows certificate store for CA certs
  - `CertOpenSystemStore(0, "ROOT")` → enumerate → export DER → `wolfSSL_CTX_load_verify_buffer()`
  - Or use `--enable-sys-ca-certs` (wolfSSL 5.6.0+) which handles this automatically
- CNG key storage: customers may want to use CNG-stored private keys with wolfSSL
  - Requires custom I/O callback or PK callback (`wolfSSL_CTX_SetEccSignCb`, etc.)
  - wolfSSL's `--enable-pkcallbacks` enables this pattern
- **SChannel replacement**: wolfSSL can replace SChannel as the TLS provider
  - Common in FIPS deployments where SChannel's FIPS status is insufficient
  - Must handle Winsock I/O via wolfSSL custom I/O callbacks
