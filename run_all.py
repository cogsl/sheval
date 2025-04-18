#!/usr/bin/python
import os
import sys
import argparse
import yaml
import csv
from src.runners import *

parser = argparse.ArgumentParser(description="Execute Recursion Shapes experiments",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-v", "--verbose", help="increase verbosity", default = 0, action="count")
parser.add_argument("--debug", help="debug info", default = 0, action="count")
parser.add_argument("--temp", help="Temporal folder", default = "temp", action="store")
parser.add_argument("--include-message", help="Include messages in output", default = False, action="store_true")
parser.add_argument("-n", "--name", help="Name of test", default = None, action="store")
parser.add_argument("-e", "--engine", help="Engine (can be shacl or shex)", default = None, action="store")
parser.add_argument("-t", "--technology", help="Technology (specific technology like shacl_tq, shaclex, ...)", default = None, action="store")
parser.add_argument("-m", "--manifest", help="Manifest file (in YAML format)", default = "manifest.yaml", action="store")
parser.add_argument("-o", "--output", help="Output file (in YAML format)", default = None, action="store")
parser.add_argument("-f", "--format", help="Output format (yaml or csv)", default = "yaml", action="store")
args = parser.parse_args()
config = vars(args)


# Load the YAML manifest file
with open(config['manifest'], 'r') as file:
    manifest = yaml.safe_load(file)
    debug(config, f"Manifest loaded: {len(manifest['tests'])} tests")

shacl_folder = manifest['shacl_folder']
shex_folder = manifest['shex_folder']
results_folder = manifest['results_folder']
results = []

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
    name = test['name']
    if config['name'] is None or name == config['name']:
        info(config,f"Test name: {name}")
        engine = test['engine']
        if config['engine'] is None or engine == config['engine']:
            info(config,f"Test engine: {engine}")
            prefix = test['default_prefix']
            data_graph = os.path.join(manifest['rdf_folder'], test['data_graph'])
            nodes = test['nodes']
            shapes = test['shapes']
            prefix = test['default_prefix']
            nodes = enrich_with_iris(nodes,prefix)
            shapes = enrich_with_iris(shapes,prefix)
            
            if engine == "shacl":
                shapes_graph = os.path.join(manifest['shacl_folder'],test['shapes_graph'])
                merged_filename = os.path.join(config['temp'], test['name'] + ".ttl")
                prepare_target_declarations(data_graph, shapes_graph, nodes, shapes, prefix, merged_filename, config)
                if config['technology'] is not None:
                    technologies = [config['technology']]
                else:
                    technologies = manifest['shacl_technologies']
                for technology in technologies:
                    if technology == "shacl_tq":
                        shacl_tq(merged_filename, name, results_folder, config, results, nodes, shapes)
                    elif technology == "jena_shacl":
                        jena_shacl(merged_filename, name, results_folder, config, results, nodes, shapes)
                    elif technology == "shaclex_shacl":
                        shaclex_shacl(merged_filename, name, results_folder, config, results, nodes, shapes)
                    elif technology == "pyshacl":
                        pyshacl(merged_filename, name, results_folder, config, results, nodes, shapes)
                    else:
                        print(f"Unknown technology: {technology}")
                        exit(1)
            elif engine == "shex":
                print(f"Running Shex for {name}")
                data_file = os.path.join(manifest['rdf_folder'], test['data_graph'])
                shex_file = os.path.join(manifest['shex_folder'], test['shex_file'] )
                shapemap_file = os.path.join(config['temp'], test['name'] + ".sm" )
                prepare_shapemap(nodes, shapes, prefix, shapemap_file, config)
                if config['technology'] is not None:
                    technologies = [config['technology']]
                else:
                    technologies = manifest['shex_technologies']
                for technology in manifest['shex_technologies']:
                    if technology == "shacl_shex":
                        shaclex_shex(data_file, shex_file, shapemap_file, name, results_folder, config, results, nodes, shapes)
                    else:
                        print(f"Unknown technology: {technology}")
                        exit(1)    
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
                    writer.writerow(["name", "technology", "conforms", "failures", "successes"])
                    for entry in results:
                        name = entry['name']
                        technology_name = entry['technology_name']
                        result = entry['result']
                        conforms = result['conforms']
                        failures = result['failures']
                        if 'successes' in result:
                            successes = result['successes']
                        else:
                            successes = []
                        writer.writerow([name, technology_name, conforms, failures, successes])
                case _:
                    print("Unknown format. Supported formats are yaml and csv.")
                    exit(1)

    


