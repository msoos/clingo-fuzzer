# Fix VMTF list corruption with a single-element list

`ClaspVmtf::VarInfo::inList()` tests `prev_ != next_`, which is false for the only element of the list (both links are the sentinel). Here, after an empty first incremental step, the list holds one variable. `endInit()` of the next step takes that variable as new, appends the other new variables behind it, and then appends it a second time.

```
$ clasp -n0 --heuristic=vmtf in.aspif
```
`in.aspif` (two steps, the first one empty):
```
asp 1 0 0 incremental
0
1 0 1 14 0 2 15 -2
1 1 3 5 13 3 0 1 14
1 0 1 29 0 2 -32 -33
1 0 1 15 0 1 29
1 0 1 35 0 1 13
1 0 1 37 0 1 -35
1 0 2 34 36 0 1 -37
0
```
Before: ``Assertion `v && v < score_.size() && !score_[v].inList()' failed`` in `ClaspVmtf::addToList()` (from `ClaspVmtf::endInit()`).  
After: `SATISFIABLE` in both steps.

Also check whether the variable is the sentinel's successor. Found by differential fuzzing of incremental programs.
