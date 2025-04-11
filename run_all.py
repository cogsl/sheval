#!/usr/bin/python
import os
import argparse
import yaml
import rdflib

shacl_prefix = "http://www.w3.org/ns/shacl#"

def shacl_tq(filename, name, results_folder, config):
    technology_name = "shacl_tq"
    command = f"shaclvalidate.sh -datafile {filename} > {results_folder}/{name}_{technology_name}.results"
    if config['verbose'] > 0 :
        print(f"Running: {command}")
    os.system(command)

def shacl_jena(filename, name, results_folder, config):
    technology_name = "shacl_jena"
    # Construct the command to run the test
    command = f"shacl v {filename} > {results_folder}/{name}_{technology_name}.results"
    if config['verbose'] > 0 :
        print(f"Running: {command}")
    os.system(command)

def shaclex(filename, name, results_folder, config):
    technology_name = "shaclex"
    command = f"shaclex --validate --engine SHACLEX --data {filename} --validationReportFormat TURTLE --showValidationReport > {results_folder}/{name}_{technology_name}.results"
    if config['verbose'] > 0 :
        print(f"Running: {command}")
    os.system(command)

def pyshacl(filename, name, results_folder, config):
    technology_name = "pyshacl"
    command = f"pyshacl {filename} > {results_folder}/{name}_{technology_name}.results"
    if config['verbose'] > 0 :
        print(f"Running: {command}")
    os.system(command)

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
    merged_filename = os.path.join(temp, filename)
    g.serialize(destination=merged_filename, format='turtle')
    print(f"Serialized graph to {merged_filename}")
    
    if engine == "shacl":
        shacl_tq(merged_filename, name, results_folder, config)
        shacl_jena(merged_filename, name, results_folder,config)
        shaclex(merged_filename, name, results_folder,config)
        pyshacl(merged_filename, name, results_folder,config)
