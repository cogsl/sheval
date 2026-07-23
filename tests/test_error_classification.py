"""
Unit tests for how sheval tells engine failures apart (CyclesDetected,
NonStratified, Timeout, Crashed, CyclesDetectedCrashed, NonStratifiedCrashed).

The stderr fixtures below marked "real" are trimmed captures from actually
running the corresponding engine binary against test_suites/recursive_shapes
fixtures (bsep1/bsep3/nstrat1/etc.), not invented text. See
tests/test_engine_integration.py for the full end-to-end versions of the
rudof/pyshacl/shacl_s cases.

Engine-specific classification rules live on each Runner subclass's
`classify_error` method (see rudof_shacl.py, pyshacl.py, jena_shacl.py);
these tests exercise them through real runner instances rather than strings,
plus the cross-cutting logic in error_classification.py itself.
"""
from runners.command_result import CommandResult
from runners.commands import RunOutcome
from runners.error_classification import classify_error, resolve_result
from runners.error_type import ErrorType
from runners.rudof_shacl import RudofShaclRunner
from runners.rudof_shex import RudofShexRunner
from runners.pyshacl import PyshaclRunner
from runners.jena_shacl import JenaShaclRunner
from runners.shacl_tq import ShaclTqRunner
from runners.shacl_s import ShaclSRunner
from runners.jena_shex import JenaShexRunner
from runners.shex_s import ShexSRunner, analyze_shapemap_shex_s

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

RUDOF_SHEX_NON_STRATIFIED_STDERR = """\
Error: ShEx error: Failed to compile ShEx schema: Schema contains negative cycles in its dependency graph. Found 1 negative cycle(s).

Caused by:
    Failed to compile ShEx schema: Schema contains negative cycles in its dependency graph. Found 1 negative cycle(s).
"""

