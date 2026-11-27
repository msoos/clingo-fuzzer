# Fix lost #edge/#show conditions after merging a frozen body

Bodies used as conditions (of `#edge` or `#show`) are frozen, but when such a body is merged into an equivalent body, the root does not inherit the frozen state. If the root is later removed as superfluous, the condition resolves to false and the edge is dropped.

```
$ clasp -n0 in.aspif
```
`in.aspif`:
```
asp 1 0 0
1 1 1 3 0 0
1 0 1 6 0 1 3
1 0 1 5 0 1 6
1 0 1 7 0 1 -8
1 0 0 0 1 -7
8 0 0 2 3 -8
0
```
Before: 2 answer sets, one with atom 3, where the edge (0,0) is a self-loop.  
After: 1 answer set.

In `LogicProgram::mergeEqBodies()`, mark the root frozen if the merged body is (adds `PrgBody::frozen()`). Found by differential fuzzing.
