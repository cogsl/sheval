import os
import logging
import re

from .shacl_runner import SHACLRunner
from .shacl_params import SHACLParams
from .commands import run, mk_command_shacl, store_result
from .analysis import analyze_validation_report
from .error_classification import resolve_result
from .error_type import ErrorType

BIN = "pyshacl"
CMD = [BIN, "-o", "$validation_report_file", "--format", "turtle", "$data_filename"]

# On mutually recursive sh:and shapes (see bsep3), pyshacl walks the recursive
# validation path, exceeds its own internal depth guard, and raises this
# instead of the graceful "ShapeRecursionWarning ... Backing out." it uses for
# simpler recursion (which is not an error at all).
_RULES = [
    (re.compile(r"Validation path too deep"), ErrorType.CYCLES_DETECTED_CRASHED),
]

# On simpler recursive shapes (see bsep1/bsep2), pyshacl doesn't crash: it
# warns "A Recursive Shape was detected ... Backing out." on stderr, then
# exits 0 with a full report. Same situation as jena_shacl's "Cycle detected"
# warning -- the report is real but its verdict isn't guaranteed correct, so
# it's classified by 'conforms' like jena_shacl.py does, not trusted outright.
_RECURSION_WARNING = re.compile(r"ShapeRecursionWarning|Recursive Shape was detected")


class PyshaclRunner(SHACLRunner):
    def __init__(self):
        super().__init__(name="pyshacl", bin_command=BIN, command_pattern=CMD)

    def classify_error(self, stderr: str, returncode: int | None, conforms: bool | None = None, stdout: str = "") -> ErrorType | None:
        text = stderr or ""
        for pattern, error_type in _RULES:
            if pattern.search(text):
                return error_type
        if conforms in (True, False) and _RECURSION_WARNING.search(text):
            return ErrorType.CYCLES_DETECTED_CONFORMANT if conforms else ErrorType.CYCLES_DETECTED_NON_CONFORMANT
        return None

    def execute(self, params: SHACLParams, results: list) -> None:
        validation_report_file = os.path.join(params.results_folder, f"{params.name}_{self.name}_results.ttl")
        validation_output = os.path.join(params.results_folder, f"{params.name}_{self.name}_output.txt")
        command = mk_command_shacl(self.command_pattern, params.filename, validation_report_file)
        outcome = run(command, validation_output, 2)
        result = resolve_result(self, outcome, lambda: analyze_validation_report(validation_report_file, params.nodes, params.shapes, params.pairs, params.include_message))
        store_result(params.name, self.engine, self.name, params.description, result, results)
