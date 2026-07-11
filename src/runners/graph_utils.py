import logging

import rdflib

shacl_prefix = "http://www.w3.org/ns/shacl#"


def prepare_shapemap(nodes: list, shapes: list, pairs: list, merged_filename: str) -> None:
    if not nodes and not shapes and not pairs:
        print("No nodes, shapes or pairs to prepare shapemap")
        return

    strs = []
    for (node, node_iri) in nodes:
        for (shape, shape_iri) in shapes:
            strs.append(f"<{node_iri}>@<{shape_iri}>")
    for pair in pairs:
        node_iri = pair['node'][1]
        shape_iri = pair['shape'][1]
        strs.append(f"<{node_iri}>@<{shape_iri}>")
    shapemap = ",".join(strs)
    with open(merged_filename, 'w') as outfile:
        logging.debug(f"Writing shapemap {shapemap}\n in file {merged_filename}")
        outfile.write(shapemap)


def prepare_target_declarations(data_graph, shapes_graph, nodes, shapes, pairs, merged_filename):
    """
    Prepare the target declarations for the SHACL shapes
    It creates a new graph which is the result of mergin the data graph,
    the shapes graph and the target declarations that are obtained from the manifest file
    """
    if not nodes and not shapes and not pairs:
        print("No nodes, shapes or pairs to prepare target declarations")
        return

    g = rdflib.Graph()
    g.parse(data_graph, format='turtle')
    g.parse(shapes_graph, format='turtle')

    for (shape, shape_iri) in shapes:
        for (node, node_iri) in nodes:
            logging.debug(f"{shape_iri} sh:targetNode {node_iri}")
            g.add((rdflib.URIRef(shape_iri), rdflib.URIRef(shacl_prefix + "targetNode"), rdflib.URIRef(node_iri)))

    for pair in pairs:
        node_iri = pair['node'][1]
        shape_iri = pair['shape'][1]
        g.add((rdflib.URIRef(shape_iri), rdflib.URIRef(shacl_prefix + "targetNode"), rdflib.URIRef(node_iri)))

    logging.debug(f"Merged graph: {g.serialize(format='turtle')}")
    # Save the merged graph to a temp file
    g.serialize(destination=merged_filename, format='turtle')
    logging.debug(f"Serialized graph to {merged_filename}")
    return


def enrich_with_iris(nodes, prefix):
    """
    Enrich the nodes with their IRIs
    param:
        nodes: a list of nodes
        prefix: the prefix to use for the IRIs
    return: a list of pairs (node, node_iri) with the nodes and their IRIs
    """
    iris = []
    for node in nodes:
        node_iri = prefix + node.replace(":", "", 1)
        iris.append((node, node_iri))
    return iris


def enrich_pairs_with_iris(pairs, prefix):
    """
    Enrich the pairs of node shape with their IRIs
    """
    enriched = []
    for pair in pairs:
        node_iri = prefix + pair['node'].replace(":", "", 1)
        shape_iri = prefix + pair['shape'].replace(":", "", 1)
        enriched_pair = {'node': (pair['node'], node_iri), 'shape': (pair['shape'], shape_iri)}
        enriched.append(enriched_pair)
    return enriched
