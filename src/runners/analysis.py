import json
import re
import logging

import rdflib


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


def analyze_shapemap_shaclex(filename: str, nodes: list, shapes: list, pairs: list):
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
    return {'conforms': conforms, 'message': message, 'failures': failures, 'successes': successes}


def analyze_shapemap_shex_s(filename, nodes, shapes, pairs):
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
    return {'conforms': conforms, 'message': message, 'failures': failures, 'successes': successes}


def analyze_shapemap_rudof(filename, nodes, shapes, pairs):
    # Extend nodes and shapes with the individual ones declared using pairs
    # so they can be found in the shapemap
    for pair in pairs:
        nodes.append(pair['node'])
        shapes.append(pair['shape'])

    conforms = None
    failures = []
    successes = []
    with open(filename, 'r') as infile:
        contents = infile.read()
        # rudof prefixes its JSON output with a "Results:" line that must be stripped before parsing
        if contents.lstrip().startswith("Results:"):
            contents = contents.lstrip().removeprefix("Results:").lstrip()
        try:
            json_result = json.loads(contents)
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
            lines = [line.rstrip() for line in contents.splitlines()]
            message = lines[0] if lines else str(e)
            conforms = False
    logging.debug(f"After analyzing shapemap, Conforms: {conforms}")
    return {'conforms': conforms, 'message': message, 'failures': failures, 'successes': successes}


def parse_jena_result_line(line):
    regex = re.compile(r'<([^>]+)>\s@\s<([^>]+)>\s.*Status\s=\s(nonconformant|conformant).*')
    m = regex.match(line)
    (node, shape, conforms) = m.group(1, 2, 3)
    return (node, shape, conforms)


def analyze_result_jena_shex(filename, nodes, shapes, pairs):
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

    return {'conforms': conforms, 'message': message, 'failures': failures, 'successes': successes}
