#!/usr/bin/env python3
# Differential fuzzer for clasp on DIMACS CNF, WCNF (MaxSAT) and OPB: random options vs. --sat-prepro=no.
# Usage: ./satfuzz.py [--only N] [--keep-going] | ./satfuzz.py --check FILE --cand="OPTS"
import argparse
import collections
import json
import os
import random
import shlex
import sys

import fuzz
from fuzz import Bug, Skip, cmd_str, run, GREEN, RED, NC

HERE = os.path.dirname(os.path.realpath(__file__))
REF = ["--sat-prepro=no"]
ASP_ONLY = ("--eq", "--backprop", "--no-backprop", "--trans-ext", "--no-gamma", "--dlp-old-map", "--loops",
            "--partial-check", "--dom-mod", "--keep-facts", "--preserve-facts", "--heuristic=domain", "--lookahead=body",
            "--lookahead=hybrid", "--opt-heuristic")


def gen_cnf(rng, weighted):
    n = rng.randint(2, 16)
    m = rng.randint(1, 4 * n)
    lines = []
    for _ in range(m):
        k = rng.choice([1, 2, 2, 3, 3, 3, 4, 5])
        lits = [rng.randint(1, n) * rng.choice([1, -1]) for _ in range(k)]
        if rng.random() < 0.03:
            lits = []  # empty clause
        elif rng.random() < 0.05:
            lits.append(lits[0])  # duplicate literal
        elif rng.random() < 0.03:
            lits.append(-lits[0])  # tautology
        lines.append(lits)
    if not weighted:
        return f"p cnf {n} {m}\n" + "".join(" ".join(map(str, c + [0])) + "\n" for c in lines)
    top = 1000
    out = [f"p wcnf {n} {m} {top}"]
    for c in lines:
        w = top if rng.random() < 0.5 else rng.randint(1, 9)
        out.append(" ".join(map(str, [w] + c + [0])))
    return "\n".join(out) + "\n"


def gen_opb(rng, objective):
    return gen_opb_sized(rng, rng.randint(2, 12), objective)


def gen_opb_sized(rng, n, objective):
    m = rng.randint(1, 2 * n)
    term = lambda: f"{rng.choice([1, 1, 2, 3, -1, -2, 5])} {'~' if rng.random() < 0.2 else ''}x{rng.randint(1, n)}"
    out = [f"* #variable= {n} #constraint= {m}"]
    if objective:
        out.append("min: " + " ".join(f"+{rng.randint(-3, 5)} x{v}".replace("+-", "-") for v in rng.sample(range(1, n + 1), rng.randint(1, n))) + " ;")
    for _ in range(m):
        terms = [term() for _ in range(rng.randint(1, 4))]
        terms = [t if t.startswith("-") else "+" + t for t in terms]
        out.append(" ".join(terms) + f" {rng.choice(['>=', '>=', '='])} {rng.randint(-2, 4)} ;")
    return "\n".join(out) + "\n"


def gen_big(rng, opb):
    """Larger instances (marked by a 'big' comment): only the result/optimum is compared, not all models."""
    if not opb:
        n = rng.randint(30, 120)
        cl = [[v * rng.choice([1, -1]) for v in rng.sample(range(1, n + 1), 3)] for _ in range(int(n * rng.uniform(3.8, 4.6)))]
        return f"c big\np cnf {n} {len(cl)}\n" + "".join(" ".join(map(str, c + [0])) + "\n" for c in cl)
    hdr, rest = gen_opb_sized(rng, rng.randint(15, 35), True).split("\n", 1)
    return hdr + "\n* big\n" + rest  # the OPB header must come first


def run_one(binary, opts, path):
    cmd = [binary, "--outf=2", *opts, path]
    js = json.loads(run(cmd) or "{}")
    if js.get("Result") == "UNKNOWN":
        raise Skip("unfinished: " + cmd_str(cmd))
    wits = [w for c in js.get("Call", []) for w in c.get("Witnesses", []) if "Value" in w]
    return cmd, js["Result"], wits


