# Fix assertion when preprocessing continues after a conflict in a later step

In a later incremental step, `LogicProgram::propagate()` adds the values of atoms from earlier steps as unit clauses. If that fails, it returns false without clearing its queue. When `classifyProgram()` then fails in a later eq pass, `Preprocessor::preprocessEq()` calls `simplifyClassifiedProgram()` for cleanup. That propagates again and adds the same unit clauses to the already conflicting master solver. Here step 2 is unsatisfiable (`:- 9, not 27` with `9` a fact of step 1 and `27` false).

```
$ clasp -n0 in.aspif
```
`in.aspif` (two steps):
```
asp 1 0 0 incremental
1 1 1 4 0 0
1 0 1 6 0 1 4
1 0 1 7 0 1 -6
1 0 1 9 0 0
0
1 0 1 10 0 1 21
1 0 1 26 1 361 2 10 599 -11 645
1 0 1 27 0 1 -26
1 0 0 0 2 9 -27
1 0 1 30 0 1 6
1 0 1 31 0 2 18 -23
1 0 1 30 0 1 -31
1 0 2 30 31 0 1 -7
1 0 1 21 0 1 30
1 0 1 33 0 3 -14 -12 -34
0
```
Before: ``Assertion `!hasConflict() || isTrue(p)' failed`` in `Solver::force()` (from `SharedContext::addUnary()` in `LogicProgram::propagate()`), in step 2.  
After: step 1 `SATISFIABLE`, step 2 `UNSATISFIABLE`.

Don't propagate once the program has a conflict. Found by differential fuzzing of incremental programs.
