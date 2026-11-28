# Fix assertion when a transformed rule simplifies to an integrity constraint

When `LogicProgram::prepareComponents()` transforms recursive aggregate rules (e.g. `--trans-ext=scc`), a resulting rule can simplify to an integrity constraint. Here eq-preprocessing makes atoms 15-18 equivalent, and the transformation of `18 :- 3 <= #count{not 13; not 16; 11; 17}` yields `18 :- not 18`. `DlpTr::addRule()` assumed a head and accessed the empty head.

```
$ clasp --trans-ext=scc in.aspif
```
`in.aspif`:
```
asp 1 0 0
1 0 1 11 0 0
1 0 1 16 0 1 15
1 0 1 17 0 1 16
1 0 1 18 1 3 4 -13 1 -16 1 11 1 17 1
1 0 1 15 0 1 18
0
```
Before: ``Assertion `pos < size' failed`` in `Potassco::Span::operator[]` (from `LogicProgram::DlpTr::addRule()`).  
After: `UNSATISFIABLE` (as without `--trans-ext=scc`).

Add such rules as integrity constraints. Found by differential fuzzing.
