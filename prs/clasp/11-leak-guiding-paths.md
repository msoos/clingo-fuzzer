# Fix leak of guiding paths left in the parallel work queue

Guiding paths split off for other threads are queued in `ParallelSolve::SharedData`, but the queue was only cleared at the start of a solve. Paths still queued when solving ended (e.g. split during the final model check) leak.

```
$ clasp -n0 --strengthen=recursive,short --sat-prepro=no -t4,split --sign-def=rnd --local-restarts --configuration=jumpy --score-other=all --restarts=L,5 --enum-mode=brave in.aspif
```
`in.aspif`:
```
asp 1 0 0
1 1 1 16 0 0
1 1 1 18 0 0
1 1 1 20 0 0
1 1 1 22 0 0
1 1 2 25 26 0 0
1 1 2 27 14 0 0
1 1 1 30 0 0
1 1 1 31 0 0
1 1 1 32 0 0
1 1 1 33 0 0
1 1 1 34 0 0
1 1 1 35 0 0
0
```
Before: with ASan, `LeakSanitizer: 52 byte(s) leaked` (`Solver::split()` from `ParallelHandler::handleSplitMessage()`) in about 3% of runs.  
After: no leak in 240 runs.

Clear the queue in the `SharedData` destructor. Found by differential fuzzing.
