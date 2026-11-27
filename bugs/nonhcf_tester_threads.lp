% clingo -n0 --sign-def=neg --partial-check=100 --del-max=10,0 --no-backprop --shuffle=1,1 --configuration=handy -t4,split --otfs=1
x0 ; -x0 :- x0 : x1.
#count { 3 : x0; 3 : x1 : x0; 3 : x1 } <= -3 :- x1 : not x0, x0; not x0.
:- x1 : x0; not x1; x0 : x1, not x0; 0 >= #count { 3 : not x1; 4 : not x0, not x1; 4 : x1; 0 : not x0 } != -3.
x1.
x0 :- not x0; x1 : x0; not x1.
x1 :- -3 = #count { 1 : x0; 0 : x0, x1 }; #sum { 1,0 : x0; -1,2 : x0, x1 } >= 0.
x0 :- x0 : -x1, x0; x0 : x0, x0.
