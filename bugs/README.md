Minimized reproducers of fixed bugs; the first line of each `.lp` is the failing command.
`notabug_*` are inconsistencies that are by design (see Known non-bugs in ../README.md).
`dup_models_*.aspif`: `clasp --eq=0 -n0` reports twice as many models as there are.
`unfounded_merged_body_lits.aspif`: `clasp -n0` reports an extra answer set with atom 1 and 5 (5 is unfounded).
`disj_removed_support_backprop.aspif`: `clasp --backprop` fails an assertion.
`vmtf_activity_shift.aspif`: `clasp --heuristic=vmtf -n0` on the UBSan build reports an undefined shift.
`disj_superfluous_weight_body.aspif`: `clasp --trans-ext=no -n0` reports the non-model {7}.
`usc_lookahead_eroot.aspif`: `clingo -n0 --opt-mode=optN --opt-strategy=usc --lookahead=atom` claims optimum `0 7 0`, but `0 7 -3` exists.
`unfounded_eq_atom_merge.aspif`: `clasp --eq=2 -n0` reports 3 answer sets instead of 2 (one has the unfounded loop 9, 15).
`superfluous_head_lost_model.aspif`: `clasp --trans-ext=no -n0` reports 2 answer sets instead of 3 (fixed upstream, #124).
`superfluous_head_integ.lp`: `clingo --trans-ext=integ -n0` reports 1 answer set instead of 2 (same cause).
`disj_eq_atom_backprop.aspif`: `clasp --backprop` fails an assertion (remaining disjunction atom merged into an eq atom).
`removed_disj_head_eq0.aspif`: `clasp --eq=0` fails `n < size()` in `LogicProgram::getDisj()` (dangling head edge to a removed disjunction).
`usc_tag_conflict.aspif`: `clasp --partial-check=10,2 --lookahead=atom --opt-strategy=usc -n0 --opt-mode=optN` fails with "You must not mess with my root level!" instead of UNSATISFIABLE.
`upper_head_iter_backprop.aspif`: `clasp --backprop` fails `n < size()` in `LogicProgram::getAtom()` (invalid head iterator in `addHeadsToUpper()`).
`split_optn_sync.aspif`: `clasp -n0 --opt-mode=optN -t8,split` sometimes (about 2% of runs) reports the optimum but no optimal models (race in `ParallelSolve::requestWork()`).
`dup_models_false_body_var.aspif`: `clasp -n0` reports 4 models instead of 2 (each answer set twice; unconstrained var of a body derived false during eq-preprocessing).
`transform_eq_body.aspif`: `clasp --trans-ext=choice` fails `relevant() && h->relevant()` in `PrgBody::addHead()` (rule transformation used a merged body).
`transform_choice_head_scc.lp`: `clingo --trans-ext=scc -n0` reports 2 answer sets instead of 3 (choice head turned into a normal head when transforming a recursive sum rule).
`transform_integrity_scc.aspif`: `clasp --trans-ext=scc` fails `pos < size` in `Span::operator[]` (transformed rule h :- not h has no head after simplification).
`usc_bound_overflow.aspif`: `clasp -n0 --opt-strategy=usc` never terminates (overflow of upper_ - lower_ with a negative lower bound; UBSan reports it).
`empty_choice_transform.aspif`: `clasp --trans-ext=choice` (or `all`) never terminates on the empty choice rule `{}.`.
`sum_opposite_goals_nolookback.lp`: `clingo -n0 --no-lookback` reports 2 answer sets instead of 3 (opposite subgoals of a sum body merged).
`vmtf_single_element_inc.aspif`: `clasp -n0 --heuristic=vmtf` fails `!score_[v].inList()` in `ClaspVmtf::addToList()` (incremental; single-element list after step 1).
`assumption_aux_atom.aspif`: `clasp -n0 --trans-ext=all` reports 1 answer set instead of 2 (assumed atom reused as aux atom of the transformed choice rule).
