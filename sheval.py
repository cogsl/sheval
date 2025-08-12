#!/usr/bin/python3
import os
import sys
import argparse
import yaml
import csv
from src.runners import *
import logging

COLORS = {
    'DEBUG': '\033[36m',    # Cyan
    'INFO': '\033[32m',     # Green
    'WARNING': '\033[33m',  # Yellow
    'ERROR': '\033[31m',    # Red
    'CRITICAL': '\033[41m', # Red background
    'RESET': '\033[0m'      # Reset to default
}

class ColorFormatter(logging.Formatter):
    def format(self, record):
        color = COLORS.get(record.levelname, COLORS['RESET'])
        message = super().format(record)
        return f"{color}{message}{COLORS['RESET']}"

def save_results_yaml(results, output):
    if output is not None:
        output_file = output + ".yaml"
        file = open(output_file, 'w')
    else:
        file = sys.stdout
        output_file = None
    yaml.dump(results, file)
    if output_file is not None:
        file.close()
        logging.info(f"Results saved to YAML {output_file}")

def save_results_csv(results, output, include_description):
    if output is not None:
        output_file = output + ".csv"
        file = open(output_file, 'w')
    else:
        output_file = None
        file = sys.stdout
    writer = csv.writer(file)
    if include_description:
        writer.writerow(["name", "engine", "technology", "description", "conforms", "message", "successes", "failures"])
    else:
        writer.writerow(["name", "engine", "technology", "conforms", "message", "successes", "failures"])
    for entry in results:
        name = entry['name']
        technology_name = entry['technology_name']
        engine_name = entry['engine_name']
        description = entry['description']
        result = entry['result']
        conforms = result['conforms']
        if 'message' in result:
            message = result['message']
        else:
            message = ""
        if 'successes' in result:
            successes = result['successes']
        else:
            successes = []
        if 'failures' in result:
            failures = result['failures']
        else:
            failures = []
        if include_description:
            writer.writerow([name, engine_name, technology_name, description, conforms, message, successes, failures])
        else:
            writer.writerow([name, engine_name, technology_name, conforms, message, successes, failures])
    if output_file is not None:
        file.close()
        logging.info(f"Results saved to CSV {output_file}")

def run_shacl(results, test, manifest, name, description, results_folder, temp, technology, data_graph, nodes, shapes, pairs, prefix, include_message, include_descr):
    logging.debug(f"Running SHACL for {name}")
    shapes_graph = os.path.join(manifest['shacl_folder'], test['shapes_graph'])
    merged_filename = os.path.join(temp, test['name'] + ".ttl")
    prepare_target_declarations(data_graph, shapes_graph, nodes, shapes, pairs, merged_filename)
    if technology is not None:
        selected_technology = technology
        if selected_technology in manifest['shacl_technologies']:
            technologies = [selected_technology]
        else:
            logging.warning(f"SHACL selected technology: {selected_technology} is not in manifest technologies {manifest['shacl_technologies']}")
            technologies = []
    else:
        technologies = manifest['shacl_technologies']
    for technology in technologies:
        logging.debug(f"Running SHACL with technology: {technology}")
        shacl_params = SHACLParams(
            filename=merged_filename,
            name=name,
            description=description,
            results_folder=results_folder,
            temp=temp,
            technology=technology,
            data_graph=data_graph,
            nodes=nodes,
            shapes=shapes,
            pairs=pairs,
            include_message=include_message,
            include_descr=include_descr
        )
        match technology:
            case "shacl_tq":
                shacl_tq(shacl_params, results)
            case "jena_shacl":
                jena_shacl(shacl_params, results)
            case "shacl_s":
                shacl_s(shacl_params, results)
            case "pyshacl":
                pyshacl(shacl_params, results)
            case "rudof":
                rudof_shacl(shacl_params, results)
            case _:
                print(f"Unknown technology: {technology}")
                exit(1)
    return

def run_shex(results, test, manifest, name, description, results_folder, temp, technology, nodes, shapes, pairs, prefix, include_message, include_descr):
    logging.debug(f"Running Shex for {name}")
    data_file = os.path.join(manifest['rdf_folder'], test['data_graph'])
    shex_file = os.path.join(manifest['shex_folder'], test['shex_file'] )
    shapemap_file = os.path.join(temp, test['name'] + ".sm" )
    prepare_shapemap(nodes, shapes, pairs, shapemap_file)
    if technology is not None:
        selected_technology = technology
        if selected_technology in manifest['shex_technologies']:
            technologies = [selected_technology]
        else:
            logging.warning(f"ShEx selected technology: {selected_technology} is not in manifest technologies {manifest['shex_technologies']}")
            technologies = []
    else:
        technologies = manifest['shex_technologies']
    for technology in technologies:
        shex_params = ShExParams(
            data_file=data_file,
            shex_file=shex_file,
            shapemap_file=shapemap_file,
            name=name,
            technology = technology,
            description=description,
            results_folder=results_folder,
            nodes=nodes,
            shapes=shapes,
            pairs=pairs,
            include_message=include_message,
            include_descr=include_descr
        )
        match technology:
            case "shex_s":
                shex_s(shex_params, results)
            case "jena_shex":
                jena_shex(shex_params, results)
            case "rudof":
                rudof_shex(shex_params, results)
            case _:
                print(f"Unknown technology: {technology}")
                exit(1)
    return

def get_list(name, dict):
    if name in dict:
        return dict[name]
    return []

def get_str(name, dict, default):
    if name in dict:
        return dict[name]
    return default

