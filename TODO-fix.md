# Open bugs

## Unfounded-set reason asked for with --no-lookback in parallel split mode (clasp)

Repro: `bugs/open_ufs_reason_nolookback_threads.lp` (not minimized yet; minim.py should work, the crash is ~90% reproducible)

```bash
clingo -n0 --opt-mode=optN -q --no-lookback -t3,split bugs/open_ufs_reason_nolookback_threads.lp
# Assertion `strategy_ == only_reason && reasons_' failed (unfounded_check.cpp:220, DefaultUnfoundedCheck::reason)
```

Found in round 11 with `--no-lookback --rand-freq=0.1 --keep-facts --opt-heuristic=sign --dom-mod=pos,show -t3,split --restart-on-model`.
With `--no-lookback` the unfounded check uses the `no_reason` strategy (unfounded_check.cpp:109), so it stores no reasons;
something still asks it for one, probably conflict analysis outside normal search (guiding-path splitting, optimization cores, or
`resolveToCore`). Check whether it also happens with `-t1`, `compete` mode, and without `--opt-mode=optN`.

## Externals with rules: text output not equivalent (gringo)

Not clear what the intended semantics is; the fuzzer skips the text pipeline for programs with `#external`.

- `bugs/open_text_external_rule.lp`: `x6 | x0. #external x2. [free] x0. x2 :- x6.` gives `{x0}` directly. Via `--text`, `x2 :- x6.` is printed without `x6`; gringo then drops the rule on reparsing, so `x2` is a free external again: `{x0}` and `{x0, x2}`.
- Conflicting duplicate externals (`#external x0. [true]` then `#external x0. [false]`): directly the first wins. `--text` prints them in reverse order, so reparsing gives the other value. The generator now declares each external only once.
