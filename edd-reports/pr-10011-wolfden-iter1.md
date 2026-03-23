# wolfDen Claude Response (iter1) — PR #10011

Here's a summary of the fix:

**Problem:** `configure.ac` line 6042-6053 listed `ENABLED_OPENSSLEXTRA` and `ENABLED_OPENSSLALL` as conditions that force-enable MD5. Since `--enable-jni` enables both OPENSSLEXTRA and OPENSSLALL, this created a transitive dependency chain: `--enable-jni` → OPENSSLEXTRA/OPENSSLALL → MD5 forced on, making `--disable-md5` ineffective.

**Fix:** Removed `ENABLED_OPENSSLEXTRA` and `ENABLED_OPENSSLALL` from the MD5 dependency conditions. The OPENSSLEXTRA/OPENSSLALL code paths in the source are already properly guarded with `#ifndef NO_MD5` — they compile and work correctly without MD5. Per the dependency cascading principle in `configure.ac`, integration flags like `--enable-jni` should only set `ENABLED_OPENSSLEXTRA="yes"` without also forcing non-certified algorithms (MD5, DES3, etc.) that the feature *happens to use*. This is especially important for FIPS builds where non-certified algorithms must remain excludable.

**Impact:** `./configure --enable-jni --disable-md5` will now correctly build without MD5. Other flags that genuinely require MD5 (wpas, haproxy, nginx, openssh, openvpn, etc.) still force-enable it.
