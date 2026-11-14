#!/usr/bin/env python3
"""PR-04: do the N tests have teeth? Each check of scripts/object_model.py / quality_gate.py is removed on a
SCRATCH COPY (the repository is not touched); the test that guards it must then FAIL. A test that stays green
when its check is gone proves nothing. Usage: teeth.py <repo> <python> <workdir>"""
import re, shutil, subprocess, sys
repo, py, work = sys.argv[1:4]
DEFECTS = [
 ("N1  id collision check removed", "scripts/object_model.py", "if oid in seen_ids:", "if False:", "test_n1_two_different_objects_with_the_same_id_are_rejected"),
 ("N4  digest check removed", "scripts/object_model.py", 'if rec.get("digest") != canonical_digest(', 'if False and rec.get("digest") != canonical_digest(', "test_n4_a_changed_record_is_rejected"),
 ("N4  summary recount removed", "scripts/object_model.py", 'if rec.get("summary") != summarize(objs):', "if False:", "test_n4_a_changed_record_is_rejected"),
 ("N5  tool-version check removed (build)", "scripts/object_model.py", 'if not ver or str(ver).lower() in ("unknown", "none", ""):', "if False:", "test_n5_an_unknown_tool_version_makes_the_record_unusable"),
 ("N6  coverage-kind enum check removed", "scripts/object_model.py", 'and v.get("kind") not in COVERAGE_KINDS', "and False", "test_n6_a_coverage_kind_that_is_not_measured_cannot_be_branch"),
 ("N8  unclassified file silently accepted", "scripts/object_model.py", "cls, rule = classify(scope, lang, f)", 'try:\n            cls, rule = classify(scope, lang, f)\n        except ModelError:\n            cls, rule = "production", {}', "test_n8_a_file_the_scope_does_not_classify_is_an_error"),
 ("N9  repeat comparison removed", "scripts/object_model.py", "if len(seen) > 1:", "if False:", "test_n9_an_object_whose_coverage_differs_between_runs_is_nondeterministic"),
 ("N10 ambiguous mutant resolved by guessing", "scripts/object_model.py", "if len(cand) > 1:", "if False:", "test_a_mutant_that_fits_two_objects_is_ambiguous_not_guessed"),
 ("N11 partial block attributed anyway", "scripts/object_model.py", "elif touching:  # cuts an object, or lies in several", "elif False:", "test_n11_a_block_that_cuts_an_object_is_not_attributed_and_no_value_is_made_up"),
 ("N12 zero denominator becomes a number", "scripts/quality_gate.py", "evaluable = caught + missed\n", "evaluable = caught + missed or 1\n", "test_zero_denominator_is_neither_100_nor_0"),
 ("N13 L2 input digest check removed", "scripts/object_model.py", 'if digest != want["sha256"] or size != want["bytes"]:', "if False:", "test_n13_l2_is_not_checked_without_inputs_and_fails_on_a_changed_input"),
 ("N13 L3 independent count removed", "scripts/object_model.py", "if have != want:", "if False:", "test_n13_a_consistently_forged_record_passes_l1_but_not_l3"),
]
def run(root, k):
    r = subprocess.run([py, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--no-cov", "-k", k, "tests/test_tools/test_object_model.py", "tests/test_tools/test_mutation_policy.py"], cwd=root, capture_output=True, text=True)
    last = [l for l in r.stdout.splitlines() if re.search(r"\d+ (passed|failed)", l)]
    return r.returncode, (last[-1].strip(" =") if last else r.stdout[-200:])
bad = 0
for label, rel, old, new, test in DEFECTS:
    root = f"{work}/t"; shutil.rmtree(root, ignore_errors=True)
    shutil.copytree(repo, root, ignore=shutil.ignore_patterns(".git", "__pycache__", "target", "node_modules"))
    p = f"{root}/{rel}"; s = open(p).read()
    assert s.count(old) == 1, f"{label}: anchor not found exactly once ({s.count(old)})"
    base_rc, base = run(root, test)
    open(p, "w").write(s.replace(old, new))
    rc, line = run(root, test)
    ok = base_rc == 0 and rc != 0
    bad += not ok
    print(f"{'OK  ' if ok else 'FAIL'} {label:<44} unmodified: [{base}]  check removed: [{line}]")
print("ALL N-TESTS HAVE TEETH" if not bad else f"{bad} TEST(S) STAY GREEN WITHOUT THEIR CHECK")
sys.exit(1 if bad else 0)
