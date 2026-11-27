Minimized reproducers of fixed bugs; the first line of each `.lp` is the failing command.
`open_*` are inconsistencies that were not fixed (unclear intended semantics).
`dup_models_*.aspif`: `clasp --eq=0 -n0` reports twice as many models as there are.
`unfounded_merged_body_lits.aspif`: `clasp -n0` reports an extra answer set with atom 1 and 5 (5 is unfounded).
`disj_removed_support_backprop.aspif`: `clasp --backprop` fails an assertion.
`vmtf_activity_shift.aspif`: `clasp --heuristic=vmtf -n0` on the UBSan build reports an undefined shift.
`disj_superfluous_weight_body.aspif`: `clasp --trans-ext=no -n0` reports the non-model {7}.
`open_usc_lookahead_optN.aspif`: `clingo -n0 --opt-mode=optN --opt-strategy=usc --lookahead=atom` claims optimum `0 7 0`, but `0 7 -3` exists (also in the original clasp; not fixed yet).
