# ShEval - SHACL/ShEx Engines Evaluation

This repo contains code to compare different SHACL and ShEx engines.

The code can be used to compare results of evaluating shapes with different graphs and target declarations or shape maps. 

More concretely, the code has been used to compare how different implementations of SHACL and ShEx behave with recursive shapes.

## Running the code

The code is prepared to be run in a reproducible way using Docker.

Build a docker image with:

```sh
docker build -t sheval .
```

## Engines available

### SHACL

- shacl_tq: [SHACL_TQ](https://github.com/TopQuadrant/shacl): SHACL implementation in Java. Download the release 1.4.4 [available here](https://github.com/TopQuadrant/shacl/releases/tag/v1.4.4). Once installed, it can be run with `shaclvalidate.sh`
- shaclex: [SHACLEX](https://github.com/weso/shaclex): SHACL implementation in Scala. Compiled the latest version available in the github repo. It can be run with `shaclex` selecting `SHACLEX` as engine.
- jena: [Jena SHACL](https://jena.apache.org/documentation/shacl/). SHACL implementation in Java. It can be run with `shacl`
- pyshacl: [PySHACL](https://github.com/RDFLib/pySHACL)

### ShEx

- [SHACLEX](https://github.com/weso/shaclex): ShEx implementation in Scala. Compiled the latest version available in the github repo. It can be run with `shaclex` and selecting `SHEX` as an engine.

### Pending implementations

- [RDF4j SHACL](https://rdf4j.org/documentation/programming/shacl/)
- [Shawell](https://github.com/cem-okulmus/shawell)

## Running the experiments

### Requirements

It is required to have [Python 3](https://www.python.org/downloads/) and [Java](https://openjdk.org/) installed.

The binaries for the validators are included in the `bin` folder.

### Usage

The script `sheval.py` runs all the experiments. It uses a `manifest.yaml` that describes each of the test cases.

The default way to run the experiments and generate a CSV fle with the results is:

```sh
python3 sheval.py --manifest manifest.yaml -f csv -o output.csv
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
usage: sheval.py [-h] [-v] [--debug] [--temp TEMP] [--include-message] [--include-description] [-n NAME] [-e ENGINE] [-t TECHNOLOGY] [-m MANIFEST] [-o OUTPUT]
                  [-f FORMAT]

Execute Recursion Shapes experiments

options:
  -h, --help            show this help message and exit
  -v, --verbose         increase verbosity (default: 0)
  --debug               debug info (default: 0)
  --temp TEMP           Temporal folder (default: temp)
  --include-message     Include messages in output (default: False)
  --include-description
                        Include descriptions in output (default: False)
  -n NAME, --name NAME  Name of test (default: None)
  -e ENGINE, --engine ENGINE
                        Engine (can be shacl or shex) (default: None)
  -t TECHNOLOGY, --technology TECHNOLOGY
                        Technology (specific technology like shacl_tq, shaclex, ...) (default: None)
  -m MANIFEST, --manifest MANIFEST
                        Manifest file (in YAML format) (default: manifest.yaml)
  -o OUTPUT, --output OUTPUT
                        Output file (in YAML format) (default: None)
  -f FORMAT, --format FORMAT
                        Output format (yaml or csv) (default: yaml)
```

It is possible to run all the tests from a manifest or to select the tests of one technology or engine.

For example, to run all the tests and generate a YAML output with the results:

```sh
python3 sheval.py -f yaml -o output.yaml
```

To run all the tests and generate a CSV output with the results:

```sh
python3 sheval.py -f csv -o output.csv
```

### Running some specific test

It is also possible to run a single test by specifying its name.

For example, to run only the test `consistency1`, you can use:

```sh
python3 sheval.py -f csv -o output.csv -n consistency1
```

It is also possible to specify one engine, which can be either `shex` or `shacl`:

```sh
python3 sheval.py -f csv -o output.csv -n consistency1 -e shex
```

Or one specific technology, like `pyshacl`, `shaclex`, etc.

```sh
python3 sheval.py -f csv -o output.csv -n consistency1 -e shex -t pyshacl
```

If you want to see which command is executed, you can add `--debug`
