# Fix assertion when the remaining atom of a shrinking disjunction is an eq atom

When all but one atom of a disjunction become false, `PrgDisj::propagateAssigned()` adds the remaining atom as a head of the disjunction's supports. That atom may have been merged into an equivalent atom in the meantime, so it is no longer relevant. Independent of #130, which handles the same situation for the supports.

```
$ clasp --backprop in.aspif
```
`in.aspif`:
```
asp 1 0 0
1 1 1 4 0 0
1 0 1 5 0 0
1 0 1 6 0 1 -7
1 0 1 7 0 1 -4
1 0 1 8 0 1 7
1 0 1 10 0 1 -4
1 0 0 0 2 12 -7
1 0 1 18 0 1 -19
1 0 1 21 0 1 -10
1 0 0 0 2 -21 20
1 0 2 10 20 0 1 -18
1 0 1 22 0 0
1 1 1 19 0 0
1 0 1 28 0 0
1 0 1 9 0 0
1 0 0 0 1 11
1 0 1 12 0 0
0
```
Before: ``Assertion `relevant() && h->relevant()' failed`` in `PrgBody::addHead()`.  
After: `SATISFIABLE` (2 answer sets with `-n0`, as with `--eq=0 --no-backprop`).

Add the root of the remaining atom instead. Found by differential fuzzing.
