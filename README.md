# Fuzzer for clingo

Differential fuzzer: `gen.py` (after [FuzzASP](https://fmv.jku.at/fuzzasp/)) generates random ground programs in
gringo 5 syntax; `fuzz.py` solves each with a reference configuration (clasp preprocessing off:
`--eq=0 --no-backprop --trans-ext=no --sat-prepro=no`) and with random option sets, through different
pipelines (direct, `--mode=gringo` aspif, `--text`, `--output=reify` + `meta.lp`), and compares answer sets,
optima, optimal models, brave/cautious consequences, projections, and crashes/sanitizer reports.
A candidate that times out although the reference was fast is re-run with a 12x timeout and reported as a hang.

## Build

```bash
cmake -S.. -B../build/rel -DCMAKE_BUILD_TYPE=Release "-DCMAKE_CXX_FLAGS_RELEASE=-O2 -g" \
  -DCLINGO_BUILD_WITH_PYTHON=OFF -DCLINGO_BUILD_WITH_LUA=OFF -DCLINGO_BUILD_STATIC=ON
cmake -S.. -B../build/asan -DCMAKE_BUILD_TYPE=Debug \
  "-DCMAKE_CXX_FLAGS=-fsanitize=address,undefined -fno-omit-frame-pointer" \
  "-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address,undefined" \
  -DCLINGO_BUILD_WITH_PYTHON=OFF -DCLINGO_BUILD_WITH_LUA=OFF -DCLINGO_BUILD_STATIC=ON
cmake --build ../build/rel -j$(nproc) && cmake --build ../build/asan -j$(nproc)
```

The release build keeps asserts on (no `-DNDEBUG`).

## Run

```bash
./fuzz.py [--task enum|opt|proj] [--size small|normal|big] [--tout 5] [--keep-going]
./fuzz_session.sh [--num N] [fuzz.py options]   # one instance per physical core in tmux, a third on --size big
```

On a bug, `fuzz.py` prints a `fuzz.py --check ...` line that reruns just the reference and the failing run;
`./minim.py` takes the same arguments and writes `<file>_min.lp` (or `.aspif`): it drops options, statements, and
parts of statements (body/head literals, aggregate elements, weights and bounds).

Minimized reproducers of bugs found so far are in `bugs/`.

## Known non-bugs

The fuzzer avoids these, as they are by design or unspecified:
- Conflicting `#external` declarations for one atom: gringo emits independent statements in reverse source order and
  clasp lets the last one win, so the first declaration wins; `--text` output read back gives the other one.
  The generator declares each external atom only once.
- An external atom stays external unless a rule for it survives grounding, so for
  `bugs/notabug_text_external_rule.lp` its `--text` output (where gringo can drop the rule on reading it back) has
  other answer sets. The text pipeline is skipped for programs with `#external`.
