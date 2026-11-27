# Fix assertion when computing a core without learning

Without learning, reasons are not recorded, so `resolveToCore()` adds all decisions to the core. It nevertheless resolved the conflict's literals, asking e.g. the unfounded set checker, which records no reasons in this mode, for a reason. Happens when an assumption (here an external) makes the program unsatisfiable.

```
$ clasp -n0 --opt-mode=optN --no-lookback in.aspif
```
`in.aspif`:
```
asp 1 0 0
1 1 1 2 0 0
5 3 2
1 1 1 6 0 2 4 7
1 0 1 8 0 1 9
1 0 1 10 0 1 6
1 0 1 10 0 1 12
1 0 1 16 0 1 10
1 0 1 15 0 1 16
1 0 1 6 0 1 17
1 0 1 17 0 1 6
1 0 2 15 17 0 0
1 0 1 4 0 1 15
1 1 1 7 0 1 8
1 0 1 19 0 1 -7
1 0 0 0 2 8 -19
1 0 1 21 0 1 5
1 0 1 20 0 1 21
1 0 1 20 0 1 -5
1 0 1 22 0 1 -21
1 0 2 20 5 0 1 -22
1 0 1 9 0 1 20
1 0 1 5 0 1 25
1 0 1 10 0 1 25
1 0 1 25 0 2 5 10
1 0 1 23 0 0
1 0 1 11 0 0
1 0 1 28 0 1 3
1 0 1 27 0 1 -10
1 0 1 29 0 1 -28
1 0 1 27 0 1 -29
1 0 1 12 0 1 27
0
```
Before: ``Assertion `strategy_ == only_reason && reasons_' failed`` in `DefaultUnfoundedCheck::reason()`.  
After: `UNSATISFIABLE`.

Return all decisions as the core directly; resolution can't add anything to that. Found by differential fuzzing.