SHEX_S_NEGATIVE_CYCLES_STDERR = """\
Schema is NOT well formed: Negative cycles: (IRILabel(<http://example.org/S>),IRILabel(<http://example.org/S>))
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
    assert classify_error(RudofShaclRunner(), CommandResult.OK, 1, RUDOF_CYCLES_STDERR) == ErrorType.CYCLES_DETECTED


def test_rudof_non_stratified():
    assert classify_error(RudofShaclRunner(), CommandResult.OK, 1, RUDOF_NON_STRATIFIED_STDERR) == ErrorType.NON_STRATIFIED


# --- pyshacl: crashes on positive (non-negated) mutual recursion -------

def test_pyshacl_cycles_detected_crashed():
    assert classify_error(PyshaclRunner(), CommandResult.OK, 2, PYSHACL_PATH_TOO_DEEP_STDERR) == ErrorType.CYCLES_DETECTED_CRASHED


def test_pyshacl_graceful_recursion_backoff_is_not_a_crash():
    # pyshacl's normal recursion handling: warns and backs out, exit 0. The
    # top-level classify_error() (used on the run-failed path) always calls
    # the runner with conforms=None, so it can't classify this as
    # Conformant/NonConformant -- that only happens via resolve_result()
    # below, once the real 'conforms' value from the report is known.
    assert classify_error(PyshaclRunner(), CommandResult.OK, 0, PYSHACL_BACKING_OUT_STDERR) is None


# --- jena_shacl: warns and continues, never observed to crash ----------

def test_jena_shacl_cycle_warning_is_not_an_error():
    assert classify_error(JenaShaclRunner(), CommandResult.OK, 0, JENA_SHACL_CYCLE_WARN_STDERR) is None


# --- shacl_tq: degrades per-constraint, never observed to crash --------

def test_shacl_tq_unsupported_recursion_is_not_an_error():
    # Exit code 1 here is shacl_tq's own "did not conform" convention, not a crash.
    assert classify_error(ShaclTqRunner(), CommandResult.OK, 1, SHACL_TQ_UNSUPPORTED_RECURSION_STDERR) is None


# --- shacl_s: hangs (no distinctive stderr) instead of crashing --------

def test_shacl_s_hang_is_classified_as_timeout():
    assert classify_error(ShaclSRunner(), CommandResult.TIMEOUT, None, "") == ErrorType.TIMEOUT


# --- jena_shex / shex_s / rudof-shex: no crashes observed --------------

def test_jena_shex_normal_run_is_not_an_error():
    assert classify_error(JenaShexRunner(), CommandResult.OK, 0, "") is None


def test_shex_s_normal_run_is_not_an_error():
    assert classify_error(ShexSRunner(), CommandResult.OK, 0, "") is None


def test_shex_s_negative_cycles():
    # shex_s refuses to compile a schema with a negative cycle in its
    # dependency graph (see test_suites/recursive_shapes/ShEx/nostratnocycle.shex).
    # classify_error itself is text-agnostic about where the message came
    # from; in the real run this text lands on stdout, not stderr -- see
    # test_shex_s_negative_cycles_via_stdout_output_file below for that path.
    assert classify_error(ShexSRunner(), CommandResult.OK, 1, SHEX_S_NEGATIVE_CYCLES_STDERR) == ErrorType.NON_STRATIFIED


def test_shex_s_negative_cycles_via_stdout_output_file(tmp_path):
    # shex_s actually prints the negative-cycles message to STDOUT and exits 0
    # -- `run()` redirects that stdout straight into the result file, so
    # `execute()` reads the file back and passes it to `resolve_result` as
    # `stdout`, which feeds it to classify_error alongside stderr. This
    # reproduces that real flow end to end.
    output_file = tmp_path / "output.json"
    output_file.write_text(SHEX_S_NEGATIVE_CYCLES_STDERR)

    outcome = RunOutcome(status=CommandResult.OK, stderr="", returncode=0)
    result = resolve_result(
        ShexSRunner(), outcome,
        lambda: analyze_shapemap_shex_s(str(output_file), [], [], []),
        output_file.read_text(),
    )

    assert result['conforms'] is False
    assert result['error_type'] == ErrorType.NON_STRATIFIED.value


def test_rudof_shex_normal_run_is_not_an_error():
    assert classify_error(RudofShexRunner(), CommandResult.OK, 0, "") is None


def test_rudof_shex_recursion_is_not_an_error():
    # Unlike its SHACL validator, rudof's ShEx validator handles recursive
    # shapes fine, so it doesn't recognize the SHACL "dependency graph" text.
    assert classify_error(RudofShexRunner(), CommandResult.OK, 1, RUDOF_CYCLES_STDERR) is None


def test_rudof_shex_non_stratified():
    # Unlike ordinary recursion, non-stratified negation fails schema
    # compilation entirely -- no output file, distinct stderr wording from
    # the SHACL validator's "Dependency graph has negative cycles ...".
    assert classify_error(RudofShexRunner(), CommandResult.OK, 1, RUDOF_SHEX_NON_STRATIFIED_STDERR) == ErrorType.NON_STRATIFIED


# --- cross-cutting behavior ---------------------------------------------

def test_timeout_is_universal_regardless_of_technology():
    runners = [RudofShaclRunner(), PyshaclRunner(), JenaShaclRunner(), JenaShexRunner(), ShaclSRunner(), ShaclTqRunner(), ShexSRunner()]
    for runner in runners:
        assert classify_error(runner, CommandResult.TIMEOUT, None, "") == ErrorType.TIMEOUT


def test_generic_crash_fallback_stack_overflow():
    # Not reproduced against any active engine in this suite, but any JVM-based
    # engine (jena_shacl, jena_shex, shacl_s, shex_s) could in principle overflow
    # its stack on sufficiently deep/pathological input.
    stderr = 'Exception in thread "main" java.lang.StackOverflowError\n\tat org.apache.jena.shacl...\n'
    assert classify_error(JenaShaclRunner(), CommandResult.OK, 1, stderr) == ErrorType.CRASHED


def test_generic_crash_fallback_killed_by_signal():
    assert classify_error(ShexSRunner(), CommandResult.OK, -11, "") == ErrorType.CRASHED


def test_non_stratified_crashed_is_defined_but_has_no_detection_rule():
    # Not reproduced against any active engine (see error_classification.py
    # module docstring: pyshacl's negation handling specifically avoids the
    # crash that a purely positive cycle triggers). Kept for forward
    # compatibility, not wired to a pattern yet.
    assert ErrorType.NON_STRATIFIED_CRASHED.value == "NonStratifiedCrashed"
    # merely mentioning non-stratification, with no crash signature, must not
    # be misclassified as a crash of any kind
    assert classify_error(PyshaclRunner(), CommandResult.OK, 0, "non-stratified") is None


# --- resolve_result: wiring classification into a runner's result dict --

def test_resolve_result_uses_analysis_when_run_succeeds():
    outcome = RunOutcome(status=CommandResult.OK, stderr="", returncode=0)
    result = resolve_result(PyshaclRunner(), outcome, lambda: {'conforms': True, 'failures': []})
    assert result == {'conforms': True, 'failures': []}


def test_resolve_result_falls_back_to_analysis_on_nonzero_exit_without_known_crash():
    # pyshacl/shacl_tq use a nonzero exit code to mean "ran fine, did not conform"
    outcome = RunOutcome(status=CommandResult.OK, stderr="", returncode=1)
    result = resolve_result(PyshaclRunner(), outcome, lambda: {'conforms': False, 'failures': [{'node': ':a'}]})
    assert result == {'conforms': False, 'failures': [{'node': ':a'}]}


def test_resolve_result_classifies_known_crash_without_calling_analyze():
    outcome = RunOutcome(status=CommandResult.OK, stderr=PYSHACL_PATH_TOO_DEEP_STDERR, returncode=2)

    def analyze():
        raise AssertionError("analyze() should not be called once a crash is classified")

    result = resolve_result(PyshaclRunner(), outcome, analyze)
    assert result['conforms'] is None
    assert result['error_type'] == ErrorType.CYCLES_DETECTED_CRASHED.value


def test_resolve_result_timeout_skips_analysis():
    outcome = RunOutcome(status=CommandResult.TIMEOUT, stderr="", returncode=None)

    def analyze():
        raise AssertionError("analyze() should not be called on timeout")

    result = resolve_result(ShaclSRunner(), outcome, analyze)
    assert result['error_type'] == ErrorType.TIMEOUT.value


def test_resolve_result_jena_shacl_cycle_warning_conformant():
    # jena_shacl exits 0 and produces a real report even after warning about
    # cycles (see bsep1/bsep3) -- conforms is kept, but flagged as suspect.
    outcome = RunOutcome(status=CommandResult.OK, stderr=JENA_SHACL_CYCLE_WARN_STDERR, returncode=0)
    result = resolve_result(JenaShaclRunner(), outcome, lambda: {'conforms': True, 'failures': []})
    assert result['conforms'] is True
    assert result['error_type'] == ErrorType.CYCLES_DETECTED_CONFORMANT.value


def test_resolve_result_jena_shacl_cycle_warning_non_conformant():
    outcome = RunOutcome(status=CommandResult.OK, stderr=JENA_SHACL_CYCLE_WARN_STDERR, returncode=0)
    result = resolve_result(JenaShaclRunner(), outcome, lambda: {'conforms': False, 'failures': [{'node': ':a'}]})
    assert result['conforms'] is False
    assert result['error_type'] == ErrorType.CYCLES_DETECTED_NON_CONFORMANT.value


def test_resolve_result_pyshacl_recursion_warning_conformant():
    # pyshacl exits 0 and produces a real report even after warning about
    # recursion (see bsep1/bsep2) -- conforms is kept, but flagged as suspect,
    # same as jena_shacl's cycle warning above.
    outcome = RunOutcome(status=CommandResult.OK, stderr=PYSHACL_BACKING_OUT_STDERR, returncode=0)
    result = resolve_result(PyshaclRunner(), outcome, lambda: {'conforms': True, 'failures': []})
    assert result['conforms'] is True
    assert result['error_type'] == ErrorType.CYCLES_DETECTED_CONFORMANT.value


def test_resolve_result_pyshacl_recursion_warning_non_conformant():
    outcome = RunOutcome(status=CommandResult.OK, stderr=PYSHACL_BACKING_OUT_STDERR, returncode=0)
    result = resolve_result(PyshaclRunner(), outcome, lambda: {'conforms': False, 'failures': [{'node': ':a'}]})
    assert result['conforms'] is False
    assert result['error_type'] == ErrorType.CYCLES_DETECTED_NON_CONFORMANT.value


def test_resolve_result_jena_shacl_no_cycle_warning_is_untouched():
    outcome = RunOutcome(status=CommandResult.OK, stderr="", returncode=0)
    result = resolve_result(JenaShaclRunner(), outcome, lambda: {'conforms': True, 'failures': []})
    assert result == {'conforms': True, 'failures': []}


def test_resolve_result_unclassified_exception_keeps_conforms_none_and_error_type_none():
    outcome = RunOutcome(status=CommandResult.EXCEPTION, stderr="", returncode=None)

    def analyze():
        raise AssertionError("analyze() should not be called on an unclassified exception")

    result = resolve_result(PyshaclRunner(), outcome, analyze)
    assert result['conforms'] is None
    assert result['error_type'] is None
