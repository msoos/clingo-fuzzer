# Fix wrong UNSAT from a lost disjunction support

`PrgHead::simplifySupports()` detected duplicate choice supports by node id, but a body and a disjunction can have the same id. A duplicate choice edge from body 0 replaced the support from disjunction 0 and left the disjunction marked as seen, so the next eq-pass dropped it as well and made the atom false.

```
$ clasp in.aspif
```
`in.aspif` (from gringo: `x0 : not x1; x3. x2 :- x3. 13 <= #sum { 9 : x2; 5 : x3 } :- not x2.`):
```
asp 1 0 0
1 0 1 1 0 0
1 0 1 2 0 1 -3
1 0 1 3 0 1 4
1 0 2 5 4 0 1 1
1 1 2 3 4 0 1 2
1 0 1 6 1 13 2 3 9 4 5
1 0 0 0 2 2 -6
4 2 x0 1 5
4 2 x3 1 4
4 2 x2 1 3
0
```
Before: `UNSATISFIABLE`.  
After: `SATISFIABLE` (answer set {x2, x3}).

Compare the support nodes, not their ids. Found by differential fuzzing.
