# Bare Claude Response — PR #10008

All version files have been updated. Here's a summary of the changes for release 5.9.0:

| File | Change |
|------|--------|
| `configure.ac` | AC_INIT version 5.8.4 → 5.9.0, library version 44:0:1 → 45:0:0 |
| `CMakeLists.txt` | project VERSION 5.8.4 → 5.9.0, library version 44:0:1 → 45:0:0 |
| `wolfssl/version.h` | VERSION_STRING "5.9.0", VERSION_HEX 0x05009000 |
| `wolfssl.rc` | FILEVERSION/PRODUCTVERSION 5,9,0,0 + copyright 2026 |
| `IDE/WIN10/wolfssl-fips.rc` | FILEVERSION/PRODUCTVERSION 5,9,0,0 + copyright 2026 |
| `IDE/WIN-SRTP-KDF-140-3/wolfssl-fips.rc` | FILEVERSION/PRODUCTVERSION 5,9,0,0 |
| `ChangeLog.md` | New 5.9.0 release header (Mar 22, 2026) |
| `README.md` | Release header updated to 5.9.0 |

**Notes:**
- Library version bumped to 45:0:0 (FIRST incremented for new minor release, SECOND and THIRD reset)
- Historical references to 5.8.4 in `ChangeLog.md`, `README-async.md`, and `wolfcrypt/test/README.md` were left unchanged (they're accurate historical references)
- Template files (`*.in`) using `@VERSION@` substitution need no changes — they pull from configure.ac automatically
- There's a leftover `wolfssl.rc.utf8` temp file that I couldn't remove (permission denied) — please delete it manually
