# Fix externals that stay external although a rule defines them (simplified rule)

An external atom with a rule in the same step is no longer external. If that rule is simplified away before the frozen atoms are updated, e.g. because its body is false at the top level, the atom has no supports left and stays external. So the result depends on how far the input was simplified. Here `x3 :- x2` with `x2` false via `:- x2, -x2` and the fact `-x2`, and `clingo --keep-facts` gives a different answer. This generalizes #135, which handles a rule whose head is false when the rule is added.

```
$ clasp -n0 in.aspif
```
`in.aspif` (from gringo: `#external x2. [false] #external x3. [true] x1. -x2. x3 :- not not x1; x2. -1 > { x4 } :- x3. :- x4.`):
```
asp 1 0 0
1 0 1 1 0 0
1 0 1 2 0 0
5 3 1
5 4 2
1 0 1 3 0 1 4
1 0 1 5 0 1 3
1 0 0 0 2 4 2
1 0 0 0 1 5
4 2 x2 1 4
4 2 x3 1 3
4 2 x1 0
4 3 -x2 0
0
```
Before: `UNSATISFIABLE` (`x3` is still treated as an external with value true), while the equivalent program from `gringo --keep-facts` (which keeps `not not x1` as an aux atom) is `SATISFIABLE`.  
After: `SATISFIABLE` for both.

Record frozen rule heads in `LogicProgram::addRule()` and mark those without supports as released in `prepareExternals()`, as `pushHead()` already does for rules with a false head. Found by differential fuzzing (`--keep-facts` vs. default).
