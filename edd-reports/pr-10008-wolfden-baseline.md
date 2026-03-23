# wolfDen Claude Response (baseline) — PR #10008

Fixed. Here's the summary of the release 5.9.0 prep state:

**All version bumps are correct (5.8.4 → 5.9.0):**
- `wolfssl/version.h` — version string and hex (`0x05009000`)
- `configure.ac` — `AC_INIT` version + soversion 44:0:1 → 45:0:0
- `CMakeLists.txt` — project version + soversion (matches configure.ac)
- `ChangeLog.md` — new 5.9.0 header entry added
- `README.md` — release section updated, deprecated notes removed
- `wolfssl.rc` (UTF-16) — FILEVERSION/PRODUCTVERSION, copyright 2026
- `IDE/WIN10/wolfssl-fips.rc` — versions + copyright 2025 → 2026
- `IDE/WIN-SRTP-KDF-140-3/wolfssl-fips.rc` — versions updated

**Bug fixed:** `IDE/WIN-SRTP-KDF-140-3/wolfssl-fips.rc` copyright year was still "2023" — updated to "2026" to match the other RC files.
