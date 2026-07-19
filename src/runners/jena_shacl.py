import os
import logging
import re

from .shacl_runner import SHACLRunner
from .shacl_params import SHACLParams
from .commands import run, mk_command_shacl, store_result
from .analysis import analyze_validation_report
from .error_classification import resolve_result
from .error_type import ErrorType

BIN = "binaries/apache-jena-5.3.0/bin/shacl"
CMD = [BIN, "v", "--data", "$data_filename"]

# jena_shacl warns about cycles on stderr but still exits 0 with a usable
# report (see bsep1/bsep3), unlike rudof (which aborts) or pyshacl (which can
# crash on the mutually-recursive case). Checked only when a run has already
# succeeded, to flag that report's 'conforms' value as coming from a cyclic
# catalogue rather than to explain a failure.
_CYCLE_WARNING = re.compile(r"Cycle detected")


class JenaShaclRunner(SHACLRunner):
    def __init__(self):
        super().__init__(name="jena_shacl", bin_command=BIN, command_pattern=CMD)

    def classify_error(self, stderr: str, returncode: int | None, conforms: bool | None = None, stdout: str = "") -> ErrorType | None:
        if conforms not in (True, False):
            return None
        if not _CYCLE_WARNING.search(stderr or ""):
            return None
        return ErrorType.CYCLES_DETECTED_CONFORMANT if conforms else ErrorType.CYCLES_DETECTED_NON_CONFORMANT

    def execute(self, params: SHACLParams, results: list) -> None:
        validation_report_file = os.path.join(params.results_folder, f"{params.name}_{self.name}_results.ttl")
        command = mk_command_shacl(self.command_pattern, params.filename, validation_report_file)
        outcome = run(command, validation_report_file, 5)
        result = resolve_result(self, outcome, lambda: analyze_validation_report(validation_report_file, params.nodes, params.shapes, params.pairs, params.include_message))
        store_result(params.name, self.engine, self.name, params.description, result, results)
