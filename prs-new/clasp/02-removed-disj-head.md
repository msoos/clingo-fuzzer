# Fix dangling disjunction head after removing a satisfied disjunction

Without eq-preprocessing, the supports of a head are rebuilt while computing the upper closure. If a disjunction becomes satisfied before all its supports are reached, `PrgDisj::detach()` removes it only from the bodies seen so far. For a body reached later, `addHeadsToUpper()` marks its heads dirty only for eq or false heads, not removed ones. So the edge to the removed disjunction survives and is followed during the SCC check.

```
$ clasp --eq=0 in.aspif
```
`in.aspif` (`5|6. 6|11. 6|11 :- 5, 30. 11 :- 23. 35 :- 5. 5 :- 35. 23. 30.`):
```
asp 1 0 0
1 0 2 5 6 0 0
1 0 2 6 11 0 0
1 0 1 11 0 1 23
1 0 2 6 11 0 2 5 30
1 0 1 35 0 1 5
1 0 1 5 0 1 35
1 0 1 23 0 0
1 0 1 30 0 0
0
```
Before: ``Assertion `n < size()' failed`` in `pod_vector::operator[]` (from `LogicProgram::getDisj()` in `PrgBody::scc()`).  
After: `SATISFIABLE` (2 answer sets with `-n0`, as with default options).

Mark the heads dirty for any non-relevant head. Found by differential fuzzing.
