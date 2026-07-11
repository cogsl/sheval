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


def extend_nodes_shapes(nodes, shapes, pairs):
    """
    Extend nodes and shapes with the individual ones declared using pairs
    so they can be found when resolving qnames
    """
    for pair in pairs:
        nodes.append(pair['node'])
        shapes.append(pair['shape'])


def classify_shapemap_results(shapemap_results, nodes, shapes):
    """
    Classify a list of shapemap results (dicts with 'node', 'shape' and 'status' keys) into
    failures and successes, resolving node/shape IRIs to the qnames we are interested in.
    Results whose node or shape is not in the nodes/shapes lists are ignored.
    return: a (failures, successes) tuple of lists of {'node': ..., 'shape': ...} dicts
    """
    failures = []
    successes = []
    for result in shapemap_results:
        node = remove_gt_lt(result['node'])
        shape = remove_gt_lt(result['shape'])
        status = result['status']
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
            else:
                logging.info(f"Shape {shape} not found in the shapes list: {shapes}")
        else:
            logging.info(f"Node {node} not found in the nodes list: {nodes}")
    return failures, successes


def summarize_shapemap_results(json_result, nodes, shapes):
    """
    Classify a parsed shapemap JSON result and derive a conforms/message summary from it.
    Used by engines that report their shapemap results as a plain JSON list of
    {'node', 'shape', 'status'} entries.
    return: a (conforms, message, failures, successes) tuple
    """
    if isinstance(json_result, list):
        failures, successes = classify_shapemap_results(json_result, nodes, shapes)
        if failures:
            conforms, message = False, "Some nodes are not conformant"
        else:
            conforms, message = True, "No failures"
    else:
        failures, successes = [], []
        conforms, message = False, "No results in shapemap"
    return conforms, message, failures, successes


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
    extend_nodes_shapes(nodes, shapes, pairs)

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
