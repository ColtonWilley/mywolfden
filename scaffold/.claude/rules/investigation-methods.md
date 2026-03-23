# Investigation Self-Check

Before proposing a change or stating a conclusion, ask yourself:

## Did I read the actual code?

- Did I read the target function, or am I inferring from a loaded pattern?
- Is there an analogous function nearby that already handles a similar case?
  (Check the same file — wolfSSL groups related operations together.)
- If I'm claiming a function exists or works a certain way, did I Grep/Read it?
- If I'm proposing a code change, did I read the function I'm modifying?

## Am I following the code or my loaded knowledge?

- If the code around my target shows pattern A but my loaded knowledge
  suggests pattern B, am I following the code? (Follow the code.)
- Am I reaching for a familiar pattern when the code shows something simpler?
- Would a developer reading only this file see the same pattern I'm applying?

## Did I check the build configuration context?

- What `#ifdef` guards are active on the code path I'm tracing?
- Did I verify the macro name exists (in configure.ac, settings.h, or
  user_settings.h)? Misspelled macros compile silently.
- Am I tracing a code path that actually compiles under the active config?

## Is my conclusion supported by evidence?

- Can I point to specific code I read to support each claim?
- If I haven't verified something, did I say so?
- "I expect X based on the pattern in Y, but I haven't verified" is
  always better than a confident assertion that turns out wrong.
