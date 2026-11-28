#!/usr/bin/env python3
# Differential fuzzer for clingo: random programs, random option sets, checked against a no-preprocessing run.
# Usage: ./fuzz.py [--seed S] [--only N] [--tout T] ; ./fuzz.py --check FILE --task T --pipe P --cand "OPTS"

import argparse
import copy
import json
import os
import random
import shlex
import signal
import stat
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.realpath(__file__))
RED, GREEN, YELLOW, MAGENTA, NC = "\033[31m", "\033[32m", "\033[33m", "\033[35m", "\033[0m"
# /etc/ld.so.preload puts a lib before the ASan runtime
ENV = dict(os.environ,
           ASAN_OPTIONS="verify_asan_link_order=0:detect_leaks=1:abort_on_error=1",
           UBSAN_OPTIONS="print_stacktrace=1:halt_on_error=1")
REF = ["--eq=0", "--no-backprop", "--trans-ext=no", "--sat-prepro=no"]
OK_RC = {0, 10, 20, 30}
MAX_OUT = 64 << 20
BAD_OUT = ["AddressSanitizer", "LeakSanitizer", "runtime error:", "Assertion", "*** ERROR"]
TASKS = ["enum", "opt", "proj"]
OPT_ERR = ["*** ERROR: (clingo): <config>", "*** ERROR: (clingo): In context",
           "*** ERROR: (clasp): <config>", "*** ERROR: (clasp): In context"]
# already reported, see bugs/; --no-known turns this off
KNOWN = {}

options = None
current_proc = None


def _cleanup_and_exit(_signum, _frame):
    if current_proc is not None and current_proc.poll() is None:
        current_proc.kill()
        current_proc.wait()
    sys.exit(0)


signal.signal(signal.SIGHUP, _cleanup_and_exit)
signal.signal(signal.SIGTERM, _cleanup_and_exit)


class Bug(Exception):
    pass


class Skip(Exception):
    pass


class Timeout(Skip):
    def __init__(self, cmd):
        super().__init__("timeout: " + cmd_str(cmd))
        self.cmd = cmd


def unique_file(prefix, suffix=".lp", max_num_files=100000):
    counter = 1
    while True:
        path = os.path.join(options.outdir, f"{prefix}_{counter}{suffix}")
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL, stat.S_IREAD | stat.S_IWRITE)
            os.close(fd)
            return path
        except OSError:
            pass
        counter += 1
        if counter > max_num_files:
            print(f"Cannot create unique_file, last try was: {path}")
            sys.exit(-1)


def cmd_str(cmd):
    return " ".join(shlex.quote(str(x)) for x in cmd)


