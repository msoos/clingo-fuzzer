# Fix out-of-bounds tester solver access for inconsistent non-hcf testers

If the tester of a non-hcf component is inconsistent from the start, `SharedContext::endInit()` does not attach the solvers for the other threads. A minimality test from another thread then accessed a non-existing tester solver.

```
$ clasp -n0 --sign-def=neg --partial-check=100 --del-max=10,0 --no-backprop --shuffle=1,1 --configuration=handy -t4,split --otfs=1 in.aspif
```
`in.aspif`:
```
asp 1 0 0
1 0 0 0 1 -4
1 0 1 4 0 1 5
1 0 0 0 1 2
1 0 1 3 0 0
1 0 1 10 0 1 4
1 0 1 9 0 1 10
1 0 2 9 4 0 0
1 0 1 5 0 1 9
1 0 1 6 0 0
0
```
Before: ``Assertion `n < size()' failed`` in `pod_vector::operator[]` (from `NonHcfComponent::test()`).  
After: `SATISFIABLE`.

An inconsistent tester has no counterexample, so `test()` succeeds (and `simplify()` does nothing) if the solver is missing. Found by differential fuzzing.
