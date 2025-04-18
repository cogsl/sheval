# Recursive shapes experiment

The experiment comapres how different implementations of SHACL and ShEx behave with recursive shapes.

## Implementations

### SHACL

- [SHACL_TQ](https://github.com/TopQuadrant/shacl): SHACL implementation in Java. Download the release 1.4.4 [available here](https://github.com/TopQuadrant/shacl/releases/tag/v1.4.4). Once installed, it can be run with `shaclvalidate.sh`
- [SHACLEX](https://github.com/weso/shaclex): SHACL implementation in Scala. Compiled the latest version available in the github repo. It can be run with `shaclex`
- [Jena SHACL](https://jena.apache.org/documentation/shacl/). SHACL implementation in Java. It can be run with `shacl`
- [RDF4j SHACL](https://rdf4j.org/documentation/programming/shacl/)
- [PySHACL](https://github.com/RDFLib/pySHACL)
- [Shawell](https://github.com/cem-okulmus/shawell)

### ShEx

## Running the experiments

### Requirements

It is required to have [Python 3](https://www.python.org/downloads/) and [Java](https://openjdk.org/) installed.

The binaries for the validators are included in the `bin` folder.

### Usage

The script `run_all.py` runs all the experiments. It uses a `manifest.yaml` that describes each of the test cases.

The default way to run the experiments and generate a CSV fle with the results is:

```sh
python3 run_all.py --manifest manifest.yaml -f csv -o output.csv
```

The contents of `manifest.yaml` declare the experiments that can be run. It consists of a list of configuration entries like:

```yaml
rdf_folder: RDF 
shacl_folder: SHACL
shacl_technologies: 
  - pyshacl
  - shaclex
  - jena_shacl
  - shacl_tq
shex_folder: ShEx
results_folder: results
```

Followed by a list of test entries like:

```yaml
tests:
    - name: test_name                       # Name of the test
      data_graph: data.ttl                  # File with RDF data
      shapes_graph: shapes.ttl              # File with Shapes data
      engine: shacl                         # Type of engine shacl or shex
      description: Example                  # Short description of the test
      default_prefix: "http://example.org/" # Default prefix used for nodes and shapes
      nodes:                                # List of target nodes
        - ":a"
        - ":b"
        - ":c"
        - ":d"
      shapes:                               # List of shapes
        - ":S"
```

For SHACL, the test runner will merge the RDF data graph and the shapes graph and add the corresponding target declarations, creating a file in the `temp` folder. It will run the SHACL or ShEx validators and generate a validation report in Turtle which will be analyzed to check if the result is conforming or if there are any violations.

For ShEx, the test runner will create a shape map with the corresponding nodes and shapes and run the ShEx validators using it.

```sh
usage: run_all.py [-h] [-v] [--debug] [--temp TEMP] [--include-message] [-m MANIFEST] [-o OUTPUT] [-f FORMAT]

Execute Recursion Shapes experiments

options:
  -h, --help            show this help message and exit
  -v, --verbose         increase verbosity (default: 0)
  --debug               debug info (default: 0)
  --temp TEMP           Temporal folder (default: temp)
  --include-message     Include messages in output (default: False)
  -m MANIFEST, --manifest MANIFEST
                        Manifest file (in YAML format) (default: manifest.yaml)
  -o OUTPUT, --output OUTPUT
                        Output file (in YAML format) (default: None)
  -f FORMAT, --format FORMAT
                        Output format (yaml or csv) (default: yaml)
```
