#!/usr/bin/env python3
# Minimize a failing program + options with hierarchical delta debugging; same arguments as fuzz.py --check.
# Usage: ./minim.py --check FILE --task T --pipe P --kind K --cand="OPTS" [--clingo BIN] [-j N]

import os
import re
import shlex
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.realpath(__file__))
FUZZ = os.path.join(HERE, "fuzz.py")
OPEN, CLOSE = "({[", ")}]"


def norm(args):
    out = []
    for a in args:
        if a.startswith(("--check=", "--cand=")):
            out += a.split("=", 1)
        else:
            out.append(a)
    return out


def get_arg(args, name):
    return args[args.index(name) + 1]


def set_arg(args, name, val):
    args = list(args)
    i = args.index(name)
    if name == "--cand":
        return args[:i] + ["--cand=" + val] + args[i + 2:]
    args[i + 1] = val
    return args


def signature(out):
    m = re.search(r"BUG FOUND: (.*)", out)
    if not m:
        return None
    msg = m.group(1)
    for pat in [r"Assertion `[^']*' failed", r"AddressSanitizer: [\w-]+", r"LeakSanitizer", r"runtime error: [^\n]*"]:
        mm = re.search(pat, out)
        if mm:
            return mm.group(0)
    if msg.startswith("crash/error"):
        err = re.search(r"error: (.*)", out)
        return msg.split("\n")[0] + (" " + err.group(1) if err else "")
    return msg.split(":")[0]


class Oracle:
    def __init__(self, args, sig, tmpdir, suffix):
        self.args, self.sig, self.tmpdir, self.suffix = args, sig, tmpdir, suffix
        self.cache = {}
        self.calls = 0

    def __call__(self, text, opts):
        key = (text, tuple(opts))
        if key not in self.cache:
            self.calls += 1
            fd, path = tempfile.mkstemp(suffix=self.suffix, dir=self.tmpdir)
            with os.fdopen(fd, "w") as f:
                f.write(text)
            a = set_arg(set_arg(self.args, "--check", path), "--cand", " ".join(opts))
            r = subprocess.run([sys.executable, FUZZ, *a, "--no-known"], capture_output=True, text=True)
            os.unlink(path)
            self.cache[key] = r.returncode == 1 and signature(r.stdout) == self.sig
        return self.cache[key]


