"""
Unit tests for how sheval tells engine failures apart (CyclesDetected,
NonStratified, Timeout, Crashed, CyclesDetectedCrashed, NonStratifiedCrashed).

The stderr fixtures below marked "real" are trimmed captures from actually
running the corresponding engine binary against test_suites/recursive_shapes
fixtures (bsep1/bsep3/nstrat1/etc.), not invented text. See
tests/test_engine_integration.py for the full end-to-end versions of the
rudof/pyshacl/shacl_s cases.
"""
from runners.command_result import CommandResult
from runners.commands import RunOutcome
from runners.error_classification import classify_error, resolve_result
from runners.error_type import ErrorType

# --- real captures -----------------------------------------------------

RUDOF_CYCLES_STDERR = """\
 WARN shacl/src/ir/schema.rs:220: The dependency graph has cycles. This is known as a recursive schema and the SHACL semantics for these schemas is implementation dependent
 WARN shacl/src/ir/schema.rs:223: More information about recursive schemas can be found at https://www.w3.org/TR/shacl/#shapes-recursion
Error: SHACL error: Failed to parse SHACL schema from 'loaded RDF data' with format 'loaded RDF data format': Dependency graph has cycles: [[Iri {IriS { iri: NamedNode { iri: "http://example.org/S" } }}, Bnode{"b07249148e043da91cf02c0620d377"}]]
"""

RUDOF_NON_STRATIFIED_STDERR = """\
 WARN shacl/src/ir/schema.rs:245: Warning: The dependency graph has negative cycles. This may lead to unexpected behavior in SHACL validation due to non-stratified negation
Error: SHACL error: Failed to parse SHACL schema from 'loaded RDF data' with format 'loaded RDF data format': Dependency graph has negative cycles (non-stratified): [[Iri {IriS { iri: NamedNode { iri: "http://example.org/S" } }}, Bnode{"a42019d496c909c7a186d3bb620a11a1"}]]
"""

PYSHACL_PATH_TOO_DEEP_STDERR = """\
Validator encountered a Runtime Error:
Validation path too deep!
<NodeShape http://example.org/S> -> <AndConstraintComponent on <NodeShape http://example.org/S>> -> <NodeShape http://example.org/S1> -> <AndConstraintComponent on <NodeShape http://example.org/S1>> -> <NodeShape http://example.org/S>
If you believe this is a bug in pyshacl, open an Issue on the pyshacl github page.
"""

PYSHACL_BACKING_OUT_STDERR = """\
.../pyshacl/constraints/core/shape_based_constraints.py:113: ShapeRecursionWarning: Warning, A Recursive Shape was detected executing a recursive validation sequence 6 levels deep. Backing out.
For reference, see https://www.w3.org/TR/shacl/#shapes-recursion
"""

JENA_SHACL_CYCLE_WARN_STDERR = (
    "WARN  SHACL           :: Cycle detected : node <http://example.org/S>\n"
    "WARN  SHACL           :: Cycle[<http://example.org/a>]\n"
)

SHACL_TQ_UNSUPPORTED_RECURSION_STDERR = (
    "ERROR FailureLog :: SHACL Failure: Unsupported recursion\n"
    "ERROR FailureLog :: SHACL Failure: Constraint AndConstraintComponent at :S has produced a failure for focus node :b\n"
)


# --- rudof: the only engine observed to stop cleanly on detection ------

def test_rudof_cycles_detected():
    assert classify_error("rudof", CommandResult.OK, 1, RUDOF_CYCLES_STDERR) == ErrorType.CYCLES_DETECTED


def test_rudof_non_stratified():
    assert classify_error("rudof", CommandResult.OK, 1, RUDOF_NON_STRATIFIED_STDERR) == ErrorType.NON_STRATIFIED


# --- pyshacl: crashes on positive (non-negated) mutual recursion -------

def test_pyshacl_cycles_detected_crashed():
    assert classify_error("pyshacl", CommandResult.OK, 2, PYSHACL_PATH_TOO_DEEP_STDERR) == ErrorType.CYCLES_DETECTED_CRASHED


def test_pyshacl_graceful_recursion_backoff_is_not_an_error():
    # pyshacl's normal recursion handling: warns and backs out, exit 0.
    # This is a successful run, not one of our error categories.
    assert classify_error("pyshacl", CommandResult.OK, 0, PYSHACL_BACKING_OUT_STDERR) is None


# --- jena_shacl: warns and continues, never observed to crash ----------

def test_jena_shacl_cycle_warning_is_not_an_error():
    assert classify_error("jena_shacl", CommandResult.OK, 0, JENA_SHACL_CYCLE_WARN_STDERR) is None


# --- shacl_tq: degrades per-constraint, never observed to crash --------

def test_shacl_tq_unsupported_recursion_is_not_an_error():
    # Exit code 1 here is shacl_tq's own "did not conform" convention, not a crash.
    assert classify_error("shacl_tq", CommandResult.OK, 1, SHACL_TQ_UNSUPPORTED_RECURSION_STDERR) is None


# --- shacl_s: hangs (no distinctive stderr) instead of crashing --------

def test_shacl_s_hang_is_classified_as_timeout():
    assert classify_error("shacl_s", CommandResult.TIMEOUT, None, "") == ErrorType.TIMEOUT


# --- jena_shex / shex_s / rudof-shex: no crashes observed --------------

def test_jena_shex_normal_run_is_not_an_error():
    assert classify_error("jena_shex", CommandResult.OK, 0, "") is None


