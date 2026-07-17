import os
import json
import logging

from .shex_runner import ShExRunner
from .shex_params import ShExParams
from .commands import run, mk_command_shex, store_result
from .analysis import extend_nodes_shapes, summarize_shapemap_results
from .error_classification import resolve_result

BIN = "binaries/rudof/rudof"
CMD = [BIN, "shex-validate", "--schema", "$shex_filename", "--shapemap", "$shapemap_filename", "$data_filename", "--result-format", "json", "--force-overwrite", "--output-file", "$output_filename"]


def analyze_shapemap_rudof(filename, nodes, shapes, pairs):
    extend_nodes_shapes(nodes, shapes, pairs)

    with open(filename, 'r') as infile:
        contents = infile.read()
    # rudof prefixes its JSON output with a "Results:" line that must be stripped before parsing
    if contents.lstrip().startswith("Results:"):
        contents = contents.lstrip().removeprefix("Results:").lstrip()
    try:
        json_result = json.loads(contents)
        logging.debug(f"JSON result: {json_result}")
        conforms, message, failures, successes = summarize_shapemap_results(json_result, nodes, shapes)
    except json.JSONDecodeError as e:
        lines = [line.rstrip() for line in contents.splitlines()]
        message = lines[0] if lines else str(e)
        conforms = False
        failures, successes = [], []
    logging.debug(f"After analyzing shapemap, Conforms: {conforms}")
    return {'conforms': conforms, 'message': message, 'failures': failures, 'successes': successes}


class RudofShexRunner(ShExRunner):
    def __init__(self):
        super().__init__(name="rudof", bin_command=BIN, command_pattern=CMD)

    def execute(self, params: ShExParams, results: list) -> None:
        validation_output = os.path.join(params.results_folder, f"{params.name}_{self.name}_output.json")
        command = mk_command_shex(self.command_pattern, params.data_file, params.shex_file, params.shapemap_file, validation_output)
        logging.info(f"Running: {command}")
        outcome = run(command, validation_output, 5)
        result = resolve_result(self.name, outcome, lambda: analyze_shapemap_rudof(validation_output, params.nodes, params.shapes, params.pairs))
        store_result(params.name, self.engine, self.name, params.description, result, results)
