# Fix VMTF list corruption from the sentinel var in integrated clauses

`ClauseCreator::integrate()` passes unprepared literals to the heuristic. Brave/cautious enumeration with several threads integrates clauses containing `~stepLiteral()`, which is the sentinel var 0 in single-shot solving. `ClaspVmtf::newConstraint()` then moved var 0, i.e. its own list head.

```
$ clasp -n0 --heuristic=vmtf -t2 --enum-mode=brave in.aspif
```
`in.aspif` (from gringo: `{a;b}.`):
```
asp 1 0 0
1 1 2 1 2 0 0
4 1 a 1 1
4 1 b 1 2
0
```
Before: ``Assertion `v && v < score_.size() && score_[v].inList()' failed`` in `ClaspVmtf::removeFromList()`.  
After: 3 models.

Skip var 0 in `ClaspVmtf::newConstraint()`. Found by differential fuzzing.
