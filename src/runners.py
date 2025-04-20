from enum import Enum
import os
import re
import subprocess
import rdflib
import json

class CommandResult(Enum):
    OK = 0
    TIMEOUT = 1
    ERROR = 2
    EXCEPTION = 3

shacl_prefix = "http://www.w3.org/ns/shacl#"

def run(command, output_filename, timeout = 2, debug = False):
    result = CommandResult.ERROR
    try:
        with open(output_filename, "w") as output:
            if debug:
                command_str = " ".join(command) + " > " + str(output_filename)
                print(f"Command: {command_str}")
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

def mk_command(command, filename, output):
    return list(map(lambda x: 
                       x.replace("$data_filename", filename)
                       .replace("$validation_report_file", output), command))

def mk_command_shex(command, data_filename, shex_filename, shapemap_filename, output):
    return list(map(lambda x: 
                       x.replace("$data_filename", data_filename)
                       .replace("$shex_filename", shex_filename)
                       .replace("$shapemap_filename", shapemap_filename)
                       .replace("$output_filename", output), command))

pyshacl_cmd = ["bin/pyshacl", "-o", "$validation_report_file", "--format", "turtle", "$data_filename" ]

shacl_tq_cmd = ["bin/shacl-1.4.4/bin/shaclvalidate.sh","-datafile", "$data_filename"]

shaclex_shacl_cmd = ["bin/shaclex-0.2.7/bin/shaclex",
                     "--validate",
                     "--engine","SHACLEX",
                     "--data", "$data_filename",
                     "--validationReportFormat","TURTLE",
                     "--showValidationReport",
                     "--validationReportFile", "$validation_report_file"
                     ]

