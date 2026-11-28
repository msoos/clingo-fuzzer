# Fix assumption atoms reused as aux atoms

`LogicProgram::addAssumption()` does not register the assumed atoms. If an assumed atom has no rules and is larger than every atom seen so far, the program doesn't know it. `newAtom()` can then hand out the same id again, here for the aux atom of the transformed choice rule `{6}` (`--trans-ext=all`), and the assumption applies to the aux atom instead.

```
$ clasp -n0 --trans-ext=all in.aspif
```
`in.aspif` (`{6}. :- 9, not 13.` with the assumption `not 14`; atoms 9, 13, 14 have no rules):
```
asp 1 0 0
1 1 1 6 0 0
1 0 0 0 2 9 -13
6 1 -14
0
```
Before: `Models : 1` (`6` is forced).  
After: `Models : 2` (as without `--trans-ext=all`).

Register the atoms of assumptions, as for other statements. Found by differential fuzzing of incremental programs with assumptions.
