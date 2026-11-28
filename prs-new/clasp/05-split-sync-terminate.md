# Fix early termination of parallel split-mode search after a sync

A thread waiting for work in `SharedData::requestWork()` leaves its wait when a synchronization starts. `ParallelSolve::requestWork()` then took the empty result as "no work left" unless the sync was still active. The last thread may have completed the sync in between. For example, after the optimum is proven, it sets up the enumeration of optimal models with a fresh initial path. The waiting thread then terminates the whole search.

```
$ clasp -n0 --opt-mode=optN -t8,split in.aspif
```
`in.aspif` (from gringo: `{a;b;c}. #minimize{1,a:a; 1,b:b}.`):
```
asp 1 0 0
1 1 3 1 2 3 0 0
2 0 2 2 1 1 1
4 1 a 1 1
4 1 b 1 2
4 1 c 1 3
0
```
Before: in about 2% of runs `OPTIMUM FOUND` with `Models : 1` and no `Optimal :` line, i.e. the optimal models are not enumerated (20/1000 runs).  
After: always `Optimal : 2` (0/1000 runs).

Only terminate if `requestWork()` found that there is no work at all. Found by differential fuzzing.
