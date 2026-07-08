# ShEval - SHACL/ShEx Engines Evaluation

This repo contains code to compare different SHACL and ShEx engines.

The code can be used to compare results of evaluating shapes with different graphs and target declarations or shape maps. 

The code has been written in a generic way allowing to add new engines and test cases easily. At this moment, sheval contains one test-suite with recursive shapes, but more test-suites can be added in the future. 

The recursive shapes test-suite has been described in this paper:
[Common Foundations for Recursive Shape Languages](https://labra.weso.es/publication/2026_foundations_recursive_shapes_languages/), Shqiponja Ahmetaj, Iovka Boneva, Jan Hidders, Jose Emilio Labra Gayo, Wim Martens, Fabio Mogavero, Filip Murlak, Cem Okulmus, Ognjen Savković, Mantas Šimkus, Dominik Tomaszuk, 
[23rd International Conference on Principles of Knowledge Representation and Reasoning](https://kr.org/KR2026/), 2026.


## Running the code

The code is prepared to be run in a reproducible way using Docker.

Build a docker image with:

```sh
docker build -t sheval .
```

And run the tests with the command:

```sh
docker run -it sheval test
```

The sheval command has several options which can be accessed with the `--help` argument:

```sh
docker run -it sheval --help
```

For example, if you want to get the results in CSV format, you can use:

```sh
docker run -it sheval test -f csv
```

If you want to store the results in a file, you can use the `-o` option with a filename. However, notice that if you want that file to be stored in your local machine, you need to mount the volume in docker, so the command could be something like:

```sh
docker run --rm --mount type=bind,src=.,dst=/app -it sheval test -o docker_output -f csv
```

## Engines available

### SHACL

- [Topbraid SHACL API](https://github.com/TopQuadrant/shacl): SHACL implementation in Java from TopBraid.
- [Jena SHACL](https://jena.apache.org/documentation/shacl/). SHACL implementation in Java. 
- [pySHACL](https://github.com/RDFLib/pySHACL), SHACL implementation in Python.
- [SHACL-S](https://github.com/weso/shacl-s): SHACL implementation in Scala. 
- [rudof](https://rudof-project.github.io/), SHACL implementation in Rust. 

### ShEx

- [shex-s](https://github.com/weso/shex-s): ShEx implementation in Scala.
- [Jena ShEx](https://jena.apache.org/documentation/shex/): ShEx implementation in Java
- [rudof](https://rudof-project.github.io/), SHACL implementation in Rust. 

### Pending implementations

Other implementations that we are planning to add in the future: 
- [RDF4j SHACL](https://rdf4j.org/documentation/programming/shacl/)
- [Shawell](https://github.com/cem-okulmus/shawell)
- [shex-js](https://github.com/shexjs/shex.js/)
- [maplib](https://github.com/DataTreehouse/maplib)

## Running the experiments

### Requirements

It is required to have [Python 3](https://www.python.org/downloads/) and [Java](https://openjdk.org/) installed.

The binaries for the validators are included in the `bin` folder.

### Test suites

Test cases are organized in test suites. Each test suite lives in its own folder under `test_suites/`, e.g. `test_suites/recursive_shapes`, and contains the `RDF`, `SHACL`, `ShEx`, `ShapeMaps` and `target_declarations` folders together with a `manifest.yaml` describing the test cases.

The `-s`/`--test-suite` option of `src/sheval.py test` selects which folder under `test_suites` to use (it defaults to `recursive_shapes`):

```sh
python3 src/sheval.py test --test-suite recursive_shapes -f csv -o output.csv
```

### Usage

The script `src/sheval.py` runs all the experiments. It uses a `manifest.yaml` that describes each of the test cases. By default it reads `test_suites/<test-suite>/manifest.yaml`, but a different manifest file can be specified with `-m`/`--manifest`.

The default way to run the experiments and generate a CSV fle with the results is:

```sh
python3 src/sheval.py test -f csv -o output.csv
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
usage: src/sheval.py test [-h] [-l LOGGING] [--temp TEMP] [--include-message] [--include-description] [-n NAME] [-e ENGINE] [-t TECHNOLOGY] [-s TEST_SUITE] [-m MANIFEST] [-o OUTPUT]
                       [-f [FORMAT ...]]

options:
  -h, --help            show this help message and exit
  -l, --logging LOGGING
                        Logging level: [debug, info, warning] (default: warning)
  --temp TEMP           Temporal folder (default: temp)
  --include-message     Include messages in output (default: False)
  --include-description
                        Include descriptions in output (default: False)
  -n, --name NAME       Name of test (default: None)
  -e, --engine ENGINE   Engine (can be shacl or shex) (default: None)
  -t, --technology TECHNOLOGY
                        Technology (specific technology like shacl_tq, shaclex, ...) (default: None)
  -s, --test-suite TEST_SUITE
                        Name of the test suite (folder under test_suites) (default: recursive_shapes)
  -m, --manifest MANIFEST
                        Manifest file (in YAML format). Defaults to test_suites/<test-suite>/manifest.yaml (default: None)
  -o, --output OUTPUT   Output file (in YAML format) (default: None)
  -f, --format [FORMAT ...]
                        List of output formats (yaml or csv) (default: ['yaml'])
```

It is possible to run all the tests from a manifest or to select the tests of one technology or engine.

For example, to run all the tests and generate a YAML output with the results:

```sh
python3 src/sheval.py test -f yaml -o output.yaml
```

To run all the tests and generate a CSV output with the results:

```sh
python3 src/sheval.py test -f csv -o output.csv
```

### Running some specific test

It is also possible to run a single test by specifying its name.

For example, to run only the test `consistency1`, you can use:

```sh
python3 src/sheval.py test -f csv -o output.csv -n consistency1
```

It is also possible to specify one engine, which can be either `shex` or `shacl`:

```sh
python3 src/sheval.py test -f csv -o output.csv -n consistency1 -e shex
```

Or one specific technology, like `pyshacl`, `shaclex`, etc.

```sh
python3 src/sheval.py test -f csv -o output.csv -n consistency1 -e shex -t pyshacl
```

If you want to see which command is executed, you can add `--logging debug`

### Running ShEx or SHACL technologies

It is possible to run the sheval script to launch different SHACL/ShEx technologies using a uniform interface. 

As an example, the following command command runs ShEx validation with `rudof`:

```sh
python3 src/sheval.py shex -d test_suites/recursive_shapes/RDF/example21.ttl -s test_suites/recursive_shapes/ShEx/example21.shex -m test_suites/recursive_shapes/ShapeMaps/example21.sm -t rudof -o results/example21.result_shex
```

If you replace `-t rudof` by `-t jena_shex` the command will be run using Jena ShEx.


