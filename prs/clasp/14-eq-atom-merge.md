# Fix unfounded answer sets after merging atoms with equal literals

Eq-preprocessing merges atoms with the same solver literal. They then have the same truth value, but not the same supports. The merge nevertheless passed on to the root that the merged atom cannot become unfounded (`ignoreScc`) and its foundedness (`value_true`), and later values derived for the merged atom from its own supports were assigned to the root, too. The root was then treated as founded and removed from positive bodies, breaking a positive loop through it.

```
$ clasp -n0 --eq=2 in.aspif
```
`in.aspif`:
```
asp 1 0 0
1 0 1 4 0 0
1 1 1 6 0 0
1 0 0 0 1 8
1 0 1 9 0 1 10
1 1 2 14 10 0 0
1 0 1 15 0 2 9 6
1 0 1 9 0 1 15
1 0 0 0 1 7
1 0 1 14 0 0
1 0 1 20 0 1 -9
1 0 1 19 0 1 -20
1 0 0 0 1 -19
1 0 1 21 0 1 -18
1 0 1 19 0 1 -21
1 0 0 0 1 17
0
```
Before: 3 answer sets.  
After: 2 answer sets (also what `--eq=0` gives).

Pass on only weak truth (`value_weak_true`) to the root, and don't pass on `ignoreScc`. Found by differential fuzzing.
