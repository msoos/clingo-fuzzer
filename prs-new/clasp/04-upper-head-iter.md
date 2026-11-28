# Fix invalid head iterator in addHeadsToUpper()

Adding a head to the upper closure propagates, and a disjunction that shrinks to one atom then adds that atom as a head of its supports. If one of them is the body whose heads `Preprocessor::addHeadsToUpper()` is iterating, and that body had two (inline) heads, `PrgBody::addHead()` moves them to a heap vector. That overwrites the inline storage the iterator points to, so the next head read is garbage.

```
$ clasp --backprop in.aspif
```
`in.aspif`:
```
asp 1 0 0
1 0 1 28 0 1 -26
1 0 0 0 2 -28 26
1 0 1 73 0 1 -26
1 1 1 26 0 1 -73
1 0 2 26 81 0 1 -84
1 0 1 111 0 1 -26
1 0 1 109 0 1 -111
1 0 1 212 0 1 26
1 0 0 0 2 213 -215
1 0 1 216 0 1 -212
1 0 2 211 213 0 1 -216
0
```
Before: ``Assertion `n < size()' failed`` in `pod_vector::operator[]` (from `LogicProgram::getAtom()` in `addHeadsToUpper()`; other inputs fail in `getDisj()`).  
After: `SATISFIABLE` (1 answer set with `-n0`, as with `--eq=0 --no-backprop`).

Iterate over the heads by index. Found by differential fuzzing.
