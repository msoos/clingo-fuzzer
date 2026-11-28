# Fix assertion when transforming a rule whose body was merged into another one

`LogicProgram::findBody()` also returns bodies that eq-preprocessing merged into a relevant root body. When rules are transformed after preprocessing (here `--trans-ext=choice` for a recursive choice rule), `assignBodyFor()` then adds the head to the merged body instead of its root.

```
$ clasp --trans-ext=choice in.aspif
```
`in.aspif`:
```
asp 1 0 0
1 1 1 8 0 0
1 0 1 10 0 2 6 7
1 0 1 12 0 1 10
1 0 1 15 0 1 12
1 0 1 17 0 1 15
1 0 2 21 7 0 1 22
1 0 1 6 0 1 30
1 0 1 22 0 1 17
1 0 1 56 0 1 21
1 0 1 57 1 1 2 8 10 56 7
1 0 1 30 0 1 57
1 0 1 60 0 1 8
1 0 1 61 0 1 -60
1 0 1 12 0 1 -61
0
```
Before: ``Assertion `relevant() && h->relevant()' failed`` in `PrgBody::addHead()` (from `LogicProgram::DlpTr::addRule()` in `prepareComponents()`).  
After: `SATISFIABLE` (3 answer sets with `-n0`, as with `--eq=0`).

Use the root body in `assignBodyFor()`. Found by differential fuzzing.
