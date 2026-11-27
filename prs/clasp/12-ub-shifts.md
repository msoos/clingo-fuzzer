# Fix undefined shifts in lazy VMTF and Berkmin score decay

Both heuristics decay scores lazily by shifting right by the number of missed decay steps (VMTF: twice that), which can exceed the width of the type: Berkmin's decay counter goes up to 65534. The Berkmin code comment assumed the shift just wraps around (modulo 32), but in C++ that is undefined behaviour, as is `1 << 31` on an `int`.

```
$ clasp -n0 --heuristic=vmtf in.aspif
```
`in.aspif`:
```
asp 1 0 0
1 1 1 16 0 0
1 1 1 18 0 0
1 1 1 20 0 0
1 1 1 22 0 0
1 1 2 25 26 0 0
1 1 2 27 14 0 0
1 1 1 30 0 0
1 1 1 31 0 0
1 1 1 32 0 0
1 1 1 33 0 0
1 1 1 34 0 0
1 1 1 35 0 0
0
```
Before: with UBSan, `heuristics.h:202: runtime error: shift exponent 48 is too large for 32-bit type 'unsigned int'`.  
After: no runtime error.

The Berkmin case was found by inspection.

Use the intended results instead: scores become 0 once the shift reaches the width (16 bits for Berkmin's activity, 32 for VMTF; 31 for the divisor of Berkmin's occurrence counter). Found by differential fuzzing.
