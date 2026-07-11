import os
import logging

from .base import SHACLRunner, ShExRunner, SHACLParams, ShExParams, CommandResult, run, mk_command_shacl, mk_command_shex, store_result
from .analysis import analyze_validation_report, analyze_shapemap_shaclex

BIN = "binaries/shaclex-0.2.7/bin/shaclex"

# Shaclex has been replaced by SHACL_S
SHACL_CMD = [BIN,
             "--validate",
             "--engine", "SHACLEX",
             "--data", "$data_filename",
             "--validationReportFormat", "TURTLE",
             "--showValidationReport",
             "--validationReportFile", "$validation_report_file"
             ]

SHEX_CMD = [BIN,
            "--dataFormat", "TURTLE",
            "--data", "$data_filename",
            "--schema", "$shex_filename",
            "--schemaFormat", "SHEXC",
            "--shapeMap", "$shapemap_filename",
            "--validate",
            "--engine", "SHEX",
            "--trigger", "SHAPEMAP",
            "--showResult",
            "--resultFormat", "JSON",
            "--outFile", "$output_filename",
            "--checkWellFormed"
            ]


class ShaclexShaclRunner(SHACLRunner):
    def __init__(self):
        super().__init__(name="shaclex_shacl", bin_command=BIN, command_pattern=SHACL_CMD)

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


class ShaclexShexRunner(ShExRunner):
    def __init__(self):
        super().__init__(name="shaclex_shex", bin_command=BIN, command_pattern=SHEX_CMD)

    def execute(self, params: ShExParams, results: list) -> None:
        validation_output = os.path.join(params.results_folder, f"{params.name}_{self.name}_output.json")
        command = mk_command_shex(self.command_pattern, params.data_file, params.shex_file, params.shapemap_file, validation_output)
        logging.info(f"Running: {command}")
        result1 = run(command, validation_output, 5)
        if result1 == CommandResult.OK:
            logging.debug(f"Command result is OK...before analyzing shapemap file: {validation_output}")
            result = analyze_shapemap_shaclex(validation_output, params.nodes, params.shapes, params.pairs)
        else:
            result = {'conforms': "Error", 'failures': "Error running command" + str(result1)}
        store_result(params.name, self.engine, self.name, params.description, result, results)
