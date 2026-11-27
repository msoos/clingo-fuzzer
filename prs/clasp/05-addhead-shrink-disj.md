# Fix assertion when a disjunction shrinks to one atom

When all but one atom of a disjunction become false, `PrgDisj::propagateAssigned()` adds the remaining atom as a head of the disjunction's supports. A support may already be equivalent to another body, or removed, and the atom may have been merged into an equivalent atom.

```
$ clasp --backprop in.aspif
```
`in.aspif` (from gringo: `x7 | x5 :- not x7. x5; x4. x4; x7 : x7 :- not x7.`):
```
asp 1 0 0
1 0 1 1 0 1 -2
1 0 2 2 3 0 1 -2
1 0 2 3 4 0 0
1 0 1 5 0 2 2 2
1 0 1 2 0 2 2 5
1 0 0 0 2 -2 5
1 0 2 4 5 0 1 1
4 2 x7 1 2
4 2 x5 1 3
4 2 x4 1 4
0
```
Before: ``Assertion `relevant() && h->relevant()' failed`` in `PrgBody::addHead()`.  
After: `SATISFIABLE`.

Removed support, same command:
```
asp 1 0 0
1 0 1 11 0 1 12
1 0 0 0 2 -19 17
1 0 2 20 17 0 1 11
1 0 1 23 0 1 -24
1 0 1 22 0 1 -21
1 0 1 12 0 1 22
0
```
Before: same assertion. After: `SATISFIABLE`.

Merged atom, same command:
```
asp 1 0 0
1 1 1 4 0 0
1 0 1 5 0 0
1 0 1 6 0 1 -7
1 0 1 7 0 1 -4
1 0 1 8 0 1 7
1 0 1 10 0 1 -4
1 0 0 0 2 12 -7
1 0 1 18 0 1 -19
1 0 1 21 0 1 -10
1 0 0 0 2 -21 20
1 0 2 10 20 0 1 -18
1 0 1 22 0 0
1 1 1 19 0 0
1 0 1 28 0 0
1 0 1 9 0 0
1 0 0 0 1 11
1 0 1 12 0 0
0
```
Before: same assertion. After: `SATISFIABLE`.

Add the root atom as head of the root body of the support, and skip supports that were removed. Found by differential fuzzing.
