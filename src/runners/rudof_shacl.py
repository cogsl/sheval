import os
import re

from .shacl_runner import SHACLRunner
from .shacl_params import SHACLParams
from .commands import run, mk_command_shacl, store_result
from .analysis import analyze_validation_report
from .error_classification import resolve_result
from .error_type import ErrorType

BIN = "binaries/rudof/rudof"
CMD = [BIN, "shacl-validate", "$data_filename", "--result-format", "turtle", "--force-overwrite", "--output-file", "$output_filename"]

# rudof's SHACL validator aborts cleanly (no report written) on a recursive
# schema, printing one of these to stderr. See error_classification.py for
# how this fits into the overall classification flow.
_RULES = [
    (re.compile(r"negative cycles \(non-stratified\)"), ErrorType.NON_STRATIFIED),
    (re.compile(r"[Dd]ependency graph has cycles"), ErrorType.CYCLES_DETECTED),
]


class RudofShaclRunner(SHACLRunner):
    def __init__(self):
        super().__init__(name="rudof", bin_command=BIN, command_pattern=CMD)

    def classify_error(self, stderr: str, returncode: int | None, conforms: bool | None = None, stdout: str = "") -> ErrorType | None:
        text = stderr or ""
        for pattern, error_type in _RULES:
            if pattern.search(text):
                return error_type
        return None

    def execute(self, params: SHACLParams, results: list) -> None:
        validation_report_file = os.path.join(params.results_folder, f"{params.name}_{self.name}_results.ttl")
        validation_output = os.path.join(params.results_folder, f"{params.name}_{self.name}_output.txt")
        command = mk_command_shacl(self.command_pattern, params.filename, validation_report_file)
        outcome = run(command, validation_output, 2)
        result = resolve_result(self, outcome, lambda: analyze_validation_report(validation_report_file, params.nodes, params.shapes, params.pairs, params.include_message))
        store_result(params.name, self.engine, self.name, params.description, result, results)