shaclex_shex_cmd = ["bin/shaclex-0.2.7/bin/shaclex", 
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


jena_shacl_cmd = ["bin/apache-jena-5.3.0/bin/shacl", "v", "--data", "$data_filename"]

def shacl_tq(filename, name, descr, results_folder, config, results, nodes, shapes,pairs):
    try:
        technology_name = "shacl_tq"
        engine = "shacl"
        temp = config['temp']
        validation_report_file_temp = os.path.join(temp, f"{name}_{technology_name}_results_temp.ttl")
        # output_file_temp = os.path.join(temp, f"{name}_{technology_name}_output_temp.txt")
        command = mk_command(shacl_tq_cmd, filename, validation_report_file_temp)
        result1 = run(command, validation_report_file_temp, 5, config['debug'])
        if result1 == CommandResult.OK:
            validation_report_file = os.path.join(results_folder, f"{name}_{technology_name}_results_temp.ttl")
            validation_output = os.path.join(results_folder, f"{name}_{technology_name}_output.txt")
            regex = re.compile('.*Failure.*')
            split_file_by_regex(validation_report_file_temp, regex, validation_output, validation_report_file)
            result = analyze_validation_report(validation_report_file, nodes, shapes,pairs,config)
        else:
            result = { 'conforms': "Error", 'failures': "Error running command" + str(result1) }    
        store_result(name, engine, technology_name, descr, result, results)
    except Exception as e:
        info(config, f"Error running {technology_name}: {e}")
        result = { 'conforms': "Exception", 'failures': f"{e}" }
        store_result(name, engine, technology_name, descr, result, results)

def jena_shacl(filename, name, descr, results_folder, config, results, nodes, shapes,pairs):
    try:
        technology_name = "jena_shacl"
        engine = "shacl"
        validation_report_file = os.path.join(results_folder, f"{name}_{technology_name}_results.ttl")
        # output = os.path.join(results_folder, f"{name}_{technology_name}_output.txt")
        command = mk_command(jena_shacl_cmd, filename, validation_report_file)
        result1 = run(command, validation_report_file, 5, config['debug'])
        if result1 == CommandResult.OK:
            debug(config, f"Command result is OK...validation report file: {validation_report_file}")
            result = analyze_validation_report(validation_report_file,nodes,shapes,pairs,config)
            store_result(name, engine, technology_name, descr, result, results)
        else:
            result = { 'conforms': "Error", 'failures': "Error running command" + str(result1) }    
            store_result(name, engine, technology_name, descr, result, results)    
    except Exception as e:
        info(config, f"Error running {technology_name}: {e}")
        result = { 'conforms': "Exception", 'failures': f"{e}" }
        store_result(name, engine, technology_name, descr, result, results)

def shaclex_shacl(filename, name, descr, results_folder, config, results, nodes, shapes,pairs):
    try:
        technology_name = "shaclex_shacl"
        engine = "shacl"
        validation_report_file = os.path.join(results_folder, f"{name}_{technology_name}_results.ttl")
        validation_output = os.path.join(results_folder, f"{name}_{technology_name}_output.txt")
        command = mk_command(shaclex_shacl_cmd, filename, validation_report_file)
        info(config, f"Running: {command}")
        result1 = run(command, validation_output, 5, config['debug'])
        if result1 == CommandResult.OK:
            result = analyze_validation_report(validation_report_file,nodes,shapes,pairs,config)
            store_result(name, engine, technology_name, descr, result, results)
        else:
            result = { 'conforms': "Error", 'failures': "Error running command" + str(result1) }    
            store_result(name, engine, technology_name, descr, result, results)
    except Exception as e:
        info(config, f"Error running {technology_name}: {e}")
        result = { 'conforms': "Exception", 'failures': f"{e}" }
        store_result(name, engine, technology_name, descr, result, results)

def shaclex_shex(filename, shex_filename, shapemap_filename, name, descr, results_folder, config, results, nodes, shapes, pairs):
    try:
        technology_name = "shex_s"
        engine = "shex"
        # output_shapemap = os.path.join(results_folder, f"{name}_{technology_name}_output_shapemap.txt")
        validation_output = os.path.join(results_folder, f"{name}_{technology_name}_output.json")
        command = mk_command_shex(shaclex_shex_cmd, filename, shex_filename, shapemap_filename, validation_output)
        info(config, f"Running: {command}")
        result1 = run(command, validation_output, 5, config['debug'])
        if result1 == CommandResult.OK:
            print(f"Command result is OK...before analyzing shapemap file: {validation_output}")
            result = analyze_shapemap(validation_output,nodes,shapes,pairs,config)
            store_result(name, engine, technology_name, descr, result, results)
        else:
            result = { 'conforms': "Error", 'failures': "Error running command" + str(result1) }    
            store_result(name, engine, technology_name, descr, result, results)
    except Exception as e:
        info(config, f"Error running {technology_name}: {e}")
        result = { 'conforms': "Exception", 'failures': f"{e}" }
        store_result(name, engine, technology_name, descr, result, results)

# Run pyshacl validation
def pyshacl(filename, name, descr, results_folder, config, results, nodes, shapes, pairs):
    try:
        technology_name = "pyshacl"
        engine = "shacl"
        validation_report_file = os.path.join(results_folder, f"{name}_{technology_name}_results.ttl")
        validation_output = os.path.join(results_folder, f"{name}_{technology_name}_output.txt")
        command = mk_command(pyshacl_cmd, filename, validation_report_file)
        result1 = run(command, validation_output, 2, config['debug'])
        if result1 == CommandResult.OK:
            result = analyze_validation_report(validation_report_file, nodes, shapes, pairs, config)
            store_result(name, engine, technology_name, descr, result, results)
        else:
            result = { 'conforms': "Error", 'failures': "Error running command" + str(result1) }    
            store_result(name, engine, technology_name, descr, result, results)    
    except Exception as e:
        info(config, f"Error running {name} with {technology_name}: {e}")
        result = { 'conforms': "Exception", 'failures': f"{e}" }
        store_result(name, engine, technology_name, descr, result, results)

def prepare_shapemap(nodes, shapes, pairs, merged_filename, config):
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
        debug(config, f"Writing shapemap {shapemap}\n in file {merged_filename}")
        outfile.write(shapemap)

def analyze_shapemap(filename,nodes,shapes,pairs,config):
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
        print(f"JSON result: {json_result}")
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
                        info(config, f"Shape {shape} not found in the shapes list: {shapes}")
                else:
                    info(config, f"Node {node} not found in the nodes list: {nodes}")                                          
    print(f"After analyzing shapemap, Conforms: {conforms}")                    
    return { 'conforms': conforms, 'message': message, 'failures': failures, 'successes': successes }

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
    
def analyze_validation_report(filename,nodes,shapes,pairs,config):   
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
        info(config, "No results found for conforms query.")
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
                        if config['include_message']:
                            failures.append({'node': node, 'message': message, 'shape': shape})
                        else:
                            failures.append({'node': node, 'shape': shape})    
                     else:
                         info(config, f"Shape {shape} not found in the shapes list: {shapes}")
                 else:
                    info(config, f"Node {node} not found in the nodes list: {nodes}")                 
    return { 'conforms': conforms, 'failures': failures }

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

def info(config, string):
    if config['verbose'] > 0:
        print(string)

def debug(config, string):
    if config['debug'] > 0:
        print(string)        

def prepare_target_declarations(data_graph, shapes_graph, nodes, shapes, pairs, merged_filename, config):
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
            debug(config, f"{shape_iri} sh:targetNode {node_iri}")
            g.add((rdflib.URIRef(shape_iri), rdflib.URIRef(shacl_prefix + "targetNode"), rdflib.URIRef(node_iri)))

    for pair in pairs:
        node_iri = pair['node'][1]
        shape_iri = pair['shape'][1]
        g.add((rdflib.URIRef(shape_iri), rdflib.URIRef(shacl_prefix + "targetNode"), rdflib.URIRef(node_iri)))
    
    debug(config, f"Merged graph: {g.serialize(format='turtle')}")
    # Save the merged graph to a temp file
    g.serialize(destination=merged_filename, format='turtle')
    debug(config, f"Serialized graph to {merged_filename}")
    return

    