# Fix duplicate models from vars of dropped disjunctions

Without eq-preprocessing, a disjunction gets its own solver variable during preprocessing. If the disjunction is later dropped (it was removed, one of its atoms became a fact, or it lost all supports), nothing constrains that variable, so every answer set is enumerated twice.

```
$ clasp -n0 --eq=0 in.aspif
```
`in.aspif`:
```
asp 1 0 0
1 0 1 8 0 0
1 0 1 10 0 1 7
1 0 2 10 6 0 1 -11
1 0 1 7 0 1 8
4 2 a6 1 6
4 2 a7 1 7
4 2 a8 1 8
4 3 a10 1 10
0
```
Before: `Models: 2` (the same answer set twice).  
After: `Models: 1`.

Two more cases, same command:
```
asp 1 0 0
1 0 1 1 0 0
1 0 1 2 0 1 -3
1 1 1 4 0 0
1 0 2 5 2 0 1 4
1 1 1 6 0 0
1 0 1 7 0 1 -3
1 0 0 0 1 -7
0
```
Before: `Models: 8`. After: `Models: 4`.
```
asp 1 0 0
1 0 1 5 0 2 3 4
1 0 2 6 7 0 1 -5
1 0 1 3 0 0
1 0 1 4 0 0
0
```
Before: `Models: 2`. After: `Models: 1`.

In `finalizeDisjunctions()`, fix the variable of such a dropped disjunction to false (via a false aux atom with its literal). Found by differential fuzzing.
