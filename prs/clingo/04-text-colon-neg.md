# Fix text output of conditions starting with classical negation

Conditions are printed directly after a colon, so a classically negated first literal produces `:-`, which doesn't parse back. The same happens for aggregate elements, conditional literals, `#heuristic`, `#edge`, and `#minimize`.

```
$ clingo --text in.lp | clingo
```
`in.lp`:
```
{a;-b}.
#show s : -b.
```
Before: `--text` prints `#show s:-b.`; reading it back fails with `syntax error, unexpected :-`.  
After: `#show s: -b.`, which reads back fine.

Insert a space after the colon in this case (`printColon()` helper); other output is unchanged. Found by differential fuzzing.
