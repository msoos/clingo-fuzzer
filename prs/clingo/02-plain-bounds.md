# Fix plain bounds of aggregates with bounds outside the range

`AggregateAtomRange::plainBounds()` treated bound intervals lying completely outside the aggregate's range as the other side of a `!=` bound. With `--text`, this printed wrong bounds or failed an assertion.

```
$ clingo --text in.lp
```
`in.lp`:
```
{b;c;d}. ok :- -3 != #sum{1,b:b;1,c:c;1,d:d} != 2.
```
Before: `ok:--3>#sum{1,b:b;1,c:c;1,d:d}!=2.`, which never holds (`ok` is in 5 answer sets when solving directly, in none via the text output).  
After: `ok:-2!=#sum{1,b:b;1,c:c;1,d:d}.`

Same command, assertion cases:
```
{b}. :- 1 != #sum{1 : b} != 2.
```
```
7 { } != x0.
```
Before: ``Assertion `cBounds.back().first == Relation::LT || cBounds.back().first == Relation::LEQ' failed`` in `plainBounds()`.  
After: `:-1!=#sum{1:b}.` and `7<=#count{}` (the second one: all intervals are outside the range, so the aggregate is false; one such bound says so).

Skip intervals that don't intersect the range, unless all of them are outside it; then emit only the first one. Found by differential fuzzing.
