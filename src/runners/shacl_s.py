import os
import logging

from .shacl_runner import SHACLRunner
from .shacl_params import SHACLParams
from .commands import run, mk_command_shacl, store_result
from .analysis import analyze_validation_report
from .error_classification import resolve_result

BIN = "binaries/shacl_s-0.1.87/bin/shacl_s"
CMD = [BIN, "--data", "$data_filename", "--output", "$validation_report_file"]


class ShaclSRunner(SHACLRunner):
    def __init__(self):
        super().__init__(name="shacl_s", bin_command=BIN, command_pattern=CMD)

    def execute(self, params: SHACLParams, results: list) -> None:
        validation_report_file = os.path.join(params.results_folder, f"{params.name}_{self.name}_results.ttl")
        validation_output = os.path.join(params.results_folder, f"{params.name}_{self.name}_output.txt")
        command = mk_command_shacl(self.command_pattern, params.filename, validation_report_file)
        logging.info(f"Running: {command}")
        outcome = run(command, validation_output, 5)
        result = resolve_result(self, outcome, lambda: analyze_validation_report(validation_report_file, params.nodes, params.shapes, params.pairs, params.include_message))
        store_result(params.name, self.engine, self.name, params.description, result, results)
