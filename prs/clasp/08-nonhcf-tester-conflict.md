# Fix assertion when the non-hcf tester is inconsistent

While adding body constraints to the tester of a non-hcf component, a root-level conflict can arise. Adding further unit clauses then fails.

```
$ clasp --eq=0 in.aspif
```
`in.aspif` (from gringo: `x1 | x1 : not not x2. x2 ; x0 : x1 :- x2.`):
```
asp 1 0 0
1 0 1 1 0 0
1 0 1 3 0 1 -4
1 0 1 2 0 2 5 -3
1 0 1 6 0 1 -4
1 0 1 5 0 2 -6 2
1 0 0 0 2 -4 2
1 0 2 5 2 0 1 1
4 2 x1 1 5
0
```
Before: ``Assertion `!hasConflict() || isTrue(p)' failed`` in `Solver::force()` (from `ComponentMap::addBodyConstraints()`).  
After: `SATISFIABLE`.

Skip the remaining clauses once the tester has a conflict; an inconsistent tester stays inconsistent. Found by differential fuzzing.
