# Fix external atoms that stay external although a rule defines them

An external atom with a rule in the same step is no longer external. If the atom was already false when its rule was added (gringo emits `:- x0` before the rule), `pushHead()` dropped the head, the atom got no support and stayed external with its value.

```
$ clasp in.aspif
```
`in.aspif` (from gringo: `1 {x0; y} 1. #external x0. [true] :- x0.`):
```
asp 1 0 0
1 0 1 1 0 0
5 2 1
1 0 0 0 1 2
1 1 2 2 3 0 1 1
1 0 1 4 1 1 2 2 1 3 1
1 0 1 5 1 2 2 2 1 3 1
1 0 1 6 0 2 4 -5
1 0 0 0 2 1 -6
4 2 x0 1 2
4 1 y 1 3
0
```
Before: `UNSATISFIABLE`.  
After: `SATISFIABLE` (answer set {y}).

In `pushHead()`, give such a frozen atom the dummy support edge also used for released externals, so `updateFrozenAtoms()` unfreezes it. Found by differential fuzzing.
