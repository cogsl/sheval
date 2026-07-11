from dataclasses import dataclass


@dataclass
class ShExParams:
    data_file: str
    shex_file: str
    shapemap_file: str
    name: str
    description: str
    results_folder: str
    technology: str
    nodes: list
    shapes: list
    pairs: list
    include_message: bool
    include_descr: bool
