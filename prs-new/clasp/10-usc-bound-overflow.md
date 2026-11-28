# Fix overflow of core-guided optimization bounds with negative lower bound

Before a model is found, the upper bound of `UncoreMinimize` is `INT64_MAX`, while the lower bound of a level can be negative. Then `upper_ - lower_` in `pushPath()`, and `lower_ - upper_` in `validLowerBound()` and `addNext()`, overflow. The wrapped slack in `pushPath()` makes `maxW > fixW` always true, so its loop never ends. The wrapped comparison makes the lower bound look larger than the upper bound, which with only the first overflow fixed gives a wrong `UNSATISFIABLE` on larger inputs.

```
$ clasp -n0 --opt-strategy=usc in.aspif
```
`in.aspif` (from gringo: `#external a. :~ a. [-3@2] :~ a. [1@0]`):
```
asp 1 0 0
5 3 2
2 0 1 3 1
2 2 1 3 -3
0
```
Before: never terminates (UBSan reports a `signed integer overflow` in `UncoreMinimize::pushPath()`).  
After: `OPTIMUM FOUND`, `Optimization : 0 0` (as with `--opt-strategy=bb`).

Saturate the slack and compare the bounds directly. Found by differential fuzzing (UBSan build).
