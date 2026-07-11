from dataclasses import dataclass


@dataclass
class SHACLParams:
    filename: str
    name: str
    description: str
    results_folder: str
    temp: str
    technology: str
    data_graph: str
    nodes: list
    shapes: list
    pairs: list
    include_message: bool
    include_descr: bool
