from enum import Enum
import os
import re
import subprocess
import rdflib
import json
import logging

from dataclasses import dataclass

@dataclass
class SHACLParams:
    filename: str
    name: str
    description: str
    results_folder: str
    temp: str
    technology: str
    data_graph: str
    nodes: list
    shapes: list
    pairs: list
    include_message: bool
    include_descr: bool

@dataclass
class ShExParams:
    data_file: str
    shex_file: str
    shapemap_file: str
    name: str
    description: str
    results_folder: str
    technology: str
    nodes: list
    shapes: list
    pairs: list
    include_message: bool
    include_descr: bool


class SHACLRunner:
    def __init__(self, name, bin_command, command_pattern, run_shacl):
        self.name = name
        self.bin_command = bin_command
        self.command_pattern = command_pattern
        self.run_shacl = run_shacl

    def run(self, params: SHACLParams, results: list) -> None:
        logging.info(f"Running SHACL for {params.name} with technology {params.technology}")
        try:
            self.run_shacl(params, results)
        except Exception as e:
            logging.error(f"Error running SHACL for {params.name} with technology {params.technology}: {e}")
            result = {'conforms': "Exception", 'failures': f"{e}"}
            store_result(params.name, params.technology, params.description, result, results)


class ShExRunner:
    def __init__(self, name, bin_command, command_pattern, run_shex):
        self.name = name
        self.bin_command = bin_command
        self.command_pattern = command_pattern
        self.run_shex = run_shex

    def run(self, params: ShExParams, results: list) -> None:
        logging.info(f"Running ShEx for {params.name} with technology {params.technology}")
        try:
            self.run_shex(params, results)
        except Exception as e:
            logging.error(f"Error running ShEx for {params.name} with technology {params.technology}: {e}")
            result = {'conforms': "Exception", 'failures': f"{e}"}
            store_result(params.name, params.technology, params.description, result, results)


class CommandResult(Enum):
    OK = 0
    TIMEOUT = 1
    ERROR = 2
    EXCEPTION = 3

shacl_prefix = "http://www.w3.org/ns/shacl#"

def run_args(command: list[str]): 
    logging.debug(f"Before running command: {command}")
    result = CommandResult.ERROR
    try:
        result = subprocess.run(command, check=True)
    except subprocess.CalledProcessError as callProcessErr:
        cmdErrStr = str(callProcessErr)
        print("Error %s running command: %s" % (cmdErrStr, command))
        result = CommandResult.EXCEPTION
    except Exception as e:
        logging.error(f"Error running command {command}: {e}")
        result = CommandResult.EXCEPTION
    return result

def run(command, output_filename, timeout = 2):
    result = CommandResult.ERROR
    try:
        with open(output_filename, "w") as output:
            command_str = " ".join(command) + " > " + str(output_filename)
            logging.info(f"Command: {command_str}")
            subprocess.run(command, stdout = output, timeout=timeout)
            result = CommandResult.OK
    except subprocess.TimeoutExpired as timeoutErr:
        print("Timeout expired running command: %s" % (command))
        result = CommandResult.TIMEOUT
    except subprocess.CalledProcessError as callProcessErr:
        cmdErrStr = str(callProcessErr)
        print("Error %s running command: %s" % (cmdErrStr, command))
        result = CommandResult.EXCEPTION
    return result

def mk_command_shacl(command, filename, output):
    return list(map(lambda x: 
                       x.replace("$data_filename", filename)
                       .replace("$validation_report_file", output)
                       .replace("$output_filename", output)
                       , command))

def mk_command_shex(command, data_filename, shex_filename, shapemap_filename, output):
    return list(map(lambda x: 
                       x.replace("$data_filename", data_filename)
                       .replace("$shex_filename", shex_filename)
                       .replace("$shapemap_filename", shapemap_filename)
                       .replace("$output_filename", output), command))

pyshacl_bin = "pyshacl"
pyshacl_cmd = [pyshacl_bin, "-o", "$validation_report_file", "--format", "turtle", "$data_filename" ]

shacl_tq_bin = "binaries/shacl-1.4.4/bin/shaclvalidate.sh"
shacl_tq_cmd = [shacl_tq_bin, "-datafile", "$data_filename"]

