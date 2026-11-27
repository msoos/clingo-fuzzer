% clingo -n0 --opt-mode=optN --no-lookback
{ x0 }.
:- x5 : x6; x3.
{ x6; x5 } :- x3; x2 : x0, x5.
x3; x1.
x1.
#external x4. [false]
x2 :- x4 : x2; x3 : x2, x6.
x2 :- x5.
1 != { x3 } :- x6 : x6.
