"""
Classifies why a validation engine's run did not produce a usable result.

Each engine reports cycle detection / non-stratified negation / crashes in its
own way (different processes, different runtimes), so the recognized patterns
below are keyed by technology name. They were derived by actually running the
engines against test_suites/recursive_shapes fixtures, not guessed:

- rudof (SHACL): aborts cleanly, no report written, and prints one of
  "Dependency graph has cycles: [...]" or
  "Dependency graph has negative cycles (non-stratified): [...]" to stderr.
- pyshacl: on mutually recursive sh:and shapes (see bsep3), it walks the
  recursive validation path, exceeds its own internal depth guard, and raises
  "Validator encountered a Runtime Error:\\nValidation path too deep!" instead
  of the graceful "ShapeRecursionWarning ... Backing out." it uses for
  simpler recursion (which is not an error at all).
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

_RUDOF_RULES = [
    (re.compile(r"negative cycles \(non-stratified\)"), ErrorType.NON_STRATIFIED),
    (re.compile(r"[Dd]ependency graph has cycles"), ErrorType.CYCLES_DETECTED),
]

_PYSHACL_RULES = [
    (re.compile(r"Validation path too deep"), ErrorType.CYCLES_DETECTED_CRASHED),
]

_TECHNOLOGY_RULES = {
    "rudof": _RUDOF_RULES,
    "pyshacl": _PYSHACL_RULES,
}

# Engines that warn about cycles on stderr but still exit 0 with a usable
# report. Checked only when a run has already succeeded (see resolve_result),
# to flag that report's 'conforms' value as coming from a cyclic catalogue
# rather than to explain a failure.
_WARN_BUT_CONTINUED_RULES = {
    "jena_shacl": [re.compile(r"Cycle detected")],
}


def _classify_warned_but_conformant(technology: str, stderr: str, conforms) -> ErrorType | None:
    if conforms not in (True, False):
        return None
    patterns = _WARN_BUT_CONTINUED_RULES.get(technology, [])
    if not any(pattern.search(stderr or "") for pattern in patterns):
        return None
    return ErrorType.CYCLES_DETECTED_CONFORMANT if conforms else ErrorType.CYCLES_DETECTED_NON_CONFORMANT

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


def classify_error(technology: str, status: CommandResult, returncode: int | None, stderr: str) -> ErrorType | None:
    """
    Determine which ErrorType (if any) explains a failed/anomalous run.
    Returns None when nothing recognized matches, e.g. a nonzero exit that
    is actually the engine's normal "did not conform" convention (pyshacl,
    shacl_tq) rather than a crash.
    """
    if status == CommandResult.TIMEOUT:
        return ErrorType.TIMEOUT

    text = stderr or ""
    for pattern, error_type in _TECHNOLOGY_RULES.get(technology, []):
        if pattern.search(text):
            return error_type

    if _GENERIC_CRASH_PATTERN.search(text):
        return ErrorType.CRASHED

    # A negative returncode means the process was killed by a signal
    # (segfault, abort, ...) -- a crash even without a recognizable message.
    if returncode is not None and returncode < 0:
        return ErrorType.CRASHED

    return None


def resolve_result(technology: str, outcome, analyze):
    """
    Turn a command's RunOutcome into a result dict, either by parsing its
    output (when the run looks like it succeeded) or by classifying why it
    didn't. `analyze` is a zero-arg callable that parses the produced output
    file(s) into the usual {'conforms': ..., ...} shape.
    """
    if outcome.status == CommandResult.OK and outcome.returncode == 0:
        result = analyze()
        warned_but_conformant = _classify_warned_but_conformant(technology, outcome.stderr, result.get('conforms'))
        if warned_but_conformant is not None:
            result = dict(result, error_type=warned_but_conformant.value, message=outcome.stderr.strip())
        return result

    error_type = classify_error(technology, outcome.status, outcome.returncode, outcome.stderr)
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