def check_big(path, copts, binary):
    if path.endswith(".opb"):
        rcmd, rres, rw = run_one(options.clasp, REF + ["-n0", "--opt-mode=opt"], path)
        cmd, cres, cw = run_one(binary, copts + ["-n0", "--opt-mode=opt"], path)
        rbest = rw[-1].get("Costs") if rw else None
        cbest = cw[-1].get("Costs") if cw else None
        if (rres == "UNSATISFIABLE") != (cres == "UNSATISFIABLE") or rbest != cbest:
            raise Bug(f"{cres} {cbest} vs {rres} {rbest} (ref)\n--> failing: {cmd_str(cmd)}\n--> reference: {cmd_str(rcmd)}")
        return
    rcmd, rres, _ = run_one(options.clasp, REF + ["-n1"], path)
    cmd, cres, cw = run_one(binary, copts + ["-n1"], path)
    if rres != cres:
        raise Bug(f"{cres} vs {rres} (ref)\n--> failing: {cmd_str(cmd)}\n--> reference: {cmd_str(rcmd)}")
    if cw:  # the reference must accept the candidate's model
        tmp = path + ".model.cnf"
        lines = open(path).read().splitlines()
        hdr = next(i for i, l in enumerate(lines) if l.startswith("p "))
        n, m = lines[hdr].split()[2:4]
        units = [f"{l} 0" for l in cw[0]["Value"]]
        with open(tmp, "w") as f:
            f.write("\n".join(lines[:hdr] + [f"p cnf {n} {int(m) + len(units)}"] + lines[hdr + 1:] + units) + "\n")
        try:
            vcmd, vres, _ = run_one(options.clasp, REF + ["-n1"], tmp)
            if vres != "SATISFIABLE":
                raise Bug(f"model of the candidate is not a model ({vres})\n--> failing: {cmd_str(cmd)}\n--> check: {cmd_str(vcmd)}")
        finally:
            if not options.keep:
                os.unlink(tmp)


def solve(binary, opts, path, opt):
    cmd = [binary, "--outf=2", "-n0", *(["--opt-mode=optN"] if opt else []), *opts, path]
    js = json.loads(run(cmd) or "{}")
    if js.get("Result") == "UNKNOWN" or js.get("Models", {}).get("More", "no") != "no":
        raise Skip("unfinished: " + cmd_str(cmd))
    wits = [(frozenset(w["Value"]), tuple(w.get("Costs", []))) for c in js.get("Call", []) for w in c.get("Witnesses", [])
            if "Value" in w]
    if opt and wits:
        best = min(co for _, co in wits)
        # without preprocessing, an objective whose soft clauses all hold at the top level is dropped (no costs)
        return cmd, collections.Counter(m for m, co in wits if co == best), tuple(x for x in best if x)
    return cmd, collections.Counter(m for m, _ in wits), None


def check(path, copts, binary, opt):
    rcmd, ref, rbest = solve(options.clasp, REF, path, opt)
    cmd, cand, cbest = solve(binary, copts, path, opt)
    if opt and ref and cand and rbest != cbest:
        raise Bug(f"optimum {cbest} vs {rbest} (ref)\n--> failing: {cmd_str(cmd)}\n--> reference: {cmd_str(rcmd)}")
    if (set(ref) != set(cand)) if opt else (ref != cand):
        only_r = [sorted(m) for m in ref if m not in cand][:2]
        only_c = [sorted(m) for m in cand if m not in ref][:2]
        dup = [sorted(m) for m, c in cand.items() if c > 1][:2]
        raise Bug(f"{sum(cand.values())} {'optimal ' if opt else ''}models vs {sum(ref.values())} (ref); only in ref: {only_r}; "
                  f"only in cand: {only_c}; duplicates in cand: {dup}\n--> failing: {cmd_str(cmd)}\n--> reference: {cmd_str(rcmd)}")


