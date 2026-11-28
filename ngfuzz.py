#!/usr/bin/env python3
# Grounder fuzzer: a random non-ground program (genng.py) vs. the generator's own naive instantiation of it.
# Usage: ./ngfuzz.py [--only N] [--keep-going] | ./ngfuzz.py --check NG.lp GROUND.lp --pipe P --cand="OPTS"
import argparse
import os
import random
import shlex
import subprocess
import sys

import fuzz
from fuzz import Bug, Skip, GREEN, RED, NC

HERE = os.path.dirname(os.path.realpath(__file__))
GROUND_OPTS = ("--keep-facts", "--preserve-facts")


def check(ng, ground, pipe, copts, binary):
    ref = fuzz.solve(options.clingo, [ground], fuzz.REF + ["-n0"], ref=True)
    gopts = [o for o in copts if o.startswith(GROUND_OPTS)]
    sopts = [o for o in copts if not o.startswith(GROUND_OPTS)]
    tmp = None
    try:
        if pipe == "direct":
            inputs, sopts = [ng], copts
        else:
            tmp = fuzz.ground_to(pipe, ng, gopts)
            inputs = [tmp]
        cand = fuzz.solve(binary, inputs, sopts + ["-n0"])
        try:
            fuzz.compare("enum", ref, cand, "direct")
        except Bug as e:
            raise Bug(f"{e}\n--> failing: {fuzz.cmd_str(cand.cmd)}\n--> reference: {fuzz.cmd_str(ref.cmd)}")
    finally:
        if tmp and not options.keep and os.path.exists(tmp):
            os.unlink(tmp)


def one_test(seed, stats):
    rng = random.Random(seed)
    random.seed(seed)
    ng = fuzz.unique_file("ngTest", ".lp")
    ground = fuzz.unique_file("ngGround", ".lp")
    if subprocess.call([sys.executable, os.path.join(HERE, "genng.py"), "--seed", str(rng.randint(0, 2**62)), ng, ground]):
        print(f"{RED}ERROR: genng.py failed for seed {seed}{NC}")
        sys.exit(-1)
    stats["tests"] += 1
    keep = False
    try:
        for _ in range(3):
            pipe = rng.choice(["direct", "direct", "aspif", "text"])
            copts = fuzz.rnd_opts("enum", threads_ok=True)
            binary = options.asan if options.asan and rng.random() < options.asan_perc / 100 else options.clingo
            try:
                check(ng, ground, pipe, copts, binary)
                stats["runs"] += 1
            except Skip:
                stats["skips"] += 1
    except Bug as e:
        keep = True
        stats["bugs"] += 1
        print(f"{RED}BUG FOUND: {e}{NC}\n--> non-ground: {ng}\n--> ground: {ground}")
        print(f"--> check with: {os.path.join(HERE, 'ngfuzz.py')} --check {ng} {ground} --pipe {pipe} "
              f"{shlex.quote('--cand=' + ' '.join(copts))} --clingo {binary}")
        print(f"--> re-run this test: ./ngfuzz.py --seed {seed}")
        if not options.keep_going:
            sys.exit(1)
    except Skip:
        stats["skips"] += 1
    finally:
        if not keep and not options.keep:
            for p in (ng, ground):
                if os.path.exists(p):
                    os.unlink(p)


def parse():
    p = argparse.ArgumentParser(description="Grounder fuzzer: non-ground program vs. its naive instantiation")
    p.add_argument("--seed", type=int)
    p.add_argument("--only", type=int, default=2**40)
    p.add_argument("--tout", type=float, default=5)
    p.add_argument("--clingo", default=os.path.join(HERE, "..", "build", "rel", "bin", "clingo"))
    p.add_argument("--asan", default=os.path.join(HERE, "..", "build", "asan", "bin", "clingo"))
    p.add_argument("--asan-perc", type=int, default=15)
    p.add_argument("--outdir", default=os.path.join(HERE, "out"))
    p.add_argument("--keep", action="store_true")
    p.add_argument("--keep-going", action="store_true")
    p.add_argument("--check", nargs=2, metavar=("NG", "GROUND"))
    p.add_argument("--pipe", default="direct", choices=["direct", "aspif", "text"])
    p.add_argument("--cand", default="")
    o = p.parse_args()
    if not os.path.isfile(o.asan):
        o.asan = None
    return o


if __name__ == "__main__":
    options = parse()
    sys.argv = [sys.argv[0], "--tout", str(options.tout), "--outdir", options.outdir, "--clingo", options.clingo]
    fuzz.options = fuzz.parse()
    os.makedirs(options.outdir, exist_ok=True)
    if options.check:
        options.keep = True
        try:
            check(*options.check, options.pipe, shlex.split(options.cand), options.clingo)
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
