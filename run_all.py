#!/usr/bin/python
import os
import argparse
import yaml
import rdflib

shacl_prefix = "http://www.w3.org/ns/shacl#"

def shacl_tq(folder, filename, name, results_folder, config):
    complete_path = os.path.join(folder, filename)
    technology_name = "shacl_tq"
    command = f"shaclvalidate.sh -datafile {complete_path} > {results_folder}/{name}_{technology_name}.results"
    if config['verbose'] > 0 :
        print(f"Running: {command}")
    os.system(command)

def shacl_jena(folder, filename, name, results_folder, config):
    complete_path = os.path.join(folder, filename)
    technology_name = "shacl_jena"
    # Construct the command to run the test
    command = f"shacl v {complete_path} > {results_folder}/{name}_{technology_name}.results"
    if config['verbose'] > 0 :
        print(f"Running: {command}")
    os.system(command)

def shaclex(folder, filename, name, results_folder, config):
    complete_path = os.path.join(folder, filename)
    technology_name = "shaclex"
    command = f"shaclex --validate --engine SHACLEX --data {complete_path} --validationReportFormat TURTLE --showValidationReport > {results_folder}/{name}_{technology_name}.results"
    if config['verbose'] > 0 :
        print(f"Running: {command}")
    os.system(command)

def pyshacl(folder, filename, name, results_folder, config):
    complete_path = os.path.join(folder, filename)
    technology_name = "pyshacl"
    command = f"pyshacl {complete_path} > {results_folder}/{name}_{technology_name}.results"
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
    filename = test['filename']
    print(f"filename: {filename}")
    engine = test['engine']
    name = test['name']
    g = rdflib.Graph()
    shape = test['default_prefix'] + test['shape'].replace(":","",1)

    # Prepare target declarations
    for node in test['nodes']:
        clean_node = node.replace(":","",1)
        print(f"node: {test['default_prefix']}{clean_node}")
        g.add((rdflib.URIRef(shape), rdflib.URIRef(shacl_prefix + "targetNode"), rdflib.URIRef(node)))
    print(f"g: {g}")

    if engine == "shacl":
        shacl_tq(shacl_folder,filename, name, results_folder, config)
        shacl_jena(shacl_folder,filename, name, results_folder,config)
        shaclex(shacl_folder,filename, name, results_folder,config)
        pyshacl(shacl_folder,filename, name, results_folder,config)
