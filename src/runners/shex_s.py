import os
import logging

from .base import ShExRunner, ShExParams, CommandResult, run, mk_command_shex, store_result
from .analysis import analyze_shapemap_shex_s

BIN = "binaries/shexs-0.2.34/bin/shexs"
CMD = [BIN, "validate", "--data", "$data_filename", "--schema", "$shex_filename", "--shapeMap", "$shapemap_filename", "--showResultFormat", "JSON", "--output", "$output_filename"]


class ShexSRunner(ShExRunner):
    def __init__(self):
        super().__init__(name="shex_s", bin_command=BIN, command_pattern=CMD)

    def execute(self, params: ShExParams, results: list) -> None:
        validation_output = os.path.join(params.results_folder, f"{params.name}_{self.name}_output.json")
        command = mk_command_shex(self.command_pattern, params.data_file, params.shex_file, params.shapemap_file, validation_output)
        logging.info(f"Running: {command}")
        result1 = run(command, validation_output, 5)
        if result1 == CommandResult.OK:
            logging.debug(f"Command result is OK...before analyzing shapemap file: {validation_output}")
            result = analyze_shapemap_shex_s(validation_output, params.nodes, params.shapes, params.pairs)
        else:
            result = {'conforms': "Error", 'failures': "Error running command" + str(result1)}
        store_result(params.name, self.engine, self.name, params.description, result, results)
