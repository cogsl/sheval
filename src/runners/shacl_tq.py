import os
import re

from .shacl_runner import SHACLRunner
from .shacl_params import SHACLParams
from .commands import run, mk_command_shacl, store_result
from .analysis import analyze_validation_report, split_file_by_regex
from .error_classification import resolve_result

BIN = "binaries/shacl-1.4.4/bin/shaclvalidate.sh"
CMD = [BIN, "-datafile", "$data_filename"]


class ShaclTqRunner(SHACLRunner):
    def __init__(self):
        super().__init__(name="shacl_tq", bin_command=BIN, command_pattern=CMD)

    def execute(self, params: SHACLParams, results: list) -> None:
        validation_report_file_temp = os.path.join(params.temp, f"{params.name}_{self.name}_results_temp.ttl")
        command = mk_command_shacl(self.command_pattern, params.filename, validation_report_file_temp)
        outcome = run(command, validation_report_file_temp, 5)

        def analyze():
            validation_report_file = os.path.join(params.results_folder, f"{params.name}_{self.name}_results_temp.ttl")
            validation_output = os.path.join(params.results_folder, f"{params.name}_{self.name}_output.txt")
            regex = re.compile('.*Failure.*')
            split_file_by_regex(validation_report_file_temp, regex, validation_output, validation_report_file)
            return analyze_validation_report(validation_report_file, params.nodes, params.shapes, params.pairs, params.include_message)

        result = resolve_result(self, outcome, analyze)
        store_result(params.name, self.engine, self.name, params.description, result, results)
