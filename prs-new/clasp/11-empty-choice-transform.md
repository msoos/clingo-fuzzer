# Fix non-termination when transforming a choice rule with empty head

With `--trans-ext=choice` or `--trans-ext=all`, choice rules are not handled natively but passed to `RuleTransform`. For an empty head, `RuleTransform::transform()` matches no case and adds the rule back via `LogicProgram::addRule()`, which transforms it again, forever. Gringo emits such a rule for some programs.

```
$ clasp --trans-ext=choice in.aspif
```
`in.aspif` (the empty choice rule `{}.`):
```
asp 1 0 0
1 1 0 0 0
0
```
Before: never terminates, in preprocessing (same with a sum body, `{} :- 2 #count{...}`).  
After: `SATISFIABLE`.

Such a rule derives nothing, so the transformation now yields no rules. Found by differential fuzzing.
