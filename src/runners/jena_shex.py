import os
import re
import logging

from .shex_runner import ShExRunner
from .shex_params import ShExParams
from .command_result import CommandResult
from .commands import run, mk_command_shex, store_result
from .analysis import extend_nodes_shapes, classify_shapemap_results

BIN = "binaries/apache-jena-5.3.0/bin/shex"
CMD = [BIN, "v", "--data", "$data_filename", "--schema", "$shex_filename", "--map", "$shapemap_filename"]


def parse_jena_result_line(line):
    regex = re.compile(r'<([^>]+)>\s@\s<([^>]+)>\s.*Status\s=\s(nonconformant|conformant).*')
    m = regex.match(line)
    (node, shape, conforms) = m.group(1, 2, 3)
    return (node, shape, conforms)


def analyze_result_jena_shex(filename, nodes, shapes, pairs):
    extend_nodes_shapes(nodes, shapes, pairs)

    with open(filename, 'r') as infile:
        results = [dict(zip(('node', 'shape', 'status'), parse_jena_result_line(line))) for line in infile]
    failures, successes = classify_shapemap_results(results, nodes, shapes)

    return {'conforms': not failures, 'message': "", 'failures': failures, 'successes': successes}


class JenaShexRunner(ShExRunner):
    def __init__(self):
        super().__init__(name="jena_shex", bin_command=BIN, command_pattern=CMD)

    def execute(self, params: ShExParams, results: list) -> None:
        output_file = os.path.join(params.results_folder, f"{params.name}_{self.name}_results.txt")
        command = mk_command_shex(self.command_pattern, params.data_file, params.shex_file, params.shapemap_file, output_file)
        result1 = run(command, output_file, 5)
        if result1 == CommandResult.OK:
            logging.debug(f"Command result is OK...validation report file: {output_file}")
            result = analyze_result_jena_shex(output_file, params.nodes, params.shapes, params.pairs)
        else:
            result = {'conforms': "Error", 'failures': "Error running command" + str(result1)}
        store_result(params.name, self.engine, self.name, params.description, result, results)
