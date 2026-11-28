# Fix duplicate models from the var of a disjunction removed in the last eq pass

Builds on #127 (branch `pr/dup-models-disj-eq1` is `pr/dup-models-disj` plus one commit), so it could also be added to #127.

A disjunction that gets its own variable during classification and is then removed in the same pass (here `8 | 13` is satisfied by the fact `8`) loses its literal in `Preprocessor::simplifyHead()`. With more eq passes the variable is dropped, but with `--eq=1` there is no further pass. The variable then stays in the solver unconstrained and #127's fix in `finalizeDisjunctions()` doesn't see it, so every answer set is enumerated twice.

```
$ clasp -n0 --eq=1 in.aspif
```
`in.aspif` (`8 :- not 9. 8 | 13 :- not 14. 8 | 13 :- 11.`; 9, 11, 14 have no rules):
```
asp 1 0 0
1 0 1 8 0 1 -9
1 0 2 8 13 0 1 -14
1 0 2 8 13 0 1 11
0
```
Before (with #127): `Models : 2`; `--eq=0` and the default give 1.  
After: `Models : 1`.

Keep the literal of a removed disjunction, so that `finalizeDisjunctions()` fixes its variable. Found by differential fuzzing (non-ground programs vs. their instantiation).
