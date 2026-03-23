# Bare Claude Response — PR #10011

The fix checks `$enable_md5` (the raw value from `AC_ARG_ENABLE`) rather than `$ENABLED_MD5`. This is important because:

- `$enable_md5` is `"no"` only when the user explicitly passed `--disable-md5`
- `$ENABLED_MD5` could be `"no"` just from the default, which would break the existing behavior where JNI implicitly enables MD5

This way:
- `--enable-jni` alone: MD5 is still enabled (existing behavior preserved)
- `--enable-jni --disable-md5`: MD5 stays disabled (the fix)

The fix is a one-line conditional guard in `configure.ac:8087` that checks if the user explicitly passed `--disable-md5` before force-enabling MD5 in the JNI/OPENSSLEXTRA block. When `--enable-jni` is used without `--disable-md5`, behavior is unchanged. When both are used together, the explicit `--disable-md5` is respected, which is needed for FIPS builds that want to exclude non-certified algorithms.
