import os
import logging

from .shacl_runner import SHACLRunner
from .shacl_params import SHACLParams
from .command_result import CommandResult
from .commands import run, mk_command_shacl, store_result
from .analysis import analyze_validation_report

BIN = "binaries/apache-jena-5.3.0/bin/shacl"
CMD = [BIN, "v", "--data", "$data_filename"]


class JenaShaclRunner(SHACLRunner):
    def __init__(self):
        super().__init__(name="jena_shacl", bin_command=BIN, command_pattern=CMD)

    def execute(self, params: SHACLParams, results: list) -> None:
        validation_report_file = os.path.join(params.results_folder, f"{params.name}_{self.name}_results.ttl")
        command = mk_command_shacl(self.command_pattern, params.filename, validation_report_file)
        result1 = run(command, validation_report_file, 5)
        if result1 == CommandResult.OK:
            logging.debug(f"Command result is OK...validation report file: {validation_report_file}")
            result = analyze_validation_report(validation_report_file, params.nodes, params.shapes, params.pairs, params.include_message)
        else:
            result = {'conforms': "Error", 'failures': "Error running command" + str(result1)}
        store_result(params.name, self.engine, self.name, params.description, result, results)
