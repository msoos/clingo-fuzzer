# Fix assertion when a shrinking disjunction has an eq or removed support

When all but one atom of a disjunction become false, `PrgDisj::propagateAssigned()` adds the remaining atom as a head of the disjunction's supports. A support may already be equivalent to another body, or removed.

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
Before: same assertion. After: `UNSATISFIABLE`.

Add the head to the root body of the support, and skip supports that were removed. Found by differential fuzzing.
