from enum import Enum


class ErrorType(Enum):
    """How a validation engine failed to produce a result.

    CyclesDetected / NonStratified: the engine noticed the problem and stopped
    cleanly (no report produced), e.g. rudof aborting SHACL validation.
    Timeout: the engine was killed after exceeding the configured time limit.
    Crashed: the engine terminated unexpectedly (stack overflow or similar),
    unrelated to (or without evidence of) cycle/stratification detection.
    CyclesDetectedCrashed / NonStratifiedCrashed: the engine noticed cycles or
    non-stratified negation but kept processing instead of stopping, and then
    crashed, e.g. pyshacl's "Validation path too deep!" on mutually recursive
    sh:and shapes.
    CyclesDetectedConformant / CyclesDetectedNonConformant: the engine noticed
    cycles, warned about them, but kept going and produced a full validation
    report anyway (unlike CyclesDetectedCrashed, it didn't crash), e.g.
    jena_shacl's "Cycle detected" warning followed by a normal report. The
    two variants record whether that report said conforms=true or
    conforms=false, since the warning means the verdict isn't guaranteed
    correct either way.
    """
    CYCLES_DETECTED = "CyclesDetected"
    NON_STRATIFIED = "NonStratified"
    TIMEOUT = "Timeout"
    CRASHED = "Crashed"
    CYCLES_DETECTED_CRASHED = "CyclesDetectedCrashed"
    NON_STRATIFIED_CRASHED = "NonStratifiedCrashed"
    CYCLES_DETECTED_CONFORMANT = "CyclesDetectedConformant"
    CYCLES_DETECTED_NON_CONFORMANT = "CyclesDetectedNonConformant"
