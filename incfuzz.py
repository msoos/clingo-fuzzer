#!/usr/bin/env python3
# Multi-shot fuzzer: splits a ground program into incremental aspif steps, checks each step against a single-shot run.
# Usage: ./incfuzz.py [--only N] [--keep-going] | ./incfuzz.py --check FILE.aspif --cand="OPTS"
import argparse
import json
import os
import random
import shlex
import sys

import fuzz
from fuzz import Bug, Skip, Timeout, cmd_str, run, GREEN, RED, NC

HERE = os.path.dirname(os.path.realpath(__file__))
GROUND_ONLY = ("--keep-facts", "--preserve-facts")
FREE, TRUE, FALSE, RELEASE = 0, 1, 2, 3


def rule_atoms(st):
    """(head atoms, body atoms) of an aspif rule statement: 1 <head type> <n> <atoms> <body>."""
    nh = st[2]
    head = st[3:3 + nh]
    rest = st[3 + nh:]
    if rest[0] == 0:
        lits = rest[2:2 + rest[1]]
    else:
        lits = rest[3:3 + 2 * rest[2]:2]
    return head, [abs(l) for l in lits]


def renumber(line, m):
    """Rewrite the atoms of an aspif rule/output/external line with the mapping m."""
    t = line.split()
    lit = lambda x: str(m[abs(int(x))] * (1 if int(x) > 0 else -1))
    if t[0] == "1":
        n = int(t[2])
        t[3:3 + n] = [str(m[int(a)]) for a in t[3:3 + n]]
        r = 3 + n
        if t[r] == "0":
            nb = int(t[r + 1])
            t[r + 2:r + 2 + nb] = [lit(x) for x in t[r + 2:r + 2 + nb]]
        else:
            nb = int(t[r + 2])
            for i in range(nb):
                t[r + 3 + 2 * i] = lit(t[r + 3 + 2 * i])
    elif t[0] == "4":
        t[4:] = [lit(x) for x in t[4:]]
    elif t[0] == "5":
        t[1] = str(m[int(t[1])])
    elif t[0] == "7":  # 7 <type> <atom> <bias> <prio> <n> <lits>
        t[2] = str(m[int(t[2])])
        t[6:] = [lit(x) for x in t[6:]]
    elif t[0] == "2":  # 2 <prio> <n> <lit> <weight> ...
        for i in range(int(t[2])):
            t[3 + 2 * i] = lit(t[3 + 2 * i])
    return " ".join(t)


def split(prog_lines, k, rng):
    """Distribute the rules/outputs of a single-shot aspif into k steps; returns incremental aspif text."""
    rules, outs, mins = [], [], []
    for line in prog_lines:
        st = [int(x) if x.lstrip("-").isdigit() else x for x in line.split()]
        if st[0] == 1:
            rules.append((line, *rule_atoms(st)))
        elif st[0] == 4:
            lits = [abs(int(x)) for x in line.split()[4:]]  # 4 <len> <name> <n> <lits>
            outs.append((line, lits))
        elif st[0] == 2:
            mins.append((line, [abs(int(x)) for x in line.split()[3::2]]))
        elif st[0] == 7:  # heuristics don't change the answer sets
            t = line.split()
            mins.append((line, [int(t[2])] + [abs(int(x)) for x in t[6:]]))
    defined = {a for _, h, _ in rules for a in h}
    used = {a for _, _, b in rules for a in b} | {a for _, l in outs + mins for a in l}
    step = {a: rng.randint(1, k) for a in defined}
    changed = True
    while changed:
        changed = False
        for _, h, b in rules:
            s = max([step[a] for a in h] + [step.get(a, 1) for a in b] + [1])
            for a in h:
                if step[a] < s:
                    step[a], changed = s, True
    externals = sorted(used - defined)
    ext = rng.sample(externals, min(len(externals), rng.randint(0, 4)))
    # atoms first defined in a step must have larger ids than all atoms of earlier steps
    order = sorted(defined | used, key=lambda a: (step.get(a, 1), a))
    m = {a: i + 1 for i, a in enumerate(order)}
    steps = [[] for _ in range(k)]
    for line, h, b in rules:
        s = max([step[a] for a in h] + [step.get(a, 1) for a in b] + [1])
        steps[s - 1].append(renumber(line, m))
    for line, lits in outs + mins:  # minimize statements of all steps accumulate
        steps[max([step.get(a, 1) for a in lits] + [1]) - 1].append(renumber(line, m))
    val = {}
    for i in range(k):
        for a in ext:
            if val.get(a) == RELEASE:
                continue
            if i == 0 or rng.random() < 0.5:
                val[a] = rng.choice([FREE, TRUE, FALSE, FALSE, RELEASE] if i else [FREE, TRUE, FALSE])
                steps[i].append(f"5 {m[a]} {val[a]}")
        # assumptions hold for this step only
        avail = [m[a] for a in order if step.get(a, 1) <= i + 1]
        if avail and rng.random() < 0.4:
            lits = [x * rng.choice([1, -1]) for x in rng.sample(avail, min(len(avail), rng.randint(1, 2)))]
            steps[i].append(f"6 {len(lits)} " + " ".join(map(str, lits)))
    return "asp 1 0 0 incremental\n" + "".join("\n".join(s + ["0"]) + "\n" for s in steps)


