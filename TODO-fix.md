# Open bugs

## Externals with rules: text output not equivalent (gringo)

Not clear what the intended semantics is; the fuzzer skips the text pipeline for programs with `#external`.

- `bugs/open_text_external_rule.lp`: `x6 | x0. #external x2. [free] x0. x2 :- x6.` gives `{x0}` directly. Via `--text`, `x2 :- x6.` is printed without `x6`; gringo then drops the rule on reparsing, so `x2` is a free external again: `{x0}` and `{x0, x2}`.
- Conflicting duplicate externals (`#external x0. [true]` then `#external x0. [false]`): directly the first wins. `--text` prints them in reverse order, so reparsing gives the other value. The generator now declares each external only once.
