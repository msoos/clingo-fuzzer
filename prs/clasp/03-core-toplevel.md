# Fix assertion in resolveToCore() with top-level conflict literals

When the program is unsatisfiable under assumptions (here the external `a`, assumed false), the core is computed with `resolveToCore()`, which also tried to resolve literals assigned on level 0.

```
$ clasp --eq=0 in.aspif
```
`in.aspif` (from gringo: `#external a. b :- c. c :- not b.`):
```
asp 1 0 0
1 0 1 1 0 1 -2
1 0 1 2 0 1 1
5 3 2
4 1 a 1 3
4 1 c 1 1
4 1 b 1 2
0
```
Before: ``Assertion `dl' failed`` in `Solver::resolveToCore()`.  
After: `UNSATISFIABLE`.

Skip top-level literals in `resolveToCore()`; they don't depend on any assumption. Found by differential fuzzing.
