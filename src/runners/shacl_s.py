import os
import logging

from .shacl_runner import SHACLRunner
from .shacl_params import SHACLParams
from .command_result import CommandResult
from .commands import run, mk_command_shacl, store_result
from .analysis import analyze_validation_report

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
        result1 = run(command, validation_output, 5)
        if result1 == CommandResult.OK:
            result = analyze_validation_report(validation_report_file, params.nodes, params.shapes, params.pairs, params.include_message)
        else:
            result = {'conforms': "Error", 'failures': "Error running command" + str(result1)}
        store_result(params.name, self.engine, self.name, params.description, result, results)
