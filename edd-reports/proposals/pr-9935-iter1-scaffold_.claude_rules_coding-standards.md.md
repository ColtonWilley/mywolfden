# Improvement Proposal: PR #9935, Iteration 1

**File:** `scaffold/.claude/rules/coding-standards.md`
**Action:** `insert_after`
**Anchor:** `WOLFSSL_API`

## Reasoning
Developers adding new public API functions often miss the WOLFSSL_ABI annotation, forget WOLFSSL_ENTER, or use malloc instead of XMALLOC. This is a reusable checklist applicable to any new wolfSSL_* function, not specific to IP SANs.

## Proposed Content
```

**Public API function checklist** — when adding a new `wolfSSL_*` function to `ssl.h` + `ssl.c`:
- Declare with both `WOLFSSL_ABI` (ABI stability) and `WOLFSSL_API` (symbol export) in `ssl.h`
- Open the implementation with `WOLFSSL_ENTER("wolfSSL_your_function_name")`
- Validate pointer args immediately; return `BAD_FUNC_ARG` on null
- Use `XMALLOC(size, heap, DYNAMIC_TYPE_*)` — never raw `malloc`; pick the closest existing `DYNAMIC_TYPE_` constant
- Free any previously stored value before overwriting (XFREE + NULL the field)
```
