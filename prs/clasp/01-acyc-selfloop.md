# Fix assertion on true self-loop acyc edge with sat-prepro

A self-loop `#edge` whose condition is true makes `AcyclicityCheck::init()` set a conflict while attaching to the graph, but `init()` still returned true. SatElite preprocessing then propagated on a conflicting solver.

```
$ clasp --sat-prepro=2 in.aspif
```
`in.aspif` (from gringo: `#edge (0,0).`):
```
asp 1 0 0
8 0 0 0
0
```
Before: ``Assertion `!hasConflict()' failed`` in `Solver::unitPropagate()`.  
After: `UNSATISFIABLE`.

Return `!s.hasConflict()` from `AcyclicityCheck::init()`. Found by differential fuzzing.
