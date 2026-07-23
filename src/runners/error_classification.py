"""
Classifies why a validation engine's run did not produce a usable result.

Each engine reports cycle detection / non-stratified negation / crashes in its
own way (different processes, different runtimes), so the recognized patterns
live as a `classify_error` method on the corresponding Runner subclass (see
e.g. RudofShaclRunner, PyshaclRunner, JenaShaclRunner) rather than here. This
module only holds the cross-cutting logic that applies regardless of engine:
timeouts, generic runtime crash signatures, and the overall control flow that
decides when to call an engine's own classifier versus just parsing its
output.

The per-engine rules were derived by actually running the engines against
test_suites/recursive_shapes fixtures, not guessed:

- rudof (SHACL): aborts cleanly, no report written, and prints one of
  "Dependency graph has cycles: [...]" or
  "Dependency graph has negative cycles (non-stratified): [...]" to stderr.
- rudof (ShEx): handles ordinary recursive schemas fine (see bsep1_shex), but
  on non-stratified negation (see nstrat1_shex/nstrat2_shex) it fails to
  compile the schema at all and prints "Schema contains negative cycles in
  its dependency graph. Found N negative cycle(s)." to stderr instead of
  writing a result file.
- pyshacl: on mutually recursive sh:and shapes (see bsep3), it walks the
  recursive validation path, exceeds its own internal depth guard, and raises
  "Validator encountered a Runtime Error:\\nValidation path too deep!" instead
  of the graceful "ShapeRecursionWarning ... Backing out." it uses for
  simpler recursion (see bsep1/bsep2). That graceful case is not a crash --
  it exits 0 with a full report -- but the warning means the verdict isn't
  guaranteed correct, so it's classified as
  CyclesDetectedConformant/CyclesDetectedNonConformant the same way as
  jena_shacl's cycle warning below, rather than trusted outright.
- jena_shacl: on cyclic shapes (see bsep1, bsep3), it prints "Cycle detected"
  warnings to stderr but keeps going and exits 0 with a full validation
  report, unlike rudof (which aborts) or pyshacl (which can crash on the
  mutually-recursive case). Since the report was produced despite the
  warning, its 'conforms' value is kept and classified as
  CyclesDetectedConformant/CyclesDetectedNonConformant rather than discarded
  like the abort/crash cases above.

No engine in the current suite reproduces the "non-stratified negation
detected, kept going, then crashed" case (NonStratifiedCrashed) -- pyshacl's
negation handling is specifically what makes it back out gracefully instead
of crashing. The category is kept for when/if it's observed but has no
detection rule of its own yet, so it only matches through the generic crash
fallback below if the stderr text happens to mention non-stratification.
"""
import re

from .command_result import CommandResult
from .error_type import ErrorType

# Generic, runtime-level crash signatures. Not tied to any specific engine in
# this codebase (none of the active engines were observed crashing this way
# against the current fixtures) -- these cover the JVM/Python/Rust runtimes
# the engines are built on, so a real crash is still classified as Crashed
# rather than falling through unclassified.
_GENERIC_CRASH_PATTERN = re.compile(
    r"StackOverflowError|OutOfMemoryError|RecursionError"
    r"|Fatal Python error|maximum recursion depth exceeded"
    r"|panicked at|segmentation fault|core dumped",
    re.IGNORECASE,
)


def classify_error(runner, status: CommandResult, returncode: int | None, stderr: str, stdout: str = "") -> ErrorType | None:
    """
    Determine which ErrorType (if any) explains a failed/anomalous run.
    Returns None when nothing recognized matches, e.g. a nonzero exit that
    is actually the engine's normal "did not conform" convention (pyshacl,
    shacl_tq) rather than a crash. `stdout` is passed through to the engine's
    own classifier for engines that report errors there instead of stderr
    (see shex_s, which prints "Negative cycles" to stdout).
    """
    if status == CommandResult.TIMEOUT:
        return ErrorType.TIMEOUT

    text = stderr or ""

    specific = runner.classify_error(text, returncode, None, stdout)
    if specific is not None:
        return specific

    if _GENERIC_CRASH_PATTERN.search(text):
        return ErrorType.CRASHED

    # A negative returncode means the process was killed by a signal
    # (segfault, abort, ...) -- a crash even without a recognizable message.
    if returncode is not None and returncode < 0:
        return ErrorType.CRASHED

    return None


def resolve_result(runner, outcome, analyze, stdout: str = ""):
    """
    Turn a command's RunOutcome into a result dict, either by parsing its
    output (when the run looks like it succeeded) or by classifying why it
    didn't. `analyze` is a zero-arg callable that parses the produced output
    file(s) into the usual {'conforms': ..., ...} shape. `runner` is the
    Runner instance whose `classify_error` method supplies engine-specific
    rules. `stdout` is the run's captured standard output, for engines whose
    `run()` call doesn't redirect it straight into the result file (or that
    need it alongside stderr to classify a failure -- see shex_s).
    """
    if outcome.status == CommandResult.OK and outcome.returncode == 0:
        result = analyze()
        warned_but_conformant = runner.classify_error(outcome.stderr, outcome.returncode, result.get('conforms'), stdout)
        if warned_but_conformant is not None:
            updated = {'error_type': warned_but_conformant.value}
            if not result.get('message'):
                updated['message'] = outcome.stderr.strip()
            result = dict(result, **updated)
        return result

    error_type = classify_error(runner, outcome.status, outcome.returncode, outcome.stderr, stdout)
    if error_type is not None:
        return {'conforms': None, 'error_type': error_type.value, 'message': outcome.stderr.strip()}

    if outcome.status == CommandResult.OK:
        # Nonzero exit but no recognized crash signature: some engines (pyshacl,
        # shacl_tq) use a nonzero exit code to mean "ran fine, did not conform".
        return analyze()

    message = f"Error running command {outcome.status}"
    if outcome.stderr:
        message += f": {outcome.stderr.strip()}"
    return {'conforms': None, 'error_type': None, 'message': message}
