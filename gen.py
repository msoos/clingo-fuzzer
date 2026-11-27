#!/usr/bin/env python3
# Random ground ASP program generator in gringo 5 syntax, after FuzzASP. Usage: gen.py --seed N [opts] > prog.lp
# One statement per line, so minim.py can delta-debug by line.

import argparse
import random

p = argparse.ArgumentParser()
p.add_argument("--seed", type=int, default=None)
p.add_argument("--size", choices=["small", "normal", "big"], default="normal")
p.add_argument("--opt", action="store_true", help="add #minimize / weak constraints")
p.add_argument("--proj", action="store_true", help="#project the same atoms as #show")
p.add_argument("--reifiable", action="store_true", help="only what the meta encodings handle")
p.add_argument("--neg", action="store_true", help="use classical negation")
a = p.parse_args()
rnd = random.Random(a.seed)

lo, hi = {"small": (2, 8), "normal": (4, 25), "big": (15, 80)}[a.size]
natoms = rnd.randint(lo, hi)
nrules = rnd.randint(natoms // 2 + 1, int(natoms * 2.2) + 2)

w = {k: rnd.randint(0, 10) for k in
     ["normal", "constraint", "disj", "choice", "headagg", "fact", "condhead"]}
w["normal"] += 3
w["choice"] += 2
w["constraint"] //= 3
p_not = rnd.choice([0, 20, 40, 60])
p_notnot = rnd.choice([0, 0, 5, 15])
p_neg = rnd.choice([0, 10, 30]) if a.neg else 0
p_agg = rnd.choice([0, 0, 10, 25, 50])
p_cond = rnd.choice([0, 10, 30])
maxbody = rnd.randint(1, 5)
maxhead = rnd.randint(2, 5)
maxwt = rnd.choice([1, 3, 10, 1000])
neg_wt = rnd.choice([False, True])


def atom(i=None):
    if i is None:
        i = rnd.randrange(natoms)
    s = f"x{i}"
    if rnd.randint(1, 100) <= p_neg:
        s = "-" + s
    return s


def lit():
    s = atom()
    r = rnd.randint(1, 100)
    if r <= p_notnot:
        return "not not " + s
    if r <= p_notnot + p_not:
        return "not " + s
    return s


def weight():
    return rnd.randint(-maxwt if neg_wt else 0, maxwt)


def cond(maxlen=2):
    return ", ".join(lit() for _ in range(rnd.randint(1, maxlen)))


def guards(wmin, wmax):
    rel = ["<", "<=", ">", ">=", "=", "!="]
    left = right = ""
    if rnd.random() < 0.7:
        left = f"{rnd.randint(wmin - 1, wmax + 1)} {rnd.choice(rel)} "
    if not left or rnd.random() < 0.3:
        right = f" {rnd.choice(rel)} {rnd.randint(wmin - 1, wmax + 1)}"
    return left, right


def body_agg():
    n = rnd.randint(1, 5)
    fun = rnd.choice(["#count", "#sum", "#sum+", "#min", "#max", "set"])
    if fun == "set":
        left, right = guards(0, n)
        return left + "{ " + "; ".join(head_elem(50, lit()) for _ in range(n)) + " }" + right
    elems = []
    for _ in range(n):
        tid = rnd.randint(0, n)  # tuple collisions on purpose
        t = f"{tid}" if fun == "#count" else f"{weight()},{tid}"
        elems.append(f"{t} : {cond(2)}")
    span = n * maxwt
    left, right = guards(-span if neg_wt else 0, span)
    return left + fun + " { " + "; ".join(elems) + " }" + right


def body(minlen=0):
    parts = []
    for _ in range(rnd.randint(minlen, maxbody)):
        r = rnd.randint(1, 100)
        if r <= p_agg:
            parts.append(body_agg())
        elif r <= p_agg + p_cond:
            parts.append(f"{atom()} : {cond(2)}")
        else:
            parts.append(lit())
    return parts


def rule(head, minbody=0):
    b = body(minbody)
    if not b:
        return head + "."
    return f"{head} :- " + "; ".join(b) + "."


def head_elem(c, e=None):
    e = e or atom()
    if rnd.randint(1, 100) <= c:
        return f"{e} : {cond(2)}"
    return e


def gen_rule(kind):
    if kind == "fact":
        return atom() + "."
    if kind == "normal":
        return rule(atom(), 1)
    if kind == "constraint":
        return ":- " + "; ".join(body(1)) + "."
    if kind in ("disj", "condhead"):
        c = 40 if kind == "condhead" else 0
        h = rnd.choice([" ; ", " | "]).join(head_elem(c) for _ in range(rnd.randint(2, maxhead)))
        return rule(h)
    if kind == "choice":
        n = rnd.randint(1, maxhead)
        h = "{ " + "; ".join(head_elem(p_cond) for _ in range(n)) + " }"
        if rnd.random() < 0.4:
            left, right = guards(0, n)
            h = left + h + right
        return rule(h)
    if kind == "headagg":
        n = rnd.randint(1, maxhead)
        fun = rnd.choice(["#count", "#sum"])
        elems = []
        for _ in range(n):
            tid = rnd.randint(0, n)
            t = f"{tid}" if fun == "#count" else f"{weight()},{tid}"
            e = f"{t} : {atom()}"
            if rnd.randint(1, 100) <= p_cond:
                e += f" : {cond(2)}"
            elems.append(e)
        span = n * maxwt
        left, right = guards(-span if neg_wt else 0, span)
        return rule(left + fun + " { " + "; ".join(elems) + " }" + right)
    raise ValueError(kind)


out = []
kinds = list(w)
weights = [w[k] for k in kinds]
for i in range(natoms):
    if rnd.random() < 0.7:
        out.append(rule(atom(i)) if rnd.random() < 0.8 else "{ " + atom(i) + " }.")
for _ in range(nrules):
    out.append(gen_rule(rnd.choices(kinds, weights)[0]))

if a.opt:
    for _ in range(rnd.randint(1, 6)):
        prio = rnd.randint(0, 2)
        if rnd.random() < 0.5:
            elems = "; ".join(f"{weight()}@{prio},{rnd.randint(0, 3)} : {cond(2)}"
                              for _ in range(rnd.randint(1, 4)))
            out.append(rnd.choice(["#minimize", "#maximize"]) + " { " + elems + " }.")
        else:
            out.append(f":~ {cond(3)}. [{weight()}@{prio},{rnd.randint(0, 3)}]")

if not a.reifiable:
    # conflicting duplicate externals have no defined order
    for i in rnd.sample(range(natoms), min(natoms, rnd.choice([0, 0, 1, 3]))):
        out.append(f"#external x{i}." +
                   rnd.choice(["", " [true]", " [false]", " [free]"]))
    for _ in range(rnd.choice([0, 0, 2, 6])):
        mod = rnd.choice(["level", "sign", "true", "false", "init", "factor"])
        out.append(f"#heuristic x{rnd.randrange(natoms)} : {cond(2)}. "
                   f"[{rnd.randint(-3, 5)}@{rnd.randint(0, 2)},{mod}]")
    if rnd.random() < 0.15:
        nodes = rnd.randint(2, 5)
        for _ in range(rnd.randint(1, 8)):
            out.append(f"#edge ({rnd.randrange(nodes)},{rnd.randrange(nodes)}) : {cond(2)}.")

if a.proj or rnd.random() < 0.5:
    shown = sorted(rnd.sample(range(natoms), rnd.randint(0, natoms)))
    out.append("#show.")
    for i in shown:
        out.append(f"#show x{i}/0.")
        if a.proj:
            out.append(f"#project x{i}/0.")
    if not a.proj and rnd.random() < 0.3:
        for j in range(rnd.randint(1, 3)):
            out.append(f"#show s({j}) : {cond(2)}.")

rnd.shuffle(out)
print("\n".join(out))
