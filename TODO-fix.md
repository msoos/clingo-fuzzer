# Open bugs

## usc + lookahead + optN: wrong optimum (clasp)

Repro: `bugs/open_usc_lookahead_optN.aspif`

```bash
clingo -n0 --opt-mode=optN --opt-strategy=usc --lookahead=atom bugs/open_usc_lookahead_optN.aspif
# OPTIMUM FOUND, Optimization: 0 7 0 -- but 0 7 -3 exists
```

The program (aspif atom numbers):

```
{2;3}.  4 :- 3.  {5}.  6 :- 3, not 5.  7 :- 5.  8 :- 2, 3.  10 :- not 9, not 3.  :- 7, not 2.
#minimize { 3@2 : 8 }.  #minimize { 7@1 : 10; 7@1 : 6 }.  #minimize { -3@0 : 4 }.
```

The optimum is `0 7 -3` (3 true, 2 and 5 false), checked by hand:
- Priority 2 is 0 if not both 2 and 3 are true.
- Priority 1 is then at least 7: 3 false makes 10 true; 3 and 5 true forces 2 through `:- 7, not 2`, which breaks priority 2; 3 true with 5 false makes 6 true.
- Priority 0 is -3 when 3 is true.

What is known:
- Wrong: optN with `--opt-strategy=usc` (also `usc,oll`, `usc,one`) together with `--lookahead=atom|body`.
- Wrong: `--opt-mode=optN -n1` gives the same.
- Right: `--opt-mode=opt`; optN without lookahead; optN with `--lookahead=atom,1`; optN with `--eq=0`; plain `opt` with `-t2` (there the minimizer also uses its tag).
- The original clasp 3.4.2 (`dfe6214`) behaves the same, so this is not caused by the fixes on `bug-fixes`.
- With `--verbose=3`, the run without lookahead finds `0 7 0`, then `0 7 -3`. With lookahead, the optimum is declared right after the first model. So a solve under assumptions in `UncoreMinimize` (with `useTag`, which optN always sets) apparently comes back unsatisfiable wrongly, giving a wrong core or lower bound.
- Tried and reverted, no effect: forcing implied literals in `Lookahead::checkImps()` with the level's decision as reason instead of `lit_true()`.

Places to look:
- `UncoreMinimize::pushPath`: an assumption false at level <= `eRoot_` becomes a one-literal core. Is lookahead's root-level inference valid there?
- `UncoreMinimize` handling of the tag in optN.
- `Lookahead::propagateLevel` and its undo bookkeeping (`saved_`) across `pushRoot`/`popRootLevel`.

## Externals with rules: text output not equivalent (gringo)

Not clear what the intended semantics is; the fuzzer skips the text pipeline for programs with `#external`.

- `bugs/open_text_external_rule.lp`: `x6 | x0. #external x2. [free] x0. x2 :- x6.` gives `{x0}` directly. Via `--text`, `x2 :- x6.` is printed without `x6`; gringo then drops the rule on reparsing, so `x2` is a free external again: `{x0}` and `{x0, x2}`.
- Conflicting duplicate externals (`#external x0. [true]` then `#external x0. [false]`): directly the first wins. `--text` prints them in reverse order, so reparsing gives the other value. The generator now declares each external only once.
