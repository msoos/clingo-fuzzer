# Fix wrong optimum of core-guided optimization with lookahead

`UncoreMinimize::reason()` called `initRoot()`, which sets the external root `eRoot_` to the solver's root level if `eRoot_ == aTop_`. But `pushPath()` updates `aTop_` only after pushing all assumptions of an iteration. With `--lookahead`, pushing an assumption can lead to a conflict whose analysis asks for the reason of a literal fixed by the minimizer, so `eRoot_` moved above the minimizer's own assumptions. These then counted as fixed, giving singleton cores and a too high lower bound.

```
$ clasp -n0 --opt-mode=optN --opt-strategy=usc --lookahead=atom in.aspif
```
`in.aspif`:
```
asp 1 0 0
1 1 2 2 3 0 0
1 0 1 4 0 1 3
1 1 1 5 0 0
1 0 1 6 0 2 3 -5
1 0 1 7 0 1 5
1 0 1 8 0 2 2 3
1 0 1 10 0 2 -9 -3
1 0 0 0 2 7 -2
2 0 1 4 -3
2 1 2 10 7 6 7
2 2 1 8 3
0
```
Before: `OPTIMUM FOUND`, `Optimization: 0 7 0`.  
After: `Optimization: 0 7 -3` (the optimum: atom 3 true, 2 and 5 false).

Don't call `initRoot()` in `reason()`; the reason of such a literal are the decisions up to its level. Found by differential fuzzing.
