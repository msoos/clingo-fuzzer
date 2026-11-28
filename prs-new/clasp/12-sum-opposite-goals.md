# Fix lost answer sets from merging opposite subgoals of sum bodies

When a positive and a negative subgoal of a count/sum body map to the same solver literal (here `q` and `not t`, with `t :- not q`), `PrgBody::simplifyBody()` merges the second into the first by adding its weight. Positive goals come first, so the body then depends positively on `q` with the combined weight. The external support from `not t` is lost, and a founded answer set is treated as unfounded. Merging the other way would over-approximate the support.

```
$ clasp -n0 --no-lookback in.aspif
```
`in.aspif` (from gringo: `s :- 2 #sum{2: not t; 1: q}. q :- s. q :- not u. t :- not q. {u}.`):
```
asp 1 0 0
1 1 1 1 0 0
1 0 1 2 0 1 -1
1 0 1 3 0 1 -2
1 0 1 5 0 1 4
1 0 1 2 0 1 5
1 0 1 6 1 2 2 -3 2 2 1
1 0 1 4 0 1 6
4 1 t 1 3
4 1 q 1 2
4 1 s 1 5
4 1 u 1 1
0
```
Before: `Models : 2`; the answer set {s, q, u} is missing (without `--no-lookback`, or with `--eq=0`: 3).  
After: `Models : 3`.

Keep such subgoals apart; the solver's weight constraint merges the literal anyway. Found by differential fuzzing (reify pipeline).
