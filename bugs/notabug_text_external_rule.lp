% not a bug: clingo -n0 gives {x0}; clingo --text | clingo -n0 also gives {x0,x2}
x6| x0.
#external x2. [free]
x0.
x2 :- x6.
