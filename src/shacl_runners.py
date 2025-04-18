from enum import Enum
import os
import re
import subprocess
import rdflib

class CommandResult(Enum):
    OK = 0
    TIMEOUT = 1
    ERROR = 2
    EXCEPTION = 3

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
                       x.replace("$filename", filename)
                       .replace("$validation_report_file", output), command))

pyshacl_cmd = ["bin/pyshacl", "-o", "$validation_report_file", "--format", "turtle", "$filename" ]

shacl_tq_cmd = ["bin/shacl-1.4.4/bin/shaclvalidate.sh","-datafile", "$filename"]

shaclex_cmd = ["bin/shaclex-0.2.6/bin/shaclex","--validate","--engine","SHACLEX","--data", "$filename","--validationReportFormat","TURTLE","--showValidationReport","--validationReportFile", "$validation_report_file"]

jena_shacl_cmd = ["bin/apache-jena-5.3.0/bin/shacl", "v", "--data", "$filename"]

def shacl_tq(filename, name, results_folder, config, results, nodes, shapes):
    try:
        technology_name = "shacl_tq"
        temp = config['temp']
        validation_report_file_temp = os.path.join(temp, f"{name}_{technology_name}_results_temp.ttl")
        output_file_temp = os.path.join(temp, f"{name}_{technology_name}_output_temp.txt")
        command = mk_command(shacl_tq_cmd, filename, validation_report_file_temp)
        result1 = run(command, validation_report_file_temp, 4, config['debug'])
        if result1 == CommandResult.OK:
            validation_report_file = os.path.join(results_folder, f"{name}_{technology_name}_results_temp.ttl")
            validation_output = os.path.join(results_folder, f"{name}_{technology_name}_output.txt")
            regex = re.compile('.*Failure.*')
            split_file_by_regex(validation_report_file_temp, regex, validation_output, validation_report_file)
            result = analyze_validation_report(validation_report_file, nodes, shapes,config)
        else:
            result = { 'conforms': "Error", 'failures': "Error running command" + str(result1) }    
        store_result(name, technology_name, result, results)
    except Exception as e:
        info(config, f"Error running {technology_name}: {e}")
        result = { 'conforms': "Exception", 'failures': f"{e}" }
        store_result(name, technology_name, result, results)

def jena_shacl(filename, name, results_folder, config, results, nodes, shapes):
    try:
        technology_name = "jena_shacl"
        validation_report_file = os.path.join(results_folder, f"{name}_{technology_name}_results.ttl")
        # output = os.path.join(results_folder, f"{name}_{technology_name}_output.txt")
        command = mk_command(jena_shacl_cmd, filename, validation_report_file)
        result1 = run(command, validation_report_file, 2, config['debug'])
        if result1 == CommandResult.OK:
            debug(config, f"Command result is OK...validation report file: {validation_report_file}")
            result = analyze_validation_report(validation_report_file,nodes,shapes,config)
            store_result(name, technology_name, result, results)
        else:
            result = { 'conforms': "Error", 'failures': "Error running command" + str(result1) }    
            store_result(name, technology_name, result, results)    
    except Exception as e:
        info(config, f"Error running {technology_name}: {e}")
        result = { 'conforms': "Exception", 'failures': f"{e}" }
        store_result(name, technology_name, result, results)

def shaclex(filename, name, results_folder, config, results, nodes, shapes):
    try:
        technology_name = "shaclex"
        validation_report_file = os.path.join(results_folder, f"{name}_{technology_name}_results.ttl")
        validation_output = os.path.join(results_folder, f"{name}_{technology_name}_output.txt")
        command = mk_command(shaclex_cmd, filename, validation_report_file)
        info(config, f"Running: {command}")
        result1 = run(command, validation_output, 5, config['debug'])
        if result1 == CommandResult.OK:
            result = analyze_validation_report(validation_report_file,nodes,shapes,config)
            store_result(name, technology_name, result, results)
        else:
            result = { 'conforms': "Error", 'failures': "Error running command" + str(result1) }    
            store_result(name, technology_name, result, results)
    except Exception as e:
        info(config, f"Error running {technology_name}: {e}")
        result = { 'conforms': "Exception", 'failures': f"{e}" }
        store_result(name, technology_name, result, results)

# Run pyshacl validation
def pyshacl(filename, name, results_folder, config, results, nodes, shapes):
    try:
        technology_name = "pyshacl"
        validation_report_file = os.path.join(results_folder, f"{name}_{technology_name}_results.ttl")
        validation_output = os.path.join(results_folder, f"{name}_{technology_name}_output.txt")
        command = mk_command(pyshacl_cmd, filename, validation_report_file)
        result1 = run(command, validation_output, 2, config['debug'])
        if result1 == CommandResult.OK:
            result = analyze_validation_report(validation_report_file, nodes, shapes, config)
            store_result(name, technology_name, result, results)
        else:
            result = { 'conforms': "Error", 'failures': "Error running command" + str(result1) }    
            store_result(name, technology_name, result, results)    
    except Exception as e:
        info(config, f"Error running {name} with {technology_name}: {e}")
        result = { 'conforms': "Exception", 'failures': f"{e}" }
        store_result(name, technology_name, result, results)
    
def analyze_validation_report(filename,nodes,shapes,config):   
    """
    Analyze the validation report and extract the information about the failures and the conforms property 
    Each failure is a dictionary with the node, message and shape
    param:
        filename: the name of the file to analyze which must contain a SHACL validation report
        nodes: a list of pairs (node, node_iri) with the nodes that we are interested in
        shapes: a list of pairs (shape, shape_iri) with the shapes that we are interested in
    return: a dictionary with the conforms property and a list of failures
    """
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

def store_result(name, technology_name, result, results):
    results.append({
        "name": name,
        "technology_name": technology_name,
        "result": result
    }) 

def info(config, string):
    if config['verbose'] > 0:
        print(string)

def debug(config, string):
    if config['debug'] > 0:
        print(string)        