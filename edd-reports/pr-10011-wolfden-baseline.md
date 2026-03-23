# wolfDen Claude Response (baseline) — PR #10011

The fix removes the conditional MD5 force-enable from the `--enable-jni` block. 

**The issue**: When `--enable-jni` enables OPENSSLEXTRA, it was also force-enabling MD5 (with only a partial guard checking `enable_md5`). This is problematic for FIPS builds where MD5 should remain disabled as a non-certified algorithm.

**The fix**: Remove the `ENABLED_MD5="yes"` block entirely from the JNI/OPENSSLEXTRA section. JNI requires OPENSSLEXTRA, but OPENSSLEXTRA doesn't inherently require MD5. The general MD5 dependency logic at line 6043-6053 handles cases where OPENSSLEXTRA is explicitly enabled by the user, and for the JNI path (where OPENSSLEXTRA is implicitly enabled later), MD5 should respect the user's explicit `--disable-md5` or the default-off state.

This matches the upstream fix in PR #10011 (commit `5ad9f1f68`), which is on `master` but not yet in our checkout at `255f14bab`.
