#!/usr/bin/env python3
# Minimize an aspif file w.r.t. an arbitrary command. Usage: ./minim_aspif.py FILE REGEX CMD... ({} is the file)
# A candidate fails if REGEX matches the command's stdout+stderr; writes FILE with _min before the extension.

import importlib.util
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.realpath(__file__))
spec = importlib.util.spec_from_file_location("minim", os.path.join(HERE, "minim.py"))
minim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(minim)


def main():
    if len(sys.argv) < 4 or "{}" not in sys.argv[3:]:
        print("Usage: ./minim_aspif.py FILE REGEX CMD... ({} is the file)")
        sys.exit(1)
    src, pat, cmd = sys.argv[1], re.compile(sys.argv[2]), sys.argv[3:]
    tmpdir = os.path.dirname(os.path.abspath(src))
    cache = {}

    def fails(text):
        if text not in cache:
            fd, path = tempfile.mkstemp(suffix=".aspif", dir=tmpdir)
            with os.fdopen(fd, "w") as f:
                f.write(text)
            try:
                r = subprocess.run([path if x == "{}" else x for x in cmd], capture_output=True, text=True, timeout=60)
                cache[text] = bool(pat.search(r.stdout + r.stderr))
            except subprocess.TimeoutExpired:
                cache[text] = False
            os.unlink(path)
        return cache[text]

    def text(ls):
        return "\n".join(ls) + "\n"

    lines = [x for x in open(src).read().splitlines() if x.strip()]
    if not fails(text(lines)):
        print("Does not fail")
        sys.exit(1)
    with ThreadPoolExecutor(os.cpu_count()) as pool:
        keep = minim.ddmin(len(lines), lambda ks: fails(text([lines[i] for i in ks])), pool)
        lines = [lines[i] for i in keep]
        for i in range(len(lines)):
            st = minim.parse_aspif(lines[i])
            if st is not None:
                lines[i] = minim.show_aspif(minim.reduce_aspif(
                    st, lambda x, i=i: text(lines[:i] + [minim.show_aspif(x)] + lines[i + 1:]), fails, pool))
    dst = os.path.splitext(src)[0] + "_min" + os.path.splitext(src)[1]
    with open(dst, "w") as f:
        f.write(text(lines))
    print(f"Wrote {dst} ({len(lines)} lines, {len(cache)} checks)")


if __name__ == "__main__":
    main()