def one_test(seed, stats):
    rng = random.Random(seed)
    random.seed(seed)
    kind = rng.choice(["cnf", "cnf", "wcnf", "opb", "opbopt", "bigcnf", "bigopb"])
    path = fuzz.unique_file("satTest", "." + ("opb" if "opb" in kind else "wcnf" if kind == "wcnf" else "cnf"))
    opt = kind in ("wcnf", "opbopt")
    big = kind.startswith("big")
    with open(path, "w") as f:
        f.write(gen_big(rng, kind == "bigopb") if big else gen_cnf(rng, kind == "wcnf") if "cnf" in kind
                else gen_opb(rng, kind == "opbopt"))
    stats["tests"] += 1
    keep = False
    try:
        for _ in range(4):
            copts = [o for o in fuzz.rnd_opts("opt" if opt else "enum", threads_ok=True) if not o.startswith(ASP_ONLY)]
            if rng.random() < 0.5 and not any(o.startswith("--sat-prepro") for o in copts):
                copts.append("--sat-prepro=" + rng.choice(["2", "3", "1", "2,iter=1", "3,occ=5", "2,size=1"]))
            binary = options.asan if options.asan and rng.random() < options.asan_perc / 100 else options.clasp
            try:
                if big:
                    check_big(path, copts, binary)
                else:
                    check(path, copts, binary, opt)
                stats["runs"] += 1
            except Skip as e:
                stats["skips"] += 1
                if options.verbose:
                    print(f"skip: {str(e)[:150]}")
    except Bug as e:
        keep = True
        stats["bugs"] += 1
        print(f"{RED}BUG FOUND: {e}{NC}\n--> input: {path}")
        print(f"--> check with: {os.path.join(HERE, 'satfuzz.py')} --check {path} {shlex.quote('--cand=' + ' '.join(copts))}"
              f" --clasp {binary}")
        print(f"--> re-run this test: ./satfuzz.py --seed {seed}")
        if not options.keep_going:
            sys.exit(1)
    except Skip:
        stats["skips"] += 1
    finally:
        if not keep and not options.keep and os.path.exists(path):
            os.unlink(path)


def parse():
    p = argparse.ArgumentParser(description="Differential fuzzer for clasp on CNF/WCNF/OPB")
    p.add_argument("--seed", type=int)
    p.add_argument("--only", type=int, default=2**40)
    p.add_argument("--tout", type=float, default=5)
    p.add_argument("--clasp", default=os.path.join(HERE, "..", "build", "rel", "bin", "clasp"))
    p.add_argument("--asan", default=os.path.join(HERE, "..", "build", "asan", "bin", "clasp"))
    p.add_argument("--asan-perc", type=int, default=15)
    p.add_argument("--outdir", default=os.path.join(HERE, "out"))
    p.add_argument("--keep", action="store_true")
    p.add_argument("--keep-going", action="store_true")
    p.add_argument("--check", metavar="FILE")
    p.add_argument("--cand", default="")
    p.add_argument("--verbose", "-v", action="store_true")
    o = p.parse_args()
    if not os.path.isfile(o.asan):
        o.asan = None
    return o


if __name__ == "__main__":
    options = parse()
    sys.argv = [sys.argv[0], "--tout", str(options.tout), "--outdir", options.outdir]
    fuzz.options = fuzz.parse()
    os.makedirs(options.outdir, exist_ok=True)
    if options.check:
        text = open(options.check).read()
        opt = options.check.endswith(".wcnf") or (options.check.endswith(".opb") and "min:" in text)
        try:
            if text.startswith("c big") or "\n* big\n" in text:
                check_big(options.check, shlex.split(options.cand), options.clasp)
            else:
                check(options.check, shlex.split(options.cand), options.clasp, opt)
            print("OK")
        except Bug as e:
            print(f"{RED}BUG FOUND: {e}{NC}")
            sys.exit(1)
        except Skip as e:
            print(f"SKIP: {e}")
        sys.exit(0)
    stats = {"tests": 0, "runs": 0, "skips": 0, "bugs": 0}
    for i in range(options.only):
        one_test(options.seed if options.seed is not None else int.from_bytes(os.urandom(7)), stats)
        if options.seed is not None:
            break
        if (i + 1) % 50 == 0:
            print(f"{GREEN}--- stats: {stats}{NC}")
    print(f"{GREEN}--- stats: {stats}{NC}")
