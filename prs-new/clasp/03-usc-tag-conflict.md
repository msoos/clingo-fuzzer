# Fix root-level error of core-guided optimization when pushing the tag conflicts

When enumerating optimal models, `UncoreMinimize::integrate()` first pushes its tag literal as a new root level. If propagating it conflicts, `integrate()` returns before `initRoot()`, so `eRoot_`/`aTop_` stay below the solver's root level. This happens when lookahead or the partial stability check find the program unsatisfiable only above level 0. `popPath()` in `handleUnsat()` then fails.

```
$ clasp --partial-check=10,2 --lookahead=atom --opt-strategy=usc -n0 --opt-mode=optN in.aspif
```
`in.aspif`:
```
asp 1 0 0
1 1 1 5 0 0
1 0 2 6 7 0 0
1 1 1 8 0 0
1 1 1 33 0 1 12
1 0 1 35 0 2 36 32
1 0 1 44 0 1 8
1 0 1 32 0 1 33
1 0 1 52 0 1 -5
1 0 1 7 0 1 52
1 0 0 0 2 -52 53
1 0 1 53 0 0
1 0 1 6 0 1 32
1 0 1 59 0 1 44
1 0 1 61 0 1 -8
1 0 0 0 2 60 -61
1 0 1 6 0 1 60
1 0 1 60 0 1 6
1 0 0 0 1 -60
1 0 1 62 0 1 -59
1 0 1 60 0 1 -62
1 1 1 7 0 1 35
1 0 1 97 0 1 6
1 1 1 12 0 2 35 97
1 0 1 99 0 1 7
1 0 1 98 0 1 99
1 0 1 36 0 1 98
1 0 1 107 0 0
1 0 1 110 0 1 -106
1 0 2 109 32 0 1 -110
1 0 1 106 0 2 107 109
2 0 0
0
```
Before: `*** ERROR: (clasp): You must not mess with my root level!`  
After: `UNSATISFIABLE` (as with default options).

Call `initRoot()` also when `prepare()` fails. Found by differential fuzzing.
