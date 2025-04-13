#!/usr/bin/python
import os
import sys
import argparse
import yaml
import rdflib
import csv
from src.shacl_runners import *

shacl_prefix = "http://www.w3.org/ns/shacl#"
parser = argparse.ArgumentParser(description="Execute Recursion Shapes experiments",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-v", "--verbose", help="increase verbosity", default = 0, action="count")
parser.add_argument("--debug", help="debug info", default = 0, action="count")
parser.add_argument("--temp", help="Temporal folder", default = "temp", action="store")
parser.add_argument("--include-message", help="Include messages in output", default = False, action="store_true")
parser.add_argument("-m", "--manifest", help="Manifest file (in YAML format)", default = "manifest.yaml", action="store")
parser.add_argument("-o", "--output", help="Output file (in YAML format)", default = None, action="store")
parser.add_argument("-f", "--format", help="Output format (yaml or csv)", default = "yaml", action="store")
args = parser.parse_args()
config = vars(args)


# Load the YAML manifest file
with open(config['manifest'], 'r') as file:
    manifest = yaml.safe_load(file)
    debug(config, f"Manifest loaded: {manifest}")

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
    info(config,f"Running test: {test}")
    engine = test['engine']
    name = test['name']
    prefix = test['default_prefix']
    data_graph = os.path.join(manifest['rdf_folder'], test['data_graph'])
    shapes_graph = os.path.join(manifest['shacl_folder'],test['shapes_graph'])
    g = rdflib.Graph()
    g.parse(data_graph, format='turtle')
    g.parse(shapes_graph, format='turtle')
    nodes = []
    shapes = []
    # Prepare target declarations and list of nodes and shapes
    for shape in test['shapes']:
        shape_iri = prefix + shape.replace(":","",1)
        shapes.append((shape, shape_iri))
        for node in test['nodes']:
            node_iri = prefix + node.replace(":","",1)
            debug(config, f"{shape_iri} sh:targetNode {node_iri}")
            nodes.append((node, node_iri))
            g.add((rdflib.URIRef(shape_iri), rdflib.URIRef(shacl_prefix + "targetNode"), rdflib.URIRef(node_iri)))

    debug(config, f"Merged graph: {g.serialize(format='turtle')}")
    # Save the merged graph to a file
    merged_filename = os.path.join(temp, name + ".ttl")
    g.serialize(destination=merged_filename, format='turtle')

    debug(config, f"Serialized graph to {merged_filename}")
    results = []
    if engine == "shacl":
        for technology in manifest['shacl_technologies']:
            if technology == "shacl_tq":
                shacl_tq(merged_filename, name, results_folder, config, results, nodes, shapes)
            elif technology == "jena_shacl":
                jena_shacl(merged_filename, name, results_folder, config, results, nodes, shapes)
            elif technology == "shaclex":
                shaclex(merged_filename, name, results_folder, config, results, nodes, shapes)
            elif technology == "pyshacl":
                pyshacl(merged_filename, name, results_folder, config, results, nodes, shapes)

    if config['output'] is not None:
        output_file = config['output']
        file = open(output_file, 'w')
    else:
        file = sys.stdout
    match config["format"]:
        case "yaml":
                yaml.dump(results, file)
        case "csv":
                writer = csv.writer(file)
                writer.writerow(["name", "technology", "conforms", "failures"])
                for entry in results:
                    name = entry['name']
                    technology_name = entry['technology_name']
                    result = entry['result']
                    conforms = result['conforms']
                    failures = result['failures']
                    writer.writerow([name, technology_name, conforms, failures])
        case _:
            print("Unknown format. Supported formats are yaml and csv.")
            exit(1)

    