shacl_s_bin = "binaries/shacl_s-0.1.87/bin/shacl_s"
shacl_s_cmd = [shacl_s_bin,
                     "--data", "$data_filename",
                     "--output", "$validation_report_file"
               ]

# Shaclex has been replaced by SHACL_S
shaclex_shacl_cmd = ["binaries/shaclex-0.2.7/bin/shaclex",
                     "--validate",
                     "--engine","SHACLEX",
                     "--data", "$data_filename",
                     "--validationReportFormat","TURTLE",
                     "--showValidationReport",
                     "--validationReportFile", "$validation_report_file"
                     ]

shaclex_shex_cmd = ["binaries/shaclex-0.2.7/bin/shaclex", 
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

shex_s_bin = "binaries/shexs-0.2.34/bin/shexs"
shex_s_cmd = [shex_s_bin, 
              "validate",
              "--data", "$data_filename", 
              "--schema", "$shex_filename", 
              "--shapeMap", "$shapemap_filename", 
              "--showResultFormat", "JSON", 
              "--output", "$output_filename",
              ] 


jena_shacl_bin = "binaries/apache-jena-5.3.0/bin/shacl"
jena_shacl_cmd = [jena_shacl_bin, 
                  "v", 
                  "--data", "$data_filename"
                  ]

rudof_bin = "binaries/rudof/rudof"
rudof_shacl_cmd = [rudof_bin,
                   "shacl-validate","$data_filename", 
                   "--result-format", "turtle", 
                   "--force-overwrite", 
                   "--output-file", "$output_filename"]

jena_shex_bin = "binaries/apache-jena-5.3.0/bin/shex"
jena_shex_cmd = [jena_shex_bin, "v", "--data", "$data_filename", "--schema", "$shex_filename", "--map", "$shapemap_filename"]

rudof_shex_cmd = [rudof_bin,"shex-validate","--schema", "$shex_filename", "--shapemap", "$shapemap_filename", "$data_filename", "--result-format", "json", "--force-overwrite", "--output-file", "$output_filename"]

def shacl_tq(params: SHACLParams, results: list) -> None:
    try:
        technology_name = "shacl_tq"
        engine = "shacl"
        validation_report_file_temp = os.path.join(params.temp, f"{params.name}_{technology_name}_results_temp.ttl")
        # output_file_temp = os.path.join(temp, f"{name}_{technology_name}_output_temp.txt")
        command = mk_command_shacl(shacl_tq_cmd, params.filename, validation_report_file_temp)
        result1 = run(command, validation_report_file_temp, 5)
        if result1 == CommandResult.OK:
            validation_report_file = os.path.join(params.results_folder, f"{params.name}_{technology_name}_results_temp.ttl")
            validation_output = os.path.join(params.results_folder, f"{params.name}_{technology_name}_output.txt")
            regex = re.compile('.*Failure.*')
            split_file_by_regex(validation_report_file_temp, regex, validation_output, validation_report_file)
            result = analyze_validation_report(validation_report_file, params.nodes, params.shapes, params.pairs, params.include_message)
        else:
            result = { 'conforms': "Error", 'failures': "Error running command" + str(result1) }    
        store_result(params.name, engine, technology_name, params.description, result, results)
    except Exception as e:
        logging.info(f"Error running {technology_name}: {e}")
        result = { 'conforms': "Exception", 'failures': f"{e}" }
        store_result(params.name, engine, technology_name, params.description, result, results)

def jena_shacl(params: SHACLParams, results: list) -> None:
    try:
        technology_name = "jena_shacl"
        engine = "shacl"
        validation_report_file = os.path.join(params.results_folder, f"{params.name}_{technology_name}_results.ttl")
        # output = os.path.join(results_folder, f"{name}_{technology_name}_output.txt")
        command = mk_command_shacl(jena_shacl_cmd, params.filename, validation_report_file)
        result1 = run(command, validation_report_file, 5)
        if result1 == CommandResult.OK:
            logging.debug(f"Command result is OK...validation report file: {validation_report_file}")
            result = analyze_validation_report(validation_report_file, params.nodes, params.shapes, params.pairs, params.include_message)
            store_result(params.name, engine, technology_name, params.description, result, results)
        else:
            result = { 'conforms': "Error", 'failures': "Error running command" + str(result1) }    
            store_result(params.name, engine, technology_name, params.description, result, results)    
    except Exception as e:
        logging.info(f"Error running {technology_name}: {e}")
        result = { 'conforms': "Exception", 'failures': f"{e}" }
        store_result(params.name, engine, technology_name, params.description, result, results)

def jena_shex(shex_params: ShExParams, results: list) -> None:
    try:
        technology_name = "jena_shex"
        engine = "shex"
        output_file = os.path.join(shex_params.results_folder, f"{shex_params.name}_{technology_name}_results.txt")
        # output = os.path.join(results_folder, f"{name}_{technology_name}_output.txt")
        command = mk_command_shex(jena_shex_cmd, shex_params.data_file, shex_params.shex_file, shex_params.shapemap_file, output_file)
        result1 = run(command, output_file, 5)
        if result1 == CommandResult.OK:
            logging.debug(f"Command result is OK...validation report file: {output_file}")
            result = analyze_result_jena_shex(output_file,shex_params.nodes,shex_params.shapes,shex_params.pairs)
            store_result(shex_params.name, engine, technology_name, shex_params.description, result, results)
        else:
            result = { 'conforms': "Error", 'failures': "Error running command" + str(result1) }    
            store_result(shex_params.name, engine, technology_name, shex_params.description, result, results)
    except Exception as e:
        logging.info(f"Error running {technology_name}: {e}")
        result = { 'conforms': "Exception", 'failures': f"{e}" }
        store_result(shex_params.name, engine, technology_name, shex_params.description, result, results)

def shaclex_shacl(params: SHACLParams, results: list) -> None:
    try:
        technology_name = "shaclex_shacl"
        engine = "shacl"
        validation_report_file = os.path.join(params.results_folder, f"{params.name}_{technology_name}_results.ttl")
        validation_output = os.path.join(params.results_folder, f"{params.name}_{technology_name}_output.txt")
        command = mk_command_shacl(shaclex_shacl_cmd, params.filename, validation_report_file)
        logging.info(f"Running: {command}")
        result1 = run(command, validation_output, 5)
        if result1 == CommandResult.OK:
            result = analyze_validation_report(validation_report_file, params.nodes, params.shapes, params.pairs, params.include_message)
            store_result(params.name, engine, technology_name, params.description, result, results)
        else:
            result = { 'conforms': "Error", 'failures': "Error running command" + str(result1) }
            store_result(params.name, engine, technology_name, params.description, result, results)
    except Exception as e:
        logging.info(f"Error running {technology_name}: {e}")
        result = { 'conforms': "Exception", 'failures': f"{e}" }
        store_result(params.name, engine, technology_name, params.description, result, results)

def shacl_s(params: SHACLParams, results: list) -> None:
    try:
        technology_name = "shacl_s"
        engine = "shacl"
        validation_report_file = os.path.join(params.results_folder, f"{params.name}_{technology_name}_results.ttl")
        validation_output = os.path.join(params.results_folder, f"{params.name}_{technology_name}_output.txt")
        command = mk_command_shacl(shacl_s_cmd, params.filename, validation_report_file)
        logging.info(f"Running: {command}")
        result1 = run(command, validation_output, 5)
        if result1 == CommandResult.OK:
            result = analyze_validation_report(validation_report_file,params.nodes,params.shapes,params.pairs, params.include_message)
            store_result(params.name, engine, technology_name, params.description, result, results)
        else:
            result = { 'conforms': "Error", 'failures': "Error running command" + str(result1) }
            store_result(params.name, engine, technology_name, params.description, result, results)
    except Exception as e:
        logging.info(f"Error running {technology_name}: {e}")
        result = { 'conforms': "Exception", 'failures': f"{e}" }
        store_result(params.name, engine, technology_name, params.description, result, results)

def shex_s(params: ShExParams, results: list) -> None:
    try:
        technology_name = "shex_s"
        engine = "shex"
        validation_output = os.path.join(params.results_folder, f"{params.name}_{technology_name}_output.json")
        command = mk_command_shex(shex_s_cmd, params.data_file, params.shex_file, params.shapemap_file, validation_output)
        logging.info(f"Running: {command}")
        result1 = run(command, validation_output, 5)
        if result1 == CommandResult.OK:
            logging.debug(f"Command result is OK...before analyzing shapemap file: {validation_output}")
            result = analyze_shapemap_shex_s(validation_output, params.nodes, params.shapes, params.pairs)
            store_result(params.name, engine, technology_name, params.description, result, results)
        else:
            result = { 'conforms': "Error", 'failures': "Error running command" + str(result1) }
            store_result(params.name, engine, technology_name, params.description, result, results)
    except Exception as e:
        logging.info(f"Error running {technology_name}: {e}")
        result = { 'conforms': "Exception", 'failures': f"{e}" }
        store_result(params.name, engine, technology_name, params.description, result, results)

def shaclex_shex(params: ShExParams, results) -> None:
    try:
        technology_name = "shaclex_shex"
        engine = "shex"
        validation_output = os.path.join(params.results_folder, f"{params.name}_{technology_name}_output.json")
        command = mk_command_shex(shaclex_shex_cmd, params.data_file, params.shex_file, params.shapemap_file, validation_output)
        logging.info(f"Running: {command}")
        result1 = run(command, validation_output, 5)
        if result1 == CommandResult.OK:
            logging.debug(f"Command result is OK...before analyzing shapemap file: {validation_output}")
            result = analyze_shapemap_shaclex(validation_output, params.nodes, params.shapes, params.pairs)
            store_result(params.name, engine, technology_name, params.description, result, results)
        else:
            result = { 'conforms': "Error", 'failures': "Error running command" + str(result1) }
            store_result(params.name, engine, technology_name, params.description, result, results)
    except Exception as e:
        logging.info(f"Error running {technology_name}: {e}")
        result = { 'conforms': "Exception", 'failures': f"{e}" }
        store_result(params.name, engine, technology_name, params.description, result, results)

def rudof_shex(params: ShExParams, results) -> None:
    try:
        technology_name = "rudof"
        engine = "shex"
        validation_output = os.path.join(params.results_folder, f"{params.name}_{technology_name}_output.json")
        command = mk_command_shex(rudof_shex_cmd, params.data_file, params.shex_file, params.shapemap_file, validation_output)
        logging.info(f"Running: {command}")
        result1 = run(command, validation_output, 5)
        if result1 == CommandResult.OK:
            logging.debug(f"Command result is OK...before analyzing shapemap file: {validation_output}")
            result = analyze_shapemap_shex_s(validation_output, params.nodes, params.shapes, params.pairs)
            store_result(params.name, engine, technology_name, params.description, result, results)
        else:
            result = { 'conforms': "Error", 'failures': "Error running command" + str(result1) }
            store_result(params.name, engine, technology_name, params.description, result, results)
    except Exception as e:
        logging.info(f"Error running {technology_name}: {e}")
        result = { 'conforms': "Exception", 'failures': f"{e}" }
        store_result(params.name, engine, technology_name, params.description, result, results)

# Run pyshacl validation
def pyshacl(params: SHACLParams, results: list) -> None:
    try:
        technology_name = "pyshacl"
        engine = "shacl"
        validation_report_file = os.path.join(params.results_folder, f"{params.name}_{technology_name}_results.ttl")
        validation_output = os.path.join(params.results_folder, f"{params.name}_{technology_name}_output.txt")
        command = mk_command_shacl(pyshacl_cmd, params.filename, validation_report_file)
        result1 = run(command, validation_output, 2)
        if result1 == CommandResult.OK:
            result = analyze_validation_report(validation_report_file, params.nodes, params.shapes, params.pairs, params.include_message)
            store_result(params.name, engine, technology_name, params.description, result, results)
        else:
            result = { 'conforms': "Error", 'failures': "Error running command" + str(result1) }
            store_result(params.name, engine, technology_name, params.description, result, results)
    except Exception as e:
        logging.info(f"Error running {params.name} with {technology_name}: {e}")
        result = { 'conforms': "Exception", 'failures': f"{e}" }
        store_result(params.name, engine, technology_name, params.description, result, results)

# Run pyshacl validation
def rudof_shacl(params: SHACLParams, results: list) -> None:
    try:
        technology_name = "rudof"
        engine = "shacl"
        validation_report_file = os.path.join(params.results_folder, f"{params.name}_{technology_name}_results.ttl")
        validation_output = os.path.join(params.results_folder, f"{params.name}_{technology_name}_output.txt")
        command = mk_command_shacl(rudof_shacl_cmd, params.filename, validation_report_file)
        result1 = run(command, validation_output, 2)
        if result1 == CommandResult.OK:
            result = analyze_validation_report(validation_report_file, params.nodes, params.shapes, params.pairs, params.include_message)
            store_result(params.name, engine, technology_name, params.description, result, results)
        else:
            result = { 'conforms': "Error", 'failures': "Error running command" + str(result1) }
            store_result(params.name, engine, technology_name, params.description, result, results)
    except Exception as e:
        logging.info(f"Error running {params.name} with {technology_name}: {e}")
        result = { 'conforms': "Exception", 'failures': f"{e}" }
        store_result(params.name, engine, technology_name, params.description, result, results)

def prepare_shapemap(nodes:list, shapes:list, pairs: list, merged_filename:str) -> None:
    if not nodes and not shapes and not pairs:
        print("No nodes, shapes or pairs to prepare shapemap")
        return
    
    strs = []
    for (node, node_iri) in nodes:
        for (shape, shape_iri) in shapes:
            strs.append(f"<{node_iri}>@<{shape_iri}>")
    for pair in pairs:
        node_iri = pair['node'][1]
        shape_iri = pair['shape'][1]
        strs.append(f"<{node_iri}>@<{shape_iri}>")
    shapemap = ",".join(strs)
    with open(merged_filename, 'w') as outfile:
        logging.debug(f"Writing shapemap {shapemap}\n in file {merged_filename}")
        outfile.write(shapemap)

def analyze_shapemap_shaclex(filename: str,nodes: list,shapes: list,pairs: list):
    # Extend nodes and shapes with the individual ones declared using pairs
    # so they can be found in the shapemap
    for pair in pairs:
        nodes.append(pair['node'])
        shapes.append(pair['shape'])

    conforms = None
    failures = []
    successes = []
    with open(filename, 'r') as infile:
        json_result = json.load(infile)
        logging.debug(f"JSON result: {json_result}")
        conforms = json_result['valid']
        if 'message' in json_result:
            message = json_result['message']
        else:
            message = ""

        if 'shapeMap' in json_result and type(json_result['shapeMap']) is list:
            for result in json_result['shapeMap']:
                node = result['node']
                shape = result['shape']
                status = result['status']
                node = remove_gt_lt(node)
                shape = remove_gt_lt(shape)
                maybe_node = find_qname(nodes, node)
                maybe_shape = find_qname(shapes, shape)
                 # We add to the list of failures only the ones that appear in the nodes and shapes that we are interested
                if maybe_node is not None:
                    node = maybe_node
                    if maybe_shape is not None:
                        shape = maybe_shape
                        if status == "conformant":
                            successes.append({'node': node, 'shape': shape})
                        else:
                            failures.append({'node': node, 'shape': shape})    
                    else:
                        logging.info(f"Shape {shape} not found in the shapes list: {shapes}")
                else:
                    logging.info(f"Node {node} not found in the nodes list: {nodes}")                                          
    logging.info(f"After analyzing shapemap, Conforms: {conforms}")                    
    return { 'conforms': conforms, 'message': message, 'failures': failures, 'successes': successes }

def analyze_shapemap_shex_s(filename,nodes,shapes,pairs):
    # Extend nodes and shapes with the individual ones declared using pairs
    # so they can be found in the shapemap
    for pair in pairs:
        nodes.append(pair['node'])
        shapes.append(pair['shape'])

    conforms = None
    failures = []
    successes = []
    with open(filename, 'r') as infile:
        try:
            json_result = json.load(infile) 
            logging.debug(f"JSON result: {json_result}")
            if isinstance(json_result, list): 
                for result in json_result:
                    logging.debug(f"Result: {result}")
                    node = result['node']
                    shape = result['shape']
                    status = result['status']
                    node = remove_gt_lt(node)
                    shape = remove_gt_lt(shape)
                    maybe_node = find_qname(nodes, node)
                    maybe_shape = find_qname(shapes, shape)
                    # We add to the list of failures only the ones that appear in the nodes and shapes that we are interested
                    if maybe_node is not None:
                        node = maybe_node
                        if maybe_shape is not None:
                            shape = maybe_shape
                            if status == "conformant":
                                successes.append({'node': node, 'shape': shape})
                            else:
                                failures.append({'node': node, 'shape': shape})    
                        else:
                                logging.info(f"Shape {shape} not found in the shapes list: {shapes}")
                    else:
                        logging.info(f"Node {node} not found in the nodes list: {nodes}")
                if failures:
                    conforms = False
                    message = "Some nodes are not conformant"
                else:
                    conforms = True
                    message = "No failures"
            else:
                message = "No results in shapemap"
                conforms = False             
        except json.JSONDecodeError as e:
            infile.seek(0)
            lines = [line.rstrip() for line in infile]
            message = lines[0]
            conforms = False        
    logging.debug(f"After analyzing shapemap, Conforms: {conforms}")                    
    return { 'conforms': conforms, 'message': message, 'failures': failures, 'successes': successes }

def analyze_result_jena_shex(filename,nodes,shapes,pairs):
    conforms = True
    failures = []
    successes = []
    message = ""
    for pair in pairs:
        nodes.append(pair['node'])
        shapes.append(pair['shape'])

    with open(filename, 'r') as infile:
        for line in infile:
            (node, shape, status) = parse_jena_result_line(line)

            maybe_node = find_qname(nodes, node)
            maybe_shape = find_qname(shapes, shape)
            if maybe_node is not None:
                node = maybe_node
                if maybe_shape is not None:
                    shape = maybe_shape
                    if status == "conformant":
                        successes.append({'node': node, 'shape': shape})
                    else:
                        failures.append({'node': node, 'shape': shape})    
                        conforms = False
                else:
                    logging.info(f"Shape {shape} not found in the shapes list: {shapes}")
            else:
                logging.info(f"Node {node} not found in the nodes list: {nodes}")

    return { 'conforms': conforms, 'message': message, 'failures': failures, 'successes': successes }

def parse_jena_result_line(line):
    regex = re.compile(r'<([^>]+)>\s@\s<([^>]+)>\s.*Status\s=\s(nonconformant|conformant).*')
    m = regex.match(line)
    (node, shape, conforms) = m.group(1,2,3)
    return (node, shape, conforms)

def remove_gt_lt(string):
    """
    Remove the < and > characters from the string
    param:
        string: the string to remove the characters from
    return: the string without the characters
    """
    if string.startswith("<") and string.endswith(">"):
        return string[1:-1]
    else:
        return string

def analyze_validation_report(filename, nodes, shapes, pairs, include_message):
    """
    Analyze the validation report and extract the information about the failures and the conforms property 
    Each failure is a dictionary with the node, message and shape
    param:
        filename: the name of the file to analyze which must contain a SHACL validation report
        nodes: a list of pairs (node, node_iri) with the nodes that we are interested in
        shapes: a list of pairs (shape, shape_iri) with the shapes that we are interested in
        pairs: a list of pairs (node, shape) with the nodes and shapes that we are interested in
    return: a dictionary with the conforms property and a list of failures
    """
    logging.info(f"Analyzing validation report {filename}")
    for pair in pairs:
        nodes.append(pair['node'])
        shapes.append(pair['shape'])

    # Load the validation report
    g = rdflib.Graph()
    g.parse(filename, format='turtle')
    
    # Extract conforms information
    query = """
    PREFIX sh: <http://www.w3.org/ns/shacl#>
    SELECT ?conforms 
    WHERE {
    ?s a sh:ValidationReport ;
         sh:conforms ?conforms .
    }
    """
    result = g.query(query)
    conforms = None
    
    failures = []

    if result.__len__() == 0:
        logging.info("No results found for conforms query.")
        conforms = "Undefined"
    else: 
        row = result.bindings[0]
        if row['conforms'] == rdflib.term.Literal('true', datatype=rdflib.XSD.boolean):
            conforms = True
        else: 
            conforms = False
            failures_query = """
            PREFIX sh: <http://www.w3.org/ns/shacl#>
            SELECT ?focusNode ?sourceShape ?resultMessage
            WHERE {
                ?s a sh:ValidationReport ;
                    sh:result ?failure .
                ?failure sh:focusNode ?focusNode ;
                        sh:resultMessage ?resultMessage ;
                        sh:sourceShape ?sourceShape 
            }
            """
            validation_results = g.query(failures_query)
            for validation_result in validation_results:
                 node = str(validation_result['focusNode'])
                 message = str(validation_result['resultMessage'])
                 shape = str(validation_result['sourceShape'])
                 maybe_node = find_qname(nodes, node)
                 maybe_shape = find_qname(shapes, shape)
                 # We add to the list of failures only the ones that appear in the nodes and shapes that we are interested
                 if maybe_node is not None:
                     node = maybe_node
                     if maybe_shape is not None:
                        shape = maybe_shape
                        if include_message:
                            failures.append({'node': node, 'message': message, 'shape': shape})
                        else:
                            failures.append({'node': node, 'shape': shape})    
                     else:
                         logging.info(f"Shape {shape} not found in the shapes list: {shapes}")
                 else:
                    logging.info(f"Node {node} not found in the nodes list: {nodes}")
    return {'conforms': conforms, 'failures': failures}

def enrich_with_iris(nodes, prefix):
    """
    Enrich the nodes with their IRIs
    param:
        nodes: a list of nodes
        prefix: the prefix to use for the IRIs
    return: a list of pairs (node, node_iri) with the nodes and their IRIs
    """
    iris = []
    for node in nodes:
        node_iri = prefix + node.replace(":","",1)
        iris.append((node, node_iri))
    return iris

def enrich_pairs_with_iris(pairs, prefix):
    """
    Enrich the pairs of node shape with their IRIs
    """
    enriched = []
    for pair in pairs:
        node_iri = prefix + pair['node'].replace(":","",1)
        shape_iri = prefix + pair['shape'].replace(":","",1)
        enriched_pair = { 'node': (pair['node'], node_iri), 'shape': (pair['shape'], shape_iri) }
        enriched.append(enriched_pair)
    return enriched

# Find the qname of an entity in a list of entities
def find_qname(entities, entity):
    for e in entities:
        if e[1] == entity:
            return e[0]
    return None

# Split the file into two files based on a regex pattern
def split_file_by_regex(source, regex, file1, file2):
    with open(source, 'r') as infile, open(file1, 'w') as outfile1, open(file2, 'w') as outfile2:
        for line in infile:
            if regex.match(line):
                outfile1.write(line)
            else:
                outfile2.write(line)

def store_result(name, engine, technology_name, descr, result, results):
    results.append({
        "name": name,
        "engine_name": engine,
        "technology_name": technology_name,
        "description": descr,
        "result": result
    }) 

def prepare_target_declarations(data_graph, shapes_graph, nodes, shapes, pairs, merged_filename):
    """
    Prepare the target declarations for the SHACL shapes
    It creates a new graph which is the result of mergin the data graph, 
    the shapes graph and the target declarations that are obtained from the manifest file
    """
    if not nodes and not shapes and not pairs:
        print("No nodes, shapes or pairs to prepare target declarations")
        return
    
    g = rdflib.Graph()
    g.parse(data_graph, format='turtle')
    g.parse(shapes_graph, format='turtle')
    
    for (shape, shape_iri) in shapes:
        for (node, node_iri) in nodes:
            logging.debug(f"{shape_iri} sh:targetNode {node_iri}")
            g.add((rdflib.URIRef(shape_iri), rdflib.URIRef(shacl_prefix + "targetNode"), rdflib.URIRef(node_iri)))

    for pair in pairs:
        node_iri = pair['node'][1]
        shape_iri = pair['shape'][1]
        g.add((rdflib.URIRef(shape_iri), rdflib.URIRef(shacl_prefix + "targetNode"), rdflib.URIRef(node_iri)))

    logging.debug(f"Merged graph: {g.serialize(format='turtle')}")
    # Save the merged graph to a temp file
    g.serialize(destination=merged_filename, format='turtle')
    logging.debug(f"Serialized graph to {merged_filename}")
    return
