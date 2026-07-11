import os
import logging

from .base import SHACLRunner, SHACLParams, CommandResult, run, mk_command_shacl, store_result
from .analysis import analyze_validation_report

BIN = "pyshacl"
CMD = [BIN, "-o", "$validation_report_file", "--format", "turtle", "$data_filename"]


class PyshaclRunner(SHACLRunner):
    def __init__(self):
        super().__init__(name="pyshacl", bin_command=BIN, command_pattern=CMD)

    def execute(self, params: SHACLParams, results: list) -> None:
        validation_report_file = os.path.join(params.results_folder, f"{params.name}_{self.name}_results.ttl")
        validation_output = os.path.join(params.results_folder, f"{params.name}_{self.name}_output.txt")
        command = mk_command_shacl(self.command_pattern, params.filename, validation_report_file)
        result1 = run(command, validation_output, 2)
        if result1 == CommandResult.OK:
            result = analyze_validation_report(validation_report_file, params.nodes, params.shapes, params.pairs, params.include_message)
        else:
            result = {'conforms': "Error", 'failures': "Error running command" + str(result1)}
        store_result(params.name, self.engine, self.name, params.description, result, results)