""" Runs a single test case 
    Stores the results in the results list
"""
def run_test(results, test, args, results_folder, manifest) -> None:
    logging.debug(f"Running test: {test['name']}")
    name = get_str('name', test, "??")
    description = get_str('description', test, "")
    if args.name is None or name == args.name:
        logging.info(f"Test name: {name}")
        engine = test['engine']
        if args.engine is None or engine == args.engine:
            logging.info(f"Test engine: {engine}")
            prefix = test['default_prefix']
            data_graph = os.path.join(manifest['rdf_folder'], test['data_graph'])
            nodes = get_list('nodes', test)
            shapes = get_list('shapes', test)
            pairs = get_list('pairs', test)
            prefix = test['default_prefix']
            nodes = enrich_with_iris(nodes,prefix)
            shapes = enrich_with_iris(shapes,prefix)
            pairs = enrich_pairs_with_iris(pairs,prefix)
            match engine:
                case "shacl":
                    run_shacl(results, test, manifest, name, description, results_folder, args.temp, args.technology, data_graph, nodes, shapes, pairs, prefix, args.include_message, args.include_description)
                case "shex":
                    run_shex(results, test, manifest, name, description, results_folder, args.temp, args.technology, nodes, shapes, pairs, prefix, args.include_message, args.include_description)
    return

def load_manifest(manifest_path):
    with open(manifest_path, 'r') as file:
        manifest = yaml.safe_load(file)
        logging.debug(f"Manifest loaded: {len(manifest['tests'])} tests")
        return manifest

def run_tests(args, unknown_args):
    setup_logging(args.logging)
    if unknown_args:
        print(f"Unknown args: {unknown_args}")
        exit(1)
    logging.info(f"Running tests with the following parameters: {args}")
    manifest = load_manifest(args.manifest)

    shacl_folder = manifest['shacl_folder']
    shex_folder = manifest['shex_folder']
    results_folder = manifest['results_folder']

    # Check if the results folder exists or create it
    if not os.path.exists(results_folder):
        os.makedirs(results_folder)

    temp = args.temp
    # Check if the results folder exists or create it
    if not os.path.exists(temp):
        os.makedirs(temp)

    # Check if the SHACL folder exists
    if not os.path.exists(shacl_folder):
        print("SHACL folder {shacl_folder} does not exist")
        exit(1)

    results = []
    for test in manifest['tests']:
        run_test(results, test, args, results_folder, manifest)
    for format in args.format:
        match format:
            case "yaml":
                save_results_yaml(results, args.output)
            case "csv":
                save_results_csv(results, args.output, args.include_description)
            case _:
                logging.warning(f"Unknown format {format}. Supported formats are [yaml, csv]")
    return

def find_binary(technology: str) -> str: 
    match technology:
        case "shacl_tq": return shacl_tq_bin
        case "shacl_s": return shacl_s_bin
        case "shex_s": return shex_s_bin
        case "rudof": return rudof_bin
        case "jena_shex": return jena_shex_bin
        case "jena_shacl": return jena_shacl_bin
        case _: 
            print(f"Technology {technology} not found")
            exit(1)
    
def run_check(args, unknown_args):
    setup_logging(args.logging)
    binary = find_binary(args.technology)
    run_args([binary] + unknown_args)
    return

def main():
    parser = argparse.ArgumentParser(
        prog = "sheval",
        description="Execute Recursion Shapes experiments",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    subparsers = parser.add_subparsers(help='subcommand help')
    parser_test = subparsers.add_parser("test", help='Run tests')
    parser_check = subparsers.add_parser('check', help='Check some technology')

    parser_test.add_argument("-l", 
       "--logging", 
       default = "warning", 
       action="store", 
       help="Logging level: [debug, info, warning]"
    )
    parser_test.add_argument(
        "--temp", 
        help="Temporal folder", 
        default = "temp", 
        action="store"
    )
    parser_test.add_argument("--include-message", 
       help="Include messages in output", 
       default = False, 
       action="store_true"
    )
    parser_test.add_argument("--include-description", 
       help="Include descriptions in output", 
       default = False, 
       action="store_true")
    parser_test.add_argument("-n", 
        "--name", 
        help="Name of test", 
        default = None, 
        action="store")
    
    parser_test.add_argument("-e", "--engine", help="Engine (can be shacl or shex)", default = None, action="store")
    parser_test.add_argument(
        "-t", 
        "--technology", 
        help="Technology (specific technology like shacl_tq, shaclex, ...)", 
        default = None, 
        action="store"
    )
    parser_test.add_argument(
        "-m", "--manifest", 
        help="Manifest file (in YAML format)", 
        default = "manifest.yaml", 
        action="store"
    )
    parser_test.add_argument("-o", 
        "--output", 
        help="Output file (in YAML format)", 
        default = None, 
        action="store"
    )
    parser_test.add_argument(
        "-f", 
        "--format", 
        help="List of output formats (yaml or csv)", 
        default = ["yaml"], 
        type = str, 
        nargs='*'
    )
    parser_test.set_defaults(func=run_tests)

    parser_check.add_argument(
        "-t", 
        "--technology", 
        help="Technology (can be jena, rudof, shacl_tq,...)", 
        default = None, 
        action="store")
    parser_check.add_argument("-l", 
       "--logging", 
       default = "warning", 
       action="store", 
       help="Logging level: [debug, info, warning]"
    )
    parser_check.set_defaults(func=run_check)
    args, unknown = parser.parse_known_args()
    args.func(args, unknown)

def setup_logging(logging_level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter("%(levelname)s: %(message)s"))
    logging.basicConfig(level=logging.WARNING, handlers=[handler])
    match logging_level:
        case "debug":
            logging.getLogger().setLevel(logging.DEBUG)
        case "info":
            logging.getLogger().setLevel(logging.INFO)
        case "warning":
            logging.getLogger().setLevel(logging.WARNING)
        case _: 
            print(f"Unknown logging level: {logging_level}")
            exit(1)
    return

if __name__ == "__main__":
    main()


