# Fix unfounded answer sets from merging duplicate body literals

If a normal body contains a negative and a positive goal that map to the same solver literal (here after replacing an eq atom by its eq goal `not 8`, where 8 is equivalent to `not 5`), `PrgBody::simplifyBody()` dropped the positive goal as a duplicate. That removed the positive dependency, so atoms that only support each other in a loop were no longer unfounded.

```
$ clasp -n0 in.aspif
```
`in.aspif`:
```
asp 1 0 0
1 1 1 1 0 0
1 0 1 2 0 1 -4
1 0 1 5 0 2 2 -1
1 0 1 7 0 2 6 5
1 1 1 5 0 1 7
1 0 1 8 0 1 -5
1 0 1 6 0 1 -8
4 2 x2 1 5
4 2 x4 1 1
0
```
Before: 3 answer sets, one of them with the unfounded loop 5, 7.  
After: 2 answer sets.

Keep the positive goal instead (dropping the negative one is safe: it is implied in every answer set). Found by differential fuzzing.
