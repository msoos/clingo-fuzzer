# Fix assertion in min/max translation with an empty excluded gap

`translateMinMax()` asserted that some element lies in each excluded gap of the aggregate's bounds. That doesn't hold if no element can take a value in the gap; then the bound is trivially satisfied.

```
$ clingo in.lp
```
`in.lp`:
```
{a}.
:- 1 != #max{3,2 : not b, a; 2,1 : a}.
```
Before: ``Assertion `!antecedent.empty()' failed`` in `translateMinMax()`.  
After: `UNSATISFIABLE`.

Skip such bounds. Found by differential fuzzing.
