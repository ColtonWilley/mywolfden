# Verification Discipline

These are mandatory rules, not suggestions.

## Never Claim Without Verifying

NEVER state that infrastructure, functions, constants, or support "already
exists" or "is already in place" without grepping for the specific symbols.
If grep returns no results, it is new work. A related feature existing does
NOT mean the target feature exists — wolfSSL has many subsystems where
versions or variants share names but have entirely separate implementations.

## Follow the Code, Not Loaded Knowledge

If the code around your target shows pattern A but your loaded knowledge
suggests pattern B, follow the code. Read the target function and at least
one analog in the same file before proposing changes. When patterns diverge,
the code you are reading is authoritative.

## Check for Applicable Checklists

Before finalizing scope on any feature addition or integration task, check
`.claude/rules/checklists/` for a matching task type. Use it as a starting
point for what files need changes — then verify each item against the actual
code. A checklist is a scope reminder, not a substitute for reading code.

## Struct Field Lifecycle

When adding a field to an internal struct, verify every lifecycle point:
- **Parse/Allocate**: where the field is populated
- **Duplicate**: deep-copy in any `Dup*` or `Copy*` function, including
  error-path cleanup of the partial copy
- **Free**: cleanup in the destructor — check ALL `#ifdef` paths

Search for existing fields on the same struct to find all lifecycle
functions. Repeat for EVERY field added, not just the primary one.
Common oversight: verifying the main field but missing auxiliary fields
(size, raw DER buffers) added alongside it.

## OpenSSL-Compat API Implementation

When implementing an OpenSSL-compatible API for a type that lacks it,
find the existing implementation on a sibling type (e.g., adding
`get_ext_d2i` to `X509_REVOKED` — find `wolfSSL_X509_get_ext_d2i`)
and trace every file it touches. The sibling implementation defines the
scope. Replicate its file-by-file pattern rather than inventing
non-standard APIs.

## Deep Knowledge (T3) Retrieval

The `knowledge/` directory contains domain-specific reference files that are
NOT auto-loaded. An index of available files is included via `@knowledge/index.md`
in CLAUDE.md — check the "Read When" column to decide if a file is relevant.

Rules for T3 usage:
- **Read on demand, not by default.** Only read a knowledge file when your
  current task matches its "Read When" trigger.
- **Code is authoritative.** If a knowledge file contradicts the code you
  are reading, follow the code. Knowledge files capture patterns that were
  true when written — the code reflects what is true now.
- **One file at a time.** Read the most relevant file, use it, move on.
  Do not bulk-load T3 files speculatively.
- **Failure modes are highest-value.** The "Known Failure Modes" tables in
  T3 files capture hard-won debugging knowledge that saves hours. When
  debugging, check the relevant T3 file's failure mode table first.