def test_shex_s_normal_run_is_not_an_error():
    assert classify_error("shex_s", CommandResult.OK, 0, "") is None


def test_rudof_shex_normal_run_is_not_an_error():
    assert classify_error("rudof", CommandResult.OK, 0, "") is None


# --- cross-cutting behavior ---------------------------------------------

def test_timeout_is_universal_regardless_of_technology():
    for technology in ("rudof", "pyshacl", "jena_shacl", "jena_shex", "shacl_s", "shacl_tq", "shex_s"):
        assert classify_error(technology, CommandResult.TIMEOUT, None, "") == ErrorType.TIMEOUT


def test_generic_crash_fallback_stack_overflow():
    # Not reproduced against any active engine in this suite, but any JVM-based
    # engine (jena_shacl, jena_shex, shacl_s, shex_s) could in principle overflow
    # its stack on sufficiently deep/pathological input.
    stderr = 'Exception in thread "main" java.lang.StackOverflowError\n\tat org.apache.jena.shacl...\n'
    assert classify_error("jena_shacl", CommandResult.OK, 1, stderr) == ErrorType.CRASHED


def test_generic_crash_fallback_killed_by_signal():
    assert classify_error("shex_s", CommandResult.OK, -11, "") == ErrorType.CRASHED


def test_non_stratified_crashed_is_defined_but_has_no_detection_rule():
    # Not reproduced against any active engine (see error_classification.py
    # module docstring: pyshacl's negation handling specifically avoids the
    # crash that a purely positive cycle triggers). Kept for forward
    # compatibility, not wired to a pattern yet.
    assert ErrorType.NON_STRATIFIED_CRASHED.value == "NonStratifiedCrashed"
    # merely mentioning non-stratification, with no crash signature, must not
    # be misclassified as a crash of any kind
    assert classify_error("pyshacl", CommandResult.OK, 0, "non-stratified") is None


# --- resolve_result: wiring classification into a runner's result dict --

def test_resolve_result_uses_analysis_when_run_succeeds():
    outcome = RunOutcome(status=CommandResult.OK, stderr="", returncode=0)
    result = resolve_result("pyshacl", outcome, lambda: {'conforms': True, 'failures': []})
    assert result == {'conforms': True, 'failures': []}


def test_resolve_result_falls_back_to_analysis_on_nonzero_exit_without_known_crash():
    # pyshacl/shacl_tq use a nonzero exit code to mean "ran fine, did not conform"
    outcome = RunOutcome(status=CommandResult.OK, stderr="", returncode=1)
    result = resolve_result("pyshacl", outcome, lambda: {'conforms': False, 'failures': [{'node': ':a'}]})
    assert result == {'conforms': False, 'failures': [{'node': ':a'}]}


def test_resolve_result_classifies_known_crash_without_calling_analyze():
    outcome = RunOutcome(status=CommandResult.OK, stderr=PYSHACL_PATH_TOO_DEEP_STDERR, returncode=2)

    def analyze():
        raise AssertionError("analyze() should not be called once a crash is classified")

    result = resolve_result("pyshacl", outcome, analyze)
    assert result['conforms'] is None
    assert result['error_type'] == ErrorType.CYCLES_DETECTED_CRASHED.value


def test_resolve_result_timeout_skips_analysis():
    outcome = RunOutcome(status=CommandResult.TIMEOUT, stderr="", returncode=None)

    def analyze():
        raise AssertionError("analyze() should not be called on timeout")

    result = resolve_result("shacl_s", outcome, analyze)
    assert result['error_type'] == ErrorType.TIMEOUT.value


def test_resolve_result_jena_shacl_cycle_warning_conformant():
    # jena_shacl exits 0 and produces a real report even after warning about
    # cycles (see bsep1/bsep3) -- conforms is kept, but flagged as suspect.
    outcome = RunOutcome(status=CommandResult.OK, stderr=JENA_SHACL_CYCLE_WARN_STDERR, returncode=0)
    result = resolve_result("jena_shacl", outcome, lambda: {'conforms': True, 'failures': []})
    assert result['conforms'] is True
    assert result['error_type'] == ErrorType.CYCLES_DETECTED_CONFORMANT.value


def test_resolve_result_jena_shacl_cycle_warning_non_conformant():
    outcome = RunOutcome(status=CommandResult.OK, stderr=JENA_SHACL_CYCLE_WARN_STDERR, returncode=0)
    result = resolve_result("jena_shacl", outcome, lambda: {'conforms': False, 'failures': [{'node': ':a'}]})
    assert result['conforms'] is False
    assert result['error_type'] == ErrorType.CYCLES_DETECTED_NON_CONFORMANT.value


def test_resolve_result_jena_shacl_no_cycle_warning_is_untouched():
    outcome = RunOutcome(status=CommandResult.OK, stderr="", returncode=0)
    result = resolve_result("jena_shacl", outcome, lambda: {'conforms': True, 'failures': []})
    assert result == {'conforms': True, 'failures': []}


def test_resolve_result_unclassified_exception_keeps_conforms_none_and_error_type_none():
    outcome = RunOutcome(status=CommandResult.EXCEPTION, stderr="", returncode=None)

    def analyze():
        raise AssertionError("analyze() should not be called on an unclassified exception")

    result = resolve_result("pyshacl", outcome, analyze)
    assert result['conforms'] is None
    assert result['error_type'] is None