def parse_steps(text):
    lines = text.strip().splitlines()
    assert lines[0].startswith("asp ") and "incremental" in lines[0]
    steps, cur = [], []
    for line in lines[1:]:
        if line.strip() == "0":
            steps.append(cur)
            cur = []
        elif line.strip():
            cur.append(line)
    return steps


def prefix_program(steps, k):
    """Single-shot aspif equivalent to steps 1..k: externals become choices (free), facts (true) or nothing,
    the assumptions of step k become integrity constraints."""
    body, val = [], {}
    for i, s in enumerate(steps[:k]):
        for line in s:
            if line.startswith("6 "):
                if i == k - 1:
                    for l in map(int, line.split()[2:]):
                        body.append(f"1 0 0 0 1 {-l}")
            elif line.startswith("5 "):
                _, a, v = line.split()
                if val.get(a) != RELEASE:
                    val[a] = int(v)
            else:
                body.append(line)
    for a, v in val.items():
        if v == FREE:
            body.append(f"1 1 1 {a} 0 0")
        elif v == TRUE:
            body.append(f"1 0 1 {a} 0 0")
    return "asp 1 0 0\n" + "\n".join(body + ["0"]) + "\n"


def models_of(js, opt):
    """Per call: all models, or for optimization the optimal models and the optimum (zero levels dropped)."""
    res = []
    for c in js.get("Call", []):
        wits = [(frozenset(w["Value"]), tuple(w.get("Costs", []))) for w in c.get("Witnesses", []) if "Value" in w]
        if opt and wits:
            best = min(co for _, co in wits)
            wits = [(m, co) for m, co in wits if co == best]
            norm = tuple(x for x in best if x)  # the runs may differ in (all-zero) priority levels
            res.append(([m for m, _ in wits], norm))
        else:
            res.append(([m for m, _ in wits], None))
    return res


def solve(binary, opts, path, opt, tout=None):
    cmd = [binary, "--outf=2", "-n0", *(["--opt-mode=optN"] if opt else []), *opts, path]
    out = run(cmd, tout=tout)
    try:
        js = json.loads(out)
    except json.JSONDecodeError as e:
        raise Bug(f"bad JSON output ({e})\n--> {cmd_str(cmd)}")
    if js.get("Result") == "UNKNOWN" or js.get("Models", {}).get("More", "no") != "no":
        raise Skip("unfinished: " + cmd_str(cmd))
    return cmd, models_of(js, opt)


