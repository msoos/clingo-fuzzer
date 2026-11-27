{ x0 }.
x3 :- x5 : x6; x0 : x4; x3; 0 >= #sum+ { 0,3 : x6, x4; 0,1 : x0; 0,0 : x6 }.
x5 :- #sum { 1,0 : x4, not not x6 } > 2.
x6 :- -1 > #min { 0,3 : x2, x6; 1,0 : x1; 1,0 : x2, x3; 0,1 : x3 }; x0; x3 : x4.
#minimize { 0@2,3 : x3; 1@2,3 : not not x6, x1; 1@2,3 : x0 }.
:~ x1, x2. [1@1,0]
{ x6; x5 : x5, x4 } :- -1 != #count { 0 : x6, x3 }; x3; 5 <= #min { 1,0 : x1, x2; 0,0 : x0; 0,0 : x3; 0,4 : x5 }; x2 : x0, x5.
x1.
x5 ; x3 ; x3 ; x1 ; x1.
x1.
x3 | x6 | x5 :- x5; x4; x6.
x3 :- #max { 1,2 : x1; 1,1 : x4 } > 2; x5 : x2, x3; 2 > #sum { 0,2 : x5, x0; 1,1 : x2 } > 3.
#external x4. [false]
x6 :- x6.
x2 :- x4 : x2; x1; x1; x3 : x2, x6.
x2 :- x5.
#external x6. [free]
1 != { x3; x2 } :- x3 : x1, x0; x5 : x1; x6 : x6.
#external x3. [true]
:~ x2, x2. [0@2,2]
{ x1 : x1, x0; x5 : x1, x3; x1; x6 }.
