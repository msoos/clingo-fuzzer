# Fix stale dependency edge when merging duplicate weight-body literals

When simplifying a count/sum body, two subgoals that map to the same solver literal (e.g. `5` and `not 4` with 4 equivalent to `not 5`) are merged by adding their weights, but unlike for normal bodies the dependency edge of the dropped subgoal was kept. Propagating that atom later reached a body that no longer contains it.

```
$ clasp --trans-ext=no in.aspif
```
`in.aspif` (from gringo: `x3 :- not x4. { x0 : not x3; x4 } != 0. x5. x0.`):
```
asp 1 0 0
1 0 1 1 0 0
1 0 1 2 0 0
1 0 1 3 0 0
1 0 1 4 0 1 -5
1 1 1 5 0 1 3
1 0 1 6 1 1 2 5 1 -4 1
1 0 0 0 2 3 -6
4 2 x4 1 5
4 2 x3 1 4
4 2 x0 0
4 2 x5 0
0
```
Before: ``Assertion `std::find(goals_begin(), goals_end(), p) != goals_end()' failed`` in `PrgBody::propagateAssigned()`.  
After: `SATISFIABLE`.

Remove the edge of the merged subgoal, as for normal bodies. Found by differential fuzzing.