def run(cmd, outfile=None, tout=None):
    global current_proc
    if options.verbose:
        print(f"{MAGENTA}--> {cmd_str(cmd)}{NC}")
    # a file instead of a pipe, so that huge outputs (millions of models) can be skipped without reading them
    out = open(outfile, "w") if outfile else tempfile.TemporaryFile("w+")
    proc = subprocess.Popen(cmd, stdout=out, stderr=subprocess.PIPE, text=True, env=ENV)
    current_proc = proc
    try:
        so, se = proc.communicate(timeout=tout or options.tout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        current_proc = None
        raise Timeout(cmd)
    finally:
        if outfile:
            out.close()
    current_proc = None
    if not outfile:
        size = out.seek(0, os.SEEK_END)
    if any(e in se for e in OPT_ERR):
        stats["opt_errs"] += 1
        raise Skip("option error: " + se.strip().splitlines()[0])
    if options.known:
        for name, pat in KNOWN.items():
            if pat in se:
                stats["known"] += 1
                raise Skip(f"known bug {name}")
    if proc.returncode not in OK_RC or any(b in se for b in BAD_OUT):
        lines = se.strip().splitlines()
        first = next((i for i, l in enumerate(lines) if "runtime error:" in l or "ERROR: " in l or "leak of" in l), None)
        tail = "\n".join(lines[first:first + 40] if first is not None else lines[-15:])
        raise Bug(f"crash/error rc={proc.returncode}\n{tail}\n--> {cmd_str(cmd)}")
    if outfile:
        return ""
    with out:
        if size > MAX_OUT:
            raise Skip(f"output too large ({size >> 20} MB): {cmd_str(cmd)}")
        out.seek(0)
        return out.read()


class Result:
    def __init__(self, js, cmd):
        self.cmd = cmd
        self.status = js["Result"]
        calls = js.get("Call", [])
        wits = calls[-1].get("Witnesses", []) if calls else []
        # hierarchical optimization reports lower bounds as {"Lower": [...]}
        wits = [w for w in wits if "Value" in w]
        self.models = [frozenset(w["Value"]) for w in wits]
        self.costs = [tuple(w.get("Costs", [])) for w in wits]
        m = js.get("Models", {})
        self.number = m.get("Number", 0)
        self.more = m.get("More", "no")
        self.optimum = tuple(m["Costs"]) if "Costs" in m else None
        self.opt_found = m.get("Optimum") == "yes"


def solve(binary, inputs, opts, pre=(), ref=False):
    cmd = [binary, *pre, "--outf=2", *opts, *inputs]
    try:
        js = run(cmd)
    except Bug as e:
        # the program itself does not parse: not a bug, e.g. while minimizing
        if ref and "parsing failed" in str(e):
            raise Skip("invalid input program")
        raise
    try:
        res = Result(json.loads(js), cmd)
    except (json.JSONDecodeError, KeyError) as e:
        raise Bug(f"bad JSON output ({e})\n--> {cmd_str(cmd)}")
    if res.status == "UNKNOWN" or res.more != "no":
        raise Skip("unfinished: " + cmd_str(cmd))
    return res


def rnd_opts(task, threads_ok=True):
    pool = [
        lambda: f"--configuration={random.choice(['frumpy', 'jumpy', 'tweety', 'handy', 'crafty', 'trendy', 'auto'])}",
        lambda: "--heuristic=" + random.choice(["berkmin", "vmtf", "vsids", "domain", "unit", "none",
                                                "berkmin,3", "vmtf,2", "vsids,70"]),
        lambda: f"--eq={random.choice([0, 1, 3, 5, -1])}",
        lambda: random.choice(["--backprop", "--no-backprop"]),
        lambda: "--trans-ext=" + random.choice(["no", "all", "choice", "card", "weight", "scc", "integ", "dynamic"]),
        lambda: "--sat-prepro=" + random.choice(["no", "1", "2", "3", "2,iter=1", "3,occ=5", "1,size=1"]),
        lambda: random.choice(["--no-gamma", "--dlp-old-map", "--eq-dfs"]),
        lambda: "--lookahead=" + random.choice(["atom", "body", "hybrid", "atom,3", "no"]),
        lambda: "--no-lookback",
        lambda: f"--rand-freq={random.choice([0.01, 0.1, 0.5, 1.0])}",
        lambda: f"--seed={random.randint(0, 2**31 - 1)}",
        lambda: "--sign-def=" + random.choice(["asp", "pos", "neg", "rnd"]),
        lambda: "--sign-fix",
        lambda: "--restarts=" + random.choice(["F,10", "L,5", "x,10,1.5", "+,5,3", "D,50,0.8", "no", "L,1"]),
        lambda: "--local-restarts",
        lambda: "--deletion=" + random.choice(["basic,50", "sort,90,lbd", "ipSort,20,mixed", "ipHeap", "no"]),
        lambda: "--del-max=" + random.choice(["10,0", "100,1"]),
        lambda: "--strengthen=" + random.choice(["local", "recursive,short", "recursive,binary,no", "no"]),
        lambda: f"--otfs={random.randint(0, 2)}",
        lambda: f"--reverse-arcs={random.randint(0, 3)}",
        lambda: "--contraction=" + random.choice(["3", "5,allUIP", "10,dynamic", "no"]),
        lambda: "--loops=" + random.choice(["common", "shared", "distinct", "no"]),
        lambda: "--partial-check=" + random.choice(["50", "10,2", "100"]),
        lambda: random.choice(["--init-moms", "--no-init-moms"]),
        lambda: "--score-res=" + random.choice(["auto", "min", "set", "multiset"]),
        lambda: "--score-other=" + random.choice(["auto", "no", "loop", "all"]),
        lambda: "--update-lbd=" + random.choice(["less", "glucose", "pseudo", "no"]),
        lambda: "--counter-restarts=" + random.choice(["3", "7,1023"]),
        lambda: "--shuffle=" + random.choice(["1,1", "5,2"]),
        lambda: "--save-progress=" + random.choice(["0", "1", "10"]),
        lambda: "--init-watches=" + random.choice(["rnd", "first", "least"]),
        lambda: "--update-mode=" + random.choice(["propagate", "conflict"]),
        lambda: "--learn-explicit",
        lambda: "--dom-mod=" + random.choice(["level", "pos,show", "neg,scc", "true,all", "false,disj", "init", "factor,opt"]),
        lambda: "--keep-facts",
        lambda: "--preserve-facts=" + random.choice(["none", "body", "symtab", "all"]),
    ]
    if threads_ok:
        pool.append(lambda: f"-t{random.randint(2, 4)},{random.choice(['compete', 'split'])}")
    if task == "enum":
        pool.append(lambda: "--enum-mode=" + random.choice(["bt", "record"]))
    if task == "opt":
        pool += [
            lambda: "--opt-strategy=" + random.choice(
                ["bb", "bb,lin", "bb,hier", "bb,inc", "bb,dec", "usc", "usc,oll", "usc,one", "usc,k,2", "usc,pmres",
                 "usc,oll,disjoint", "usc,one,succinct", "usc,k,0,stratify", "usc,pmres,disjoint,succinct"]),
            lambda: "--opt-usc-shrink=" + random.choice(["lin", "inv", "bin", "rgs", "exp", "min", "lin,3"]),
            lambda: "--opt-heuristic=" + random.choice(["sign", "model", "sign,model"]),
            lambda: "--restart-on-model",
        ]
    k = random.choice([0, 1, 2, 3, 5, 8])
    opts = [f() for f in random.sample(pool, min(k, len(pool)))]
    if "--no-lookback" in opts:
        nolb = ("--heuristic", "--restarts", "--deletion", "--del-max", "--configuration", "--local-restarts",
                "--counter-restarts", "--strengthen", "--otfs", "--reverse-arcs", "--contraction", "--update-lbd",
                "--score-", "--init-moms", "--shuffle", "--opt-strategy=usc", "--opt-usc")
        opts = [o for o in opts if not o.startswith(nolb)]
    return opts


def task_opts(task, cand=None):
    if task == "opt":
        return ["-n0", "--opt-mode=optN"]
    if task == "proj" and cand is not None:
        return ["-n0", "--project=" + random.choice(["auto", "show", "project", "auto,1", "show,3", "project,2"])]
    return ["-n0"]


def distinct(models):
    return set(models)


def optimal_set(res):
    if res.status == "UNSATISFIABLE":
        return set()
    return {m for m, c in zip(res.models, res.costs) if c == res.optimum}


def fmt_models(ms):
    out = []
    for m in sorted(sorted(x) for x in ms)[:4]:
        out.append("{" + " ".join(m[:12]) + (" ..." if len(m) > 12 else "") + "}")
    return " ".join(out) + (" ..." if len(ms) > 4 else "")


def diff_msg(a, b, an, bn):
    only_a = fmt_models(a - b)
    only_b = fmt_models(b - a)
    return f"{len(a)} models vs {len(b)}; only in {an}: {only_a}; only in {bn}: {only_b}"


def align_levels(a, b):
    # regrounding may drop a minimize level whose cost is always 0: drop such levels from the longer one
    def n(r):
        return len(r.optimum) if r.optimum is not None else 0
    if n(a) == n(b):
        return a, b
    if a.optimum is None or b.optimum is None:
        a, b = copy.copy(a), copy.copy(b)
        a.optimum, b.optimum = a.optimum or (), b.optimum or ()
    swap = n(a) < n(b)
    long_, short = (b, a) if swap else (a, b)
    vecs = [long_.optimum or ()] + long_.costs
    zero = [i for i in range(n(long_)) if all(len(v) > i and v[i] == 0 for v in vecs)]
    drop = set(zero[:n(long_) - n(short)])
    out = copy.copy(long_)
    out.optimum = tuple(x for i, x in enumerate(long_.optimum or ()) if i not in drop)
    out.costs = [tuple(x for i, x in enumerate(c) if i not in drop) for c in long_.costs]
    return (a, out) if swap else (out, b)


def compare(task, ref, cand, kind):
    if (ref.status == "UNSATISFIABLE") != (cand.status == "UNSATISFIABLE"):
        raise Bug(f"status mismatch: ref {ref.status} vs {cand.status}")
    if task == "opt":
        if kind in ("text", "aspif"):
            ref, cand = align_levels(ref, cand)
        if ref.optimum != cand.optimum:
            raise Bug(f"optimum mismatch: ref {ref.optimum} vs {cand.optimum}")
        a, b = optimal_set(ref), optimal_set(cand)
        if a != b:
            raise Bug("optimal models differ: " + diff_msg(a, b, "ref", "cand"))
        return
    a, b = distinct(ref.models), distinct(cand.models)
    if kind == "brave":
        want = frozenset().union(*a) if a else None
        got = cand.models[-1] if cand.models else None
        if want != got:
            raise Bug(f"brave consequences: want {sorted(want or [])} got {sorted(got or [])}")
        return
    if kind == "cautious":
        want = frozenset.intersection(*a) if a else None
        got = cand.models[-1] if cand.models else None
        if want != got:
            raise Bug(f"cautious consequences: want {sorted(want or [])} got {sorted(got or [])}")
        return
    if a != b:
        raise Bug("models differ: " + diff_msg(a, b, "ref", "cand"))
    if task == "proj" and len(cand.models) != len(b):
        raise Bug(f"projection printed duplicates: {len(cand.models)} models, {len(b)} distinct")
    if task == "enum" and kind == "direct" and ref.number != cand.number:
        raise Bug(f"model count mismatch: ref {ref.number} vs {cand.number}")


def ground_to(fmt, prog, gopts):
    binary = options.clingo
    if fmt == "aspif":
        f = unique_file("aspif", ".aspif")
        run([binary, "--mode=gringo", *gopts, prog], f)
    elif fmt == "text":
        f = unique_file("text", ".lp")
        run([binary, "--text", *gopts, prog], f)
        if "#delayed" in open(f).read() or "#external" in open(prog).read():
            # externals with rules whose bodies gringo can only simplify on reparsing behave differently
            os.unlink(f)
            raise Skip("text output has #delayed")
    else:
        f = unique_file("reify", ".lp")
        run([binary, "--output=reify", *gopts, prog], f)
    return f


def run_cand(t, ref, pipe, kind, copts, binary):
    tmp = None
    pre = []
    t["last_cmd"] = None
    gopts = [o for o in copts if o.startswith(("--keep-facts", "--preserve-facts"))]
    sopts = [o for o in copts if o not in gopts]
    try:
        if pipe == "direct":
            inputs = [t["prog"]]
            sopts = copts
        elif pipe in ("aspif", "text"):
            tmp = ground_to(pipe, t["prog"], gopts)
            inputs = [tmp]
        else:
            tmp = ground_to("reify", t["prog"], gopts + random.choice([[], ["--reify-sccs"]]))
            inputs = [tmp, os.path.join(options.meta_dir, "meta.lp")]
            sopts = [o for o in sopts if not o.startswith("--heuristic=domain") and not o.startswith("--dom-mod")]
        extra = task_opts(t["task"], cand=True)
        if kind in ("brave", "cautious"):
            extra = ["-n0", f"--enum-mode={kind}"]
            sopts = [o for o in sopts if not o.startswith("--enum-mode")]
        cand = solve(binary, inputs, sopts + extra, pre)
        t["last_cmd"] = cand.cmd
        compare(t["task"], ref, cand, kind)
    finally:
        if tmp and not options.keep:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass


def gen_prog(t):
    t["prog"] = unique_file("fuzzTest")
    args = [os.path.join(HERE, "gen.py"), "--seed", str(t["gseed"]), "--size", t["size"]]
    if t["task"] == "opt":
        args.append("--opt")
    if t["task"] == "proj":
        args.append("--proj")
    if t["reifiable"]:
        args.append("--reifiable")
    if t["neg"]:
        args.append("--neg")
    with open(t["prog"], "w") as f:
        if subprocess.call([sys.executable, *args], stdout=f) != 0:
            print(f"{RED}ERROR: generator failed: {cmd_str(args)}{NC}")
            sys.exit(-1)


def rerun_cmd(seed):
    args, skip = [], False
    for x in sys.argv[1:]:
        if skip:
            skip = False
        elif x == "--seed":
            skip = True
        elif not x.startswith("--seed="):
            args.append(x)
    return cmd_str([sys.argv[0], *args, "--seed", str(seed), "--only", "1"])


def report(t, e, pipe, kind, copts, binary):
    print(f"{RED}BUG FOUND: {e}{NC}")
    print(f"{YELLOW}--> program:{NC} {t['prog']}")
    print(f"{YELLOW}--> reference:{NC} {cmd_str(t['ref_cmd'])}")
    if t.get("last_cmd"):
        print(f"{YELLOW}--> failing:{NC} {cmd_str(t['last_cmd'])}")
    if pipe == "ref":
        pipe = kind = "direct"
    check = [os.path.join(HERE, "fuzz.py"), "--check", t["prog"], "--task", t["task"], "--pipe", pipe,
             "--kind", kind, "--cand=" + " ".join(copts), "--clingo", binary]
    print(f"{YELLOW}--> check/minimize with:{NC} {cmd_str(check)}")
    print(f"{YELLOW}                         {NC} ./minim.py {cmd_str(check[1:])}")
    if "seed" in t:
        print(f"{YELLOW}--> re-run this fuzz test:{NC} {rerun_cmd(t['seed'])}")


def pick_cands(t):
    n = random.randint(3, 8)
    cands = []
    for _ in range(n):
        pipe = random.choices(["direct", "aspif", "text", "reify"],
                              [10, 3, 2, 3 if t["reifiable"] and t["task"] == "enum" else 0])[0]
        kind = "direct" if pipe == "direct" else pipe
        if t["task"] == "enum" and random.random() < 0.25:
            kind = random.choice(["brave", "cautious"])
        binary = options.asan if (options.asan and random.random() < options.asan_perc / 100) else options.clingo
        cands.append((pipe, kind, rnd_opts(t["task"], threads_ok=pipe != "reify"), binary))
    return cands


def check_hang(cmd, ref_time):
    tout = 12 * options.tout
    try:
        run(cmd, tout=tout)
    except Skip:
        raise Bug(f"hang: no result within {tout:.0f}s, reference took {ref_time:.2f}s\n--> {cmd_str(cmd)}")
    except Bug:
        pass


def one_test(seed):
    random.seed(seed)
    t = {"seed": seed, "task": options.task or random.choices(TASKS, [5, 3, 2])[0],
         "size": options.size or random.choices(["small", "normal", "big"], [3, 6, 1])[0],
         "gseed": random.randint(0, 2**62), "reifiable": random.random() < 0.3, "neg": random.random() < 0.4}
    gen_prog(t)
    print(f"{GREEN}=== seed {seed} task {t['task']} size {t['size']} file {t['prog']}{NC}")
    stats["tests"] += 1
    pipe, kind, copts, binary = "ref", "ref", [], options.clingo
    try:
        t["ref_cmd"] = [options.clingo, "--outf=2", *REF, *task_opts(t["task"]), t["prog"]]
        start = time.time()
        ref = solve(options.clingo, [t["prog"]], REF + task_opts(t["task"]), ref=True)
        ref_time = time.time() - start
        stats["unsat" if ref.status == "UNSATISFIABLE" else "sat"] += 1
        for pipe, kind, copts, binary in pick_cands(t):
            try:
                run_cand(t, ref, pipe, kind, copts, binary)
                stats["runs"] += 1
            except Timeout as e:
                stats["skips"] += 1
                # reify/text and ASan runs are legitimately much slower than the reference
                if pipe in ("direct", "aspif") and binary == options.clingo and ref_time < options.tout / 50:
                    check_hang(e.cmd, ref_time)
            except Skip as e:
                stats["skips"] += 1
                if options.verbose:
                    print(f"{MAGENTA}skip: {e}{NC}")
    except Skip as e:
        stats["ref_skips"] += 1
        if options.verbose:
            print(f"{MAGENTA}skip test: {e}{NC}")
    except Bug as e:
        t.setdefault("ref_cmd", [options.clingo, *REF, *task_opts(t["task"]), t["prog"]])
        report(t, e, pipe, kind, copts, binary)
        stats["bugs"] += 1
        if not options.keep_going:
            sys.exit(1)
        return
    if not options.keep:
        os.unlink(t["prog"])


def check_mode():
    t = {"prog": options.check, "task": options.task or "enum", "reifiable": True}
    copts = shlex.split(options.cand)
    binary = options.clingo
    try:
        t["ref_cmd"] = [options.clingo, "--outf=2", *REF, *task_opts(t["task"]), t["prog"]]
        ref = solve(options.clingo, [t["prog"]], REF + task_opts(t["task"]), ref=True)
        random.seed(options.seed or 0)
        run_cand(t, ref, options.pipe, options.kind, copts, binary)
    except Skip as e:
        print(f"SKIP: {e}")
        sys.exit(2)
    except Bug as e:
        report(t, e, options.pipe, options.kind, copts, binary)
        sys.exit(1)
    print("OK")
    sys.exit(0)


def parse():
    p = argparse.ArgumentParser(description="Differential fuzzer for clingo")
    p.add_argument("--seed", type=int)
    p.add_argument("--only", type=int, default=2**40)
    p.add_argument("--tout", "-t", type=float, default=5)
    p.add_argument("--task", choices=TASKS)
    p.add_argument("--size", choices=["small", "normal", "big"])
    p.add_argument("--clingo", default=os.path.join(HERE, "..", "build", "rel", "bin", "clingo"))
    p.add_argument("--asan", default=os.path.join(HERE, "..", "build", "asan", "bin", "clingo"))
    p.add_argument("--asan-perc", type=int, default=15, help="percent of candidate runs on the ASan binary")
    p.add_argument("--meta-dir", default=os.path.join(HERE, "..", "examples", "reify", "common"))
    p.add_argument("--outdir", default=os.path.join(HERE, "out"))
    p.add_argument("--keep", action="store_true", help="keep generated files")
    p.add_argument("--keep-going", action="store_true", help="don't stop at the first bug")
    p.add_argument("--no-known", dest="known", action="store_false", help="report known bugs too")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--check", metavar="FILE", help="run reference vs one candidate on FILE")
    p.add_argument("--pipe", default="direct", choices=["direct", "aspif", "text", "reify"])
    p.add_argument("--kind", default="direct", choices=["direct", "aspif", "text", "reify", "brave", "cautious"])
    p.add_argument("--cand", default="")
    o = p.parse_args()
    if not os.path.isfile(o.asan):
        o.asan = None
    return o


stats = {"sat": 0, "unsat": 0, "tests": 0, "runs": 0, "skips": 0, "ref_skips": 0, "opt_errs": 0, "known": 0, "bugs": 0}

if __name__ == "__main__":
    options = parse()
    os.makedirs(options.outdir, exist_ok=True)
    if options.check:
        options.keep = True
        check_mode()
    for i in range(options.only):
        seed = options.seed if options.seed is not None else int.from_bytes(os.urandom(7))
        one_test(seed)
        if options.seed is not None:
            break
        if (i + 1) % 50 == 0:
            print(f"{GREEN}--- stats: {stats}{NC}")
    print(f"{GREEN}--- stats: {stats}{NC}")
