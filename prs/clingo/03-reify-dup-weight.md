# Fix reified weighted literal tuples with duplicate literals

A weight body or minimize statement may contain the same literal more than once (here gringo reuses an always-true literal for the fact `c`). The reifier printed one `weighted_literal_tuple` fact per occurrence, and identical facts collapse, so weight was lost.

```
$ clingo --output=reify in.lp | clingo - examples/reify/common/meta.lp -n0
```
`in.lp`:
```
:- { a; not b; c } > 2.
c.
{a}.
```
Before: answer sets `{c}` and `{a,c}`; `{a,c}` violates the constraint.  
After: `{c}` (as `clingo -n0 in.lp`).

Sum the weights of duplicate literals in `Reifier::weightLitTuple()`. Found by differential fuzzing.
