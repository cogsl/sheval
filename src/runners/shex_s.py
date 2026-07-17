import os
import json
import logging

from .shex_runner import ShExRunner
from .shex_params import ShExParams
from .commands import run, mk_command_shex, store_result
from .analysis import extend_nodes_shapes, summarize_shapemap_results
from .error_classification import resolve_result

BIN = "binaries/shexs-0.2.34/bin/shexs"
CMD = [BIN, "validate", "--data", "$data_filename", "--schema", "$shex_filename", "--shapeMap", "$shapemap_filename", "--showResultFormat", "JSON", "--output", "$output_filename"]


def analyze_shapemap_shex_s(filename, nodes, shapes, pairs):
    extend_nodes_shapes(nodes, shapes, pairs)

    with open(filename, 'r') as infile:
        try:
            json_result = json.load(infile)
            logging.debug(f"JSON result: {json_result}")
            conforms, message, failures, successes = summarize_shapemap_results(json_result, nodes, shapes)
        except json.JSONDecodeError:
            infile.seek(0)
            lines = [line.rstrip() for line in infile]
            message = lines[0]
            conforms = False
            failures, successes = [], []
    logging.debug(f"After analyzing shapemap, Conforms: {conforms}")
    return {'conforms': conforms, 'message': message, 'failures': failures, 'successes': successes}


class ShexSRunner(ShExRunner):
    def __init__(self):
        super().__init__(name="shex_s", bin_command=BIN, command_pattern=CMD)

    def execute(self, params: ShExParams, results: list) -> None:
        validation_output = os.path.join(params.results_folder, f"{params.name}_{self.name}_output.json")
        command = mk_command_shex(self.command_pattern, params.data_file, params.shex_file, params.shapemap_file, validation_output)
        logging.info(f"Running: {command}")
        outcome = run(command, validation_output, 5)
        result = resolve_result(self.name, outcome, lambda: analyze_shapemap_shex_s(validation_output, params.nodes, params.shapes, params.pairs))
        store_result(params.name, self.engine, self.name, params.description, result, results)
