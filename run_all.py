#!/usr/bin/python
import os
import argparse
import re
import yaml
import rdflib

shacl_prefix = "http://www.w3.org/ns/shacl#"

def shacl_tq(filename, name, results_folder, config, results):
    technology_name = "shacl_tq"
    temp = config['temp']
    validation_report_file_temp = os.path.join(temp, f"{name}_{technology_name}_results_temp.ttl")
    command = f"shaclvalidate.sh -datafile {filename} > {validation_report_file_temp}"
    if config['verbose'] > 0 :
        print(f"Running: {command}")
    os.system(command)
    validation_report_file = os.path.join(results_folder, f"{name}_{technology_name}_results_temp.ttl")
    validation_output = os.path.join(results_folder, f"{name}_{technology_name}_output.txt")
    regex = re.compile('.*Failure.*')
    split_file_by_regex(validation_report_file_temp, regex, validation_output, validation_report_file)
    result = analyze_validation_report(validation_report_file)
    store_result(name, technology_name, result, results)

def shacl_jena(filename, name, results_folder, config, results):
    technology_name = "shacl_jena"
    validation_report_file = os.path.join(results_folder, f"{name}_{technology_name}_results.ttl")
    # validation_output = os.path.join(results_folder, f"{name}_{technology_name}_output.txt")
    command = f"shacl v {filename} > {validation_report_file}"
    if config['verbose'] > 0 :
        print(f"Running: {command}")
    os.system(command)
    result = analyze_validation_report(validation_report_file)
    store_result(name, technology_name, result, results)

def shaclex(filename, name, results_folder, config, results):
    technology_name = "shaclex"
    validation_report_file = os.path.join(results_folder, f"{name}_{technology_name}_results.ttl")
    validation_output = os.path.join(results_folder, f"{name}_{technology_name}_output.txt")
    command = f"shaclex --validate --engine SHACLEX --data {filename} --validationReportFormat TURTLE --showValidationReport --validationReportFile {validation_report_file} > {validation_output}"
    if config['verbose'] > 0 :
        print(f"Running: {command}")
    os.system(command)
    result = analyze_validation_report(validation_report_file)
    store_result(name, technology_name, result, results)

def pyshacl(filename, name, results_folder, config, results):
    technology_name = "pyshacl"
    validation_report_file = os.path.join(results_folder, f"{name}_{technology_name}_results.ttl")
    validation_output = os.path.join(results_folder, f"{name}_{technology_name}_output.txt")
    command = f"pyshacl {filename} -o {validation_report_file} --format turtle > {validation_output}"
    if config['verbose'] > 0 :
        print(f"Running: {command}")
    os.system(command)
    result = analyze_validation_report(validation_report_file)
    print(f"Result: {result}")
    store_result(name, technology_name, result, results)

def analyze_validation_report(filename):
    # Load the validation report
    g = rdflib.Graph()
    g.parse(filename, format='turtle')

    # Extract the number of violations
    query = """
        SELECT ?conforms
        WHERE {
            ?s a sh:ValidationResult .
            ?s sh:conforms ?conforms .
        }
    """
    result = g.query(query)
    for row in result:
        conforms = row[0]
        if conforms == rdflib.Literal("true"):
            print("The data graph conforms to the SHACL shapes.")
        else:
            print("The data graph does not conform to the SHACL shapes.")
    return result


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
    
    
parser = argparse.ArgumentParser(description="Execute Recursion Shapes experiments",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-v", "--verbose", help="increase verbosity", default = 0, action="count")
parser.add_argument("--temp", help="Temporal folder", default = "temp", action="store")
parser.add_argument("-m", "--manifest", help="Manifest file (in YAML format)", default = "manifest.yaml", action="store")
args = parser.parse_args()
config = vars(args)
print(f"Config options: {config}")


# Load the YAML manifest file
with open(config['manifest'], 'r') as file:
    manifest = yaml.safe_load(file)
    if config['verbose'] > 0:
        print(f"Manifest loaded: {manifest}")

shacl_folder = manifest['shacl_folder']
shex_folder = manifest['shex_folder']
results_folder = manifest['results_folder']

# Check if the results folder exists or create it
if not os.path.exists(results_folder):
    os.makedirs(results_folder)

temp = config['temp']
# Check if the results folder exists or create it
if not os.path.exists(temp):
    os.makedirs(temp)

# Check if the SHACL folder exists
if not os.path.exists(shacl_folder):
    print("SHACL folder {shacl_folder} does not exist")
    exit(1)

for test in manifest['tests']:
    print(f"Running test: {test}")
    engine = test['engine']
    name = test['name']
    prefix = test['default_prefix']
    data_graph = os.path.join(manifest['rdf_folder'], test['data_graph'])
    shapes_graph = os.path.join(manifest['shacl_folder'],test['shapes_graph'])
    g = rdflib.Graph()
    g.parse(data_graph, format='turtle')
    g.parse(shapes_graph, format='turtle')

    # Prepare target declarations
    for shape in test['shapes']:
        shape_iri = prefix + shape.replace(":","",1)
        for node in test['nodes']:
            node_iri = prefix + node.replace(":","",1)
            print(f"{shape_iri} sh:targetNode {node_iri}")
            g.add((rdflib.URIRef(shape_iri), rdflib.URIRef(shacl_prefix + "targetNode"), rdflib.URIRef(node_iri)))

    print(f"Merged graph: {g.serialize(format='turtle')}")
    # Save the merged graph to a file
    merged_filename = os.path.join(temp, name + ".ttl")
    g.serialize(destination=merged_filename, format='turtle')

    print(f"Serialized graph to {merged_filename}")
    results = []
    if engine == "shacl":
        shacl_tq(merged_filename, name, results_folder, config, results)
        shacl_jena(merged_filename, name, results_folder,config, results)
        shaclex(merged_filename, name, results_folder,config, results)
        pyshacl(merged_filename, name, results_folder,config, results)
    print(f"Results: {results}")