def check(inc_path, copts, binary):
    steps = parse_steps(open(inc_path).read())
    opt = any(l.startswith("2 ") for s in steps for l in s)
    tmp = fuzz.unique_file("incref", ".aspif")
    try:
        cmd, cand = solve(binary, copts, inc_path, opt)
        if len(cand) > len(steps):
            raise Bug(f"{len(cand)} calls for {len(steps)} steps\n--> {cmd_str(cmd)}")
        cand += [([], None)] * (len(steps) - len(cand))  # clasp stops after a top-level conflict: later steps are unsat
        for k in range(1, len(steps) + 1):
            with open(tmp, "w") as f:
                f.write(prefix_program(steps, k))
            rcmd, ref = solve(options.clasp, fuzz.REF, tmp, opt)
            (rm, rc), (cm, cc) = ref[0], cand[k - 1]
            a, b = set(rm), set(cm)
            if cc != rc and rm and cm:
                raise Bug(f"step {k}: optimum {cc} vs {rc} (ref)\n--> failing: {cmd_str(cmd)}\n"
                          f"--> reference (step {k} as single shot): {cmd_str(rcmd)}")
            if (not opt and len(rm) != len(cm)) or a != b:
                only_r = " ".join("{" + " ".join(sorted(m)) + "}" for m in sorted(a - b, key=sorted)[:3])
                only_c = " ".join("{" + " ".join(sorted(m)) + "}" for m in sorted(b - a, key=sorted)[:3])
                raise Bug(f"step {k}: {len(cm)} {'optimal ' if opt else ''}models vs {len(rm)} (ref); only in ref: {only_r}; "
                          f"only in cand: {only_c}\n--> failing: {cmd_str(cmd)}\n--> reference (step {k} as single shot): {cmd_str(rcmd)}")
    finally:
        if not options.keep:
            os.unlink(tmp)


def one_test(seed, stats):
    rng = random.Random(seed)
    random.seed(seed)
    t = {"task": "opt" if rng.random() < 0.3 else "enum", "size": rng.choice(["small", "normal"]), "gseed": rng.randint(0, 2**62),
         "reifiable": False, "neg": rng.random() < 0.4}
    fuzz.gen_prog(t)
    ground = fuzz.unique_file("incground", ".aspif")
    inc = fuzz.unique_file("incTest", ".aspif")
    stats["tests"] += 1
    keep = False
    try:
        run([options.clingo, "--mode=gringo", t["prog"]], outfile=ground)
        lines = [l for l in open(ground).read().splitlines()[1:] if l.strip() and l.strip() != "0"]
        lines = [l for l in lines if l.startswith(("1 ", "4 ", "2 ", "7 "))]
        with open(inc, "w") as f:
            f.write(split(lines, rng.randint(2, 4), rng))
        for _ in range(3):
            copts = [o for o in fuzz.rnd_opts(t["task"], threads_ok=True) if not o.startswith(GROUND_ONLY)]
            binary = options.asan if options.asan and rng.random() < options.asan_perc / 100 else options.clasp
            try:
                check(inc, copts, binary)
                stats["runs"] += 1
            except Timeout:
                stats["skips"] += 1
            except Skip:
                stats["skips"] += 1
    except Bug as e:
        keep = True
        stats["bugs"] += 1
        print(f"{RED}BUG FOUND: {e}{NC}")
        print(f"--> program: {t['prog']}\n--> incremental: {inc}")
        print(f"--> check with: {os.path.join(HERE, 'incfuzz.py')} --check {inc} {shlex.quote('--cand=' + ' '.join(copts))}"
              f" --clasp {binary}")
        print(f"--> re-run this test: ./incfuzz.py --seed {seed}")
        if not options.keep_going:
            sys.exit(1)
    except Skip as e:
        stats["skips"] += 1
    finally:
        if not keep and not options.keep:
            for p in (t["prog"], ground, inc):
                if os.path.exists(p):
                    os.unlink(p)


def parse():
    p = argparse.ArgumentParser(description="Multi-shot differential fuzzer for clasp")
    p.add_argument("--seed", type=int)
    p.add_argument("--only", type=int, default=2**40)
    p.add_argument("--tout", type=float, default=5)
    p.add_argument("--clasp", default=os.path.join(HERE, "..", "build", "rel", "bin", "clasp"))
    p.add_argument("--clingo", default=os.path.join(HERE, "..", "build", "rel", "bin", "clingo"))
    p.add_argument("--asan", default=os.path.join(HERE, "..", "build", "asan", "bin", "clasp"))
    p.add_argument("--asan-perc", type=int, default=15)
    p.add_argument("--outdir", default=os.path.join(HERE, "out"))
    p.add_argument("--keep", action="store_true")
    p.add_argument("--keep-going", action="store_true")
    p.add_argument("--check", metavar="FILE")
    p.add_argument("--cand", default="")
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
        options.keep = True
        try:
            check(options.check, shlex.split(options.cand), options.clasp)
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
