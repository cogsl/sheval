import os
import re
import subprocess
import rdflib

def shacl_tq(filename, name, results_folder, config, results, nodes, shapes):
    try:
        technology_name = "shacl_tq"
        temp = config['temp']
        validation_report_file_temp = os.path.join(temp, f"{name}_{technology_name}_results_temp.ttl")
        command = f"shaclvalidate.sh -datafile {filename} > {validation_report_file_temp}"
        info(config, f"Running {command}")
        isRunOk , cmdOutStr = getCommandOutput(command, "utf-8", 2)
        debug(config, f"Run OK:{isRunOk}\nCommand output:\n{cmdOutStr}")
        # In the case of SHACL TQ the validation report includes the errors at the start of the file
        # and the rest of the file is the proper validation report
        # We split the file into two files, one with the errors and one with the validation report in Turtle
        validation_report_file = os.path.join(results_folder, f"{name}_{technology_name}_results_temp.ttl")
        validation_output = os.path.join(results_folder, f"{name}_{technology_name}_output.txt")
        regex = re.compile('.*Failure.*')
        split_file_by_regex(validation_report_file_temp, regex, validation_output, validation_report_file)
        result = analyze_validation_report(validation_report_file, nodes, shapes,config)
        store_result(name, technology_name, result, results)
    except Exception as e:
        info(config, f"Error running {technology_name}: {e}")
        result = { 'conforms': "Exception", 'failures': f"{e}" }
        store_result(name, technology_name, result, results)

def jena_shacl(filename, name, results_folder, config, results, nodes, shapes):
    try:
        technology_name = "jena_shacl"
        validation_report_file = os.path.join(results_folder, f"{name}_{technology_name}_results.ttl")
        # validation_output = os.path.join(results_folder, f"{name}_{technology_name}_output.txt")
        command = f"shacl v {filename} > {validation_report_file}"
        info(config, f"Running: {command}")
        isRunOk , cmdOutStr = getCommandOutput(command, "utf-8", 2)
        debug(config, f"Run OK:{isRunOk}\nCommand output:\n{cmdOutStr}")
        result = analyze_validation_report(validation_report_file,nodes,shapes,config)
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
        command = f"shaclex --validate --engine SHACLEX --data {filename} --validationReportFormat TURTLE --showValidationReport --validationReportFile {validation_report_file} > {validation_output}"
        info(config, f"Running: {command}")
        isRunOk , cmdOutStr = getCommandOutput(command, "utf-8", 2)
        debug(config, f"Run OK:{isRunOk}\nCommand output:\n{cmdOutStr}")
        result = analyze_validation_report(validation_report_file,nodes,shapes,config)
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
        command = f"pyshacl {filename} -o {validation_report_file} --format turtle > {validation_output}"
        info(config, f"Running: {command}")
        isRunOk , cmdOutStr = getCommandOutput(command, "utf-8", 2)
        debug(config, f"Run OK:{isRunOk}\nCommand output:\n{cmdOutStr}")
        result = analyze_validation_report(validation_report_file, nodes, shapes, config)
        store_result(name, technology_name, result, results)
    except Exception as e:
        info(config, f"Error running {technology_name}: {e}")
        result = { 'conforms': "Exception", 'failures': f"{e}" }
        store_result(name, technology_name, result, results)
    
# The following code has been borrowed from: https://stackoverflow.com/questions/41094707/setting-timeout-when-using-os-system-function 
def getCommandOutput(consoleCommand, consoleOutputEncoding="utf-8", timeout=2):
    """get command output from terminal

    Args:
        consoleCommand (str): console/terminal command string
        consoleOutputEncoding (str): console output encoding, default is utf-8
        timeout (int): wait max timeout for run console command
    Returns:
        console output (str)
    Raises:
    """
    # print("getCommandOutput: consoleCommand=%s" % consoleCommand)
    isRunCmdOk = False
    consoleOutput = ""
    try:
        # consoleOutputByte = subprocess.check_output(consoleCommand)
        consoleOutputByte = subprocess.check_output(consoleCommand, shell=True, timeout=timeout)

        # commandPartList = consoleCommand.split(" ")
        # print("commandPartList=%s" % commandPartList)
        # consoleOutputByte = subprocess.check_output(commandPartList)
        # print("type(consoleOutputByte)=%s" % type(consoleOutputByte)) # <class 'bytes'>
        # print("consoleOutputByte=%s" % consoleOutputByte) # b'640x360\n'

        consoleOutput = consoleOutputByte.decode(consoleOutputEncoding) # '640x360\n'
        consoleOutput = consoleOutput.strip() # '640x360'
        isRunCmdOk = True
    except subprocess.CalledProcessError as callProcessErr:
        cmdErrStr = str(callProcessErr)
        print("Error %s for run command %s" % (cmdErrStr, consoleCommand))

    # print("isRunCmdOk=%s, consoleOutput=%s" % (isRunCmdOk, consoleOutput))
    return isRunCmdOk, consoleOutput

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