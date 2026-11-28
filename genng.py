#!/usr/bin/env python3
# Random non-ground program plus its naive instantiation over the domain d/1. Usage: genng.py --seed N NG.lp GROUND.lp
import argparse
import itertools
import random

p = argparse.ArgumentParser()
p.add_argument("--seed", type=int, default=None)
p.add_argument("ng")
p.add_argument("ground")
a = p.parse_args()
rnd = random.Random(a.seed)

K = rnd.randint(1, 4)  # domain 0..K
DOM = list(range(K + 1))
preds = {f"p{i}": rnd.randint(0, 2) for i in range(rnd.randint(2, 6))}
UNARY = [q for q, ar in preds.items() if ar == 1]
NARY = [q for q, ar in preds.items() if ar >= 1]
VARS = ["X", "Y", "Z"]


class Term:
    """A variable, a constant, var+const / var*const, or a pool of constants; evaluated under a substitution."""
    def __init__(self, var=None, const=0, op=None, pool=None):
        self.var, self.const, self.op, self.pool = var, const, op, pool

    def show(self):
        if self.pool:  # parenthesized: a bare ';' would separate whole argument tuples
            return "(" + ";".join(map(str, self.pool)) + ")"
        if self.var is None:
            return str(self.const)
        if self.op is None:
            return self.var
        return f"{self.var}{self.op}{self.const}"

    def ev(self, s):
        if self.var is None:
            return self.const
        v = s[self.var]
        return v if self.op is None else v + self.const if self.op == "+" else v * self.const


def rterm(vs, arith):
    if vs and rnd.random() < 0.8:
        v = rnd.choice(vs)
        if arith and rnd.random() < 0.25:
            return Term(v, rnd.choice([1, 2]), rnd.choice(["+", "*"]))
        return Term(v)
    return Term(None, rnd.choice(DOM))


def ratom(vs, arith=False, pred=None):
    pred = pred or rnd.choice(list(preds))
    return pred, [rterm(vs, arith) for _ in range(preds[pred])]


def show_atom(at, s=None):
    pred, args = at
    if not args:
        return pred
    return f"{pred}({','.join(str(t.ev(s)) if s is not None else t.show() for t in args)})"


CMP = ["<", "<=", "!=", "=", ">"]


def cmp_ok(op, x, y):
    return {"<": x < y, "<=": x <= y, "!=": x != y, "=": x == y, ">": x > y}[op]


