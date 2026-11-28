# Fix lost choice when transforming a recursive sum rule with a choice head

With `--trans-ext=scc` (or in non-hcf components), `LogicProgram::prepareComponents()` transforms recursive aggregate rules via `RuleTransform`. For a choice head, `RuleTransform` adds `{h} :- aux`. But `DlpTr::addRule()` uses its own edge type (normal) instead of the rule's head type, which turns the choice into `h :- aux`. Here eq-preprocessing merges the body of `{d} :- a` into the recursive sum body.

```
$ clasp -n0 --trans-ext=scc in.aspif
```
`in.aspif` (from gringo: `a :- b. c. {d} :- a. e :- #sum{435: not f; 810: d} >= 1. b :- e. {f}.`):
```
asp 1 0 0
1 0 1 2 0 1 3
1 0 1 4 0 0
1 1 1 5 0 1 2
1 0 1 6 1 1 2 -7 435 5 810
1 0 1 3 0 1 6
1 1 1 7 0 0
0
```
Before: `Models : 2`; the answer set {a,b,c,e} (atoms 2,3,4,6) is missing.  
After: `Models : 3` (as without `--trans-ext=scc`).

Use a choice edge for choice rules in `DlpTr::addRule()`. Found by differential fuzzing (as a side check of a fuzzer-found input under all `--trans-ext` modes).
