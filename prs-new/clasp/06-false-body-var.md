# Fix duplicate models from the var of a body derived false during eq-preprocessing

If a body that already got its own solver variable is derived false and removed while classifying the program, `Preprocessor::simplifyBody()` clears its literal but, unlike for superfluous bodies, does not request reclassification. The variable then stays in the solver without any constraint, so every answer set is enumerated twice. Here body `not 55` gets a variable in the second eq pass before `55` has one, and `55` is then derived true.

```
$ clasp -n0 in.aspif
```
`in.aspif`:
```
asp 1 0 0
1 0 1 40 0 1 -41
1 0 0 0 1 -42
1 0 2 49 45 0 0
1 0 1 39 0 1 28
1 0 1 42 0 1 49
1 1 1 28 0 0
1 0 1 55 0 2 42 -46
1 0 1 41 0 1 39
1 0 1 48 0 1 -55
1 0 2 48 62 0 0
1 1 1 46 0 1 40
1 0 0 0 2 40 -64
0
```
Before: `Models : 4` (each answer set twice; `--eq=0` and `--eq=1` give 2).  
After: `Models : 2`.

Reclassify if the variable is not used by an atom, as for superfluous bodies. Found by differential fuzzing.