def ddmin(n_items, test, pool):
    """Indices to keep; the removals of one granularity are tested in parallel."""
    keep = list(range(n_items))
    n = 2
    while keep:
        chunk = max(1, len(keep) // n)
        cands = [keep[:i] + keep[i + chunk:] for i in range(0, len(keep), chunk)]
        hit = next((c for c, ok in zip(cands, pool.map(test, cands)) if ok), None)
        if hit is not None:
            keep = hit
            n = max(n - 1, 2)
        elif chunk == 1:
            break
        else:
            n = min(n * 2, len(keep))
    return keep


def split_top(s, sep):
    parts, depth, cur, i = [], 0, "", 0
    while i < len(s):
        c = s[i]
        if c in OPEN:
            depth += 1
        elif c in CLOSE:
            depth -= 1
        if depth == 0 and s.startswith(sep, i) and not (sep == ":" and s.startswith((":-", ":~"), i)):
            parts.append(cur)
            cur = ""
            i += len(sep)
            continue
        cur += c
        i += 1
    parts.append(cur)
    return parts


# node: str leaf | (sep, [nodes]) | ("{}", prefix, inner, suffix)
SEPS = [":-", ";", "|", ":", ","]


def parse(s):
    s = s.strip()
    for sep in SEPS:
        parts = split_top(s, sep)
        if len(parts) > 1:
            return (sep, [parse(p) for p in parts])
    m = re.match(r"^(.*?)\{(.*)\}(.*)$", s, re.S)
    if m and m.group(2).count("{") == m.group(2).count("}"):
        return ("{}", m.group(1).strip(), parse(m.group(2)), m.group(3).strip())
    return s


def show(node):
    if isinstance(node, str):
        return node
    if node[0] == "{}":
        _, pre, inner, suf = node
        return " ".join(x for x in [pre, "{ " + show(inner) + " }", suf] if x)
    sep, kids = node
    texts = [show(k) for k in kids]
    if sep == ":-":
        head, body = texts[0], " :- ".join(t for t in texts[1:] if t)
        if not body:
            return head
        return (head + " " if head else "") + ":- " + body
    if sep == ":":
        return " : ".join(texts)
    return f"{sep} ".join(t for t in texts if t)


def split_stmt(line):
    m = re.match(r"^(.*?)\.(\s*\[[^\]]*\])?\s*$", line, re.S)
    if not m:
        return line, ""
    return m.group(1), "." + (" " + m.group(2).strip() if m.group(2) else "")


def reduce_node(node, rebuild, test, pool):
    if isinstance(node, str):
        for pat, rep in [(r"^not not ", ""), (r"^not ", ""), (r"^-(?=[a-z])", "")]:
            new = re.sub(pat, rep, node)
            if new != node and test(rebuild(new)):
                node = new
        return node
    if node[0] == "{}":
        _, pre, inner, suf = node
        for p, s in [("", suf), (pre, "")]:
            if (p, s) != (pre, suf) and test(rebuild(("{}", p, inner, s))):
                pre, suf = p, s
        inner = reduce_node(inner, lambda n: rebuild(("{}", pre, n, suf)), test, pool)
        return ("{}", pre, inner, suf)
    sep, kids = node
    kids = list(kids)
    if sep in ";|,":
        keep = ddmin(len(kids), lambda ks: test(rebuild((sep, [kids[i] for i in ks]))), pool)
        kids = [kids[i] for i in keep]
        if len(kids) == 1:
            return reduce_node(kids[0], rebuild, test, pool)
    elif sep == ":-":
        for i in range(len(kids)):
            trial = kids[:i] + [""] + kids[i + 1:]
            if test(rebuild((sep, trial))):
                kids = trial
    elif sep == ":":
        for i in range(len(kids) - 1, 0, -1):
            trial = kids[:i] + kids[i + 1:]
            if test(rebuild(trial[0] if len(trial) == 1 else (sep, trial))):
                kids = trial
        if len(kids) == 1:
            return reduce_node(kids[0], rebuild, test, pool)
    for i in range(len(kids)):
        if kids[i] != "":
            kids[i] = reduce_node(kids[i], lambda n, i=i: rebuild((sep, kids[:i] + [n] + kids[i + 1:])), test, pool)
    return (sep, kids)


def parse_aspif(line):
    t = line.split()
    if not t or not t[0].isdigit():
        return None
    if t[0] == "4":
        return {"t": 4, "name": t[2], "body": list(map(int, t[4:4 + int(t[3])])), "w": None}
    v = list(map(int, t))
    if t[0] == "1":
        h = v[2]
        st = {"t": 1, "H": v[1], "head": v[3:3 + h]}
        r = v[3 + h:]
        if r[0] == 0:
            st.update(B=0, body=r[2:2 + r[1]], w=None)
        else:
            st.update(B=1, bound=r[1], body=r[3::2][:r[2]], w=r[4::2][:r[2]])
        return st
    if t[0] == "2":
        return {"t": 2, "prio": v[1], "body": v[3::2][:v[2]], "w": v[4::2][:v[2]]}
    if t[0] == "8":
        return {"t": 8, "u": v[1], "v": v[2], "body": v[4:4 + v[3]], "w": None}
    return None


def show_aspif(st):
    b = st["body"]
    wl = [x for l, w in zip(b, st["w"]) for x in (l, w)] if st.get("w") is not None else b
    if st["t"] == 1:
        body = [0, len(b), *b] if st["B"] == 0 else [1, st["bound"], len(b), *wl]
        out = [1, st["H"], len(st["head"]), *st["head"], *body]
    elif st["t"] == 2:
        out = [2, st["prio"], len(b), *wl]
    elif st["t"] == 8:
        out = [8, st["u"], st["v"], len(b), *b]
    else:
        return " ".join(map(str, [4, len(st["name"]), st["name"], len(b), *b]))
    return " ".join(map(str, out))


def reduce_aspif(st, rebuild, test, pool):
    """Shrink the head and body lists of one aspif statement, then weight bounds."""
    def with_body(ks):
        x = dict(st, body=[st["body"][i] for i in ks])
        if st.get("w") is not None:
            x["w"] = [st["w"][i] for i in ks]
        return x
    keep = ddmin(len(st["body"]), lambda ks: test(rebuild(with_body(ks))), pool)
    st = with_body(keep)
    if st["t"] == 1:
        keep = ddmin(len(st["head"]), lambda ks: test(rebuild(dict(st, head=[st["head"][i] for i in ks]))), pool)
        st = dict(st, head=[st["head"][i] for i in keep])
        if st["B"] == 1:
            for k in sorted({1, st["bound"] // 2, st["bound"] - 1}):
                if 0 < k < st["bound"] and test(rebuild(dict(st, bound=k))):
                    st = dict(st, bound=k)
                    break
            if all(w == 1 for w in st["w"]) and st["bound"] == len(st["body"]):
                trial = dict(st, B=0, w=None)
                if test(rebuild(trial)):
                    st = trial
    return st


def main():
    args = norm(sys.argv[1:])
    jobs = 8
    if "-j" in args:
        i = args.index("-j")
        jobs = int(args[i + 1])
        args = args[:i] + args[i + 2:]
    if "--check" not in args or "--cand" not in args:
        print("Usage: ./minim.py --check FILE --task T --pipe P --kind K --cand=\"OPTS\" [--clingo BIN] [-j N]")
        sys.exit(1)
    src = get_arg(args, "--check")
    first = set_arg(args, "--cand", get_arg(args, "--cand"))
    r = subprocess.run([sys.executable, FUZZ, *first, "--no-known"], capture_output=True, text=True)
    sig = signature(r.stdout)
    if r.returncode != 1 or sig is None:
        print("Does not fail:\n" + r.stdout[-2000:])
        sys.exit(1)
    print(f"Signature: {sig}")
    ext = os.path.splitext(src)[1] or ".lp"
    oracle = Oracle(args, sig, os.path.dirname(os.path.abspath(src)), ext)
    lines = [x for x in open(src).read().splitlines() if x.strip()]
    opts = shlex.split(get_arg(args, "--cand"))

    def text(ls):
        return "\n".join(ls) + "\n"

    with ThreadPoolExecutor(jobs) as pool:
        keep = ddmin(len(opts), lambda ks: oracle(text(lines), [opts[i] for i in ks]), pool)
        opts = [opts[i] for i in keep]
        print(f"Options: {' '.join(opts) or '(none)'}  [{oracle.calls} checks]")
        keep = ddmin(len(lines), lambda ks: oracle(text([lines[i] for i in ks]), opts), pool)
        lines = [lines[i] for i in keep]
        print(f"Statements: {len(lines)}  [{oracle.calls} checks]")
        if ext == ".lp":
            for i in range(len(lines)):
                core, tail = split_stmt(lines[i])

                def rebuild(node, i=i, tail=tail):
                    return text(lines[:i] + [show(node) + tail] + lines[i + 1:])
                lines[i] = show(reduce_node(parse(core), rebuild, lambda t: oracle(t, opts), pool)) + tail
            print(f"Inside statements: done  [{oracle.calls} checks]")
        elif ext == ".aspif":
            for i in range(len(lines)):
                st = parse_aspif(lines[i])
                if st is None:
                    continue

                def rebuild(x, i=i):
                    return text(lines[:i] + [show_aspif(x)] + lines[i + 1:])
                lines[i] = show_aspif(reduce_aspif(st, rebuild, lambda t: oracle(t, opts), pool))
            print(f"Inside statements: done  [{oracle.calls} checks]")

    dst = os.path.splitext(src)[0] + "_min" + ext
    with open(dst, "w") as f:
        f.write(text(lines))
    print(f"Wrote {dst}:\n{text(lines)}", end="")
    final = set_arg(set_arg(args, "--check", dst), "--cand", " ".join(opts))
    print("Re-check: " + shlex.join([FUZZ, *final, "--no-known"]))


if __name__ == "__main__":
    main()