def gen_rule():
    """Returns (nonground text, variables, function substitution -> list of ground rule texts)."""
    nv = rnd.randint(0, 3)
    vs = VARS[:nv]
    pos = [("d", [Term(v)]) for v in vs]  # safety: every variable is bound by d/1
    extra = [ratom(vs) for _ in range(rnd.randint(0, 2))]
    neg = [ratom(vs) for _ in range(rnd.randint(0, 2))]
    cmps = [(rnd.choice(CMP), rterm(vs, True), rterm(vs, True)) for _ in range(rnd.randint(0, 2) if vs else 0)]
    # a positive body atom with a pool argument: one rule per alternative
    pool = None
    if NARY and rnd.random() < 0.2:
        q = rnd.choice(NARY)
        alts = sorted(rnd.sample(DOM, min(len(DOM), 2)))
        pool = (q, [Term(pool=alts)] + [rterm(vs, False) for _ in range(preds[q] - 1)], alts)
    # conditional literal [not] q(V) : d(V) with a local V
    condlit = None
    if UNARY and rnd.random() < 0.2:
        condlit = (rnd.random() < 0.4, rnd.choice(UNARY))
    agg = None
    if NARY and rnd.random() < 0.3:
        ap = rnd.choice(NARY)
        two = preds[ap] == 2 and rnd.random() < 0.4  # second local variable U
        args = [Term("W")] + ([Term("U")] if two else [rterm(vs, False) for _ in range(preds[ap] - 1)])
        fun = rnd.choice(["#count", "#sum", "#min", "#max"])
        agg = (fun, (ap, args), rnd.choice([">=", "<=", "!=", "="]), rnd.randint(-1, K + 2), rnd.random() < 0.25, two)
    kind = rnd.choice(["normal", "normal", "choice", "constraint", "condchoice", "disj", "interval"])
    head = ratom(vs, arith=True)

    def body_ng():
        parts = [show_atom(x) for x in pos + extra] + ["not " + show_atom(x) for x in neg]
        if pool:
            parts.append(show_atom(pool[:2]))
        if condlit:
            parts.append(f"{'not ' if condlit[0] else ''}{condlit[1]}(V) : d(V)")
        parts += [f"{l.show()}{op}{r.show()}" for op, l, r in cmps]
        if agg:
            fun, at, op, bound, naf, two = agg
            tup = ("W,W" if fun == "#sum" else "W") + (",U" if two else "")
            dom = "d(W), d(U)" if two else "d(W)"
            parts.append(f"{'not ' if naf else ''}{fun} {{ {tup} : {show_atom(at)}, {dom} }} {op} {bound}")
        return parts

    def bodies_g(s):
        for op, l, r in cmps:
            if not cmp_ok(op, l.ev(s), r.ev(s)):
                return []
        parts = [show_atom(x, s) for x in pos + extra] + ["not " + show_atom(x, s) for x in neg]
        if condlit:
            parts += [f"{'not ' if condlit[0] else ''}{condlit[1]}({v}) : d({v})" for v in DOM]
        if agg:
            fun, at, op, bound, naf, two = agg
            elems = []
            for w, u in itertools.product(DOM, DOM if two else [None]):
                tup = (f"{w},{w}" if fun == "#sum" else f"{w}") + (f",{u}" if two else "")
                elems.append(f"{tup} : {show_atom(at, dict(s, W=w, U=u))}")
            parts.append(f"{'not ' if naf else ''}{fun} {{ {'; '.join(elems)} }} {op} {bound}")
        if not pool:
            return [parts]
        q, args, alts = pool
        return [parts + [show_atom((q, [Term(None, c)] + args[1:]), s)] for c in alts]

    def text(h, b):
        return f"{h} :- {'; '.join(b)}." if b else f"{h}."

    if kind == "constraint":
        ng = ":- " + "; ".join(body_ng() or ["d(0)"]) + "."
        g = lambda s: [":- " + "; ".join(b or ["d(0)"]) + "." for b in bodies_g(s)]
    elif kind == "choice":
        ng = text("{ " + show_atom(head) + " }", body_ng())
        g = lambda s: [text("{ " + show_atom(head, s) + " }", b) for b in bodies_g(s)]
    elif kind == "condchoice" and NARY:
        hp = rnd.choice(NARY)
        hargs = [Term("V")] + [rterm(vs, False) for _ in range(preds[hp] - 1)]
        ng = text("{ " + show_atom((hp, hargs)) + " : d(V) }", body_ng())
        def g(s):
            elems = "; ".join(show_atom((hp, hargs), dict(s, V=v)) for v in DOM)
            return [text("{ " + elems + " }", b) for b in bodies_g(s)]
    elif kind == "disj":
        h2 = ratom(vs, arith=True)
        ng = text(show_atom(head) + " | " + show_atom(h2), body_ng())
        g = lambda s: [text(show_atom(head, s) + " | " + show_atom(h2, s), b) for b in bodies_g(s)]
    elif kind == "interval" and UNARY and vs:
        hp, v, c = rnd.choice(UNARY), rnd.choice(vs), rnd.randint(0, 2)
        ng = text(f"{hp}({v}..{v}+{c})", body_ng())
        g = lambda s: [text(f"{hp}({x})", b) for x in range(s[v], s[v] + c + 1) for b in bodies_g(s)]
    else:
        ng = text(show_atom(head), body_ng())
        g = lambda s: [text(show_atom(head, s), b) for b in bodies_g(s)]
    return ng, vs, g


ng_lines = [f"d(0..{K})."]
g_lines = [f"d({i})." for i in DOM]
for _ in range(rnd.randint(2, 14)):
    ng, vs, g = gen_rule()
    ng_lines.append(ng)
    for vals in itertools.product(DOM, repeat=len(vs)):
        g_lines += g(dict(zip(vs, vals)))
if NARY and rnd.random() < 0.3:  # optimization over non-ground statements
    for _ in range(rnd.randint(1, 2)):
        q, prio, off = rnd.choice(NARY), rnd.randint(0, 1), rnd.choice([0, -1])
        if preds[q] == 1:
            ng_lines.append(f"#minimize {{ W{off:+d}@{prio},W : {q}(W), d(W) }}.")
            g_lines.append("#minimize { " + "; ".join(f"{w + off}@{prio},{w} : {q}({w})" for w in DOM) + " }.")
        else:
            ng_lines.append(f"#minimize {{ W+U{off:+d}@{prio},W,U : {q}(W,U), d(W), d(U) }}.")
            g_lines.append("#minimize { " + "; ".join(f"{w + u + off}@{prio},{w},{u} : {q}({w},{u})"
                                                    for w in DOM for u in DOM) + " }.")
shows = ["#show."] + [f"#show {q}/{ar}." for q, ar in preds.items()]
open(a.ng, "w").write("\n".join(ng_lines + shows) + "\n")
open(a.ground, "w").write("\n".join(g_lines + shows) + "\n")
