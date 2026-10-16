import os
import re
import shutil

from .shacl_runner import SHACLRunner
from .shacl_params import SHACLParams
from .commands import run, store_result
from .analysis import analyze_validation_report
from .error_classification import resolve_result
from .error_type import ErrorType

# shaWell (https://github.com/cem-okulmus/shawell) validates SHACL under
# well-founded semantics. It needs a SPARQL endpoint for the data, but with
# only --shaclDoc it runs in --local --dataIncluded mode: it starts its own
# in-memory Oxigraph server, loads the (merged data+shapes) file into it and
# shuts it down afterwards. Recursive shapes are delegated to DLV.
#
# The native build lives in binaries/shawell (shawell + bin/dlv + bin/oxigraph,
# see `make shawell`). If it is missing, the docker image SHAWELL_IMAGE is used
# instead (built from the shawell repo's Dockerfile, see `make shawell-docker`).
# Set SHAWELL_DOCKER=1 to use the docker image even when the native build exists.
SHAWELL_HOME = "binaries/shawell"
BIN = os.path.join(SHAWELL_HOME, "shawell")
DLV = os.path.join(SHAWELL_HOME, "bin", "dlv")
CMD = [BIN, "--shaclDoc", "$data_filename", "--dlv", DLV, "--silent", "--outputVR", "$output_filename"]

SHAWELL_IMAGE = os.environ.get("SHAWELL_IMAGE", "shawell")
# The data file's folder and the report's folder are mounted separately, so
# they don't need to be under the current directory (e.g. `--temp /tmp/...`).
DOCKER_CMD = ["docker", "run", "--rm", "--user", f"{os.getuid()}:{os.getgid()}",
              "-v", "$data_dir:/in:ro", "-v", "$output_dir:/out", SHAWELL_IMAGE,
              "--shaclDoc", "/in/$data_basename", "--dlv", "/app/bin/dlv", "--silent", "--outputVR", "/out/$output_basename"]

# Oxigraph startup plus a DLV call per recursive schema is slower than the
# in-process engines.
TIMEOUT = 30

# shaWell writes sh:conforms with a relative datatype IRI ("true"^^<boolean>),
# which rdflib would resolve against the file's base instead of xsd:boolean.
_RELATIVE_BOOLEAN = re.compile(r'\^\^<boolean>')
_XSD_BOOLEAN = '^^<http://www.w3.org/2001/XMLSchema#boolean>'

# shaWell recovers panics in main(), prints them to stderr and exits 1.
_RULES = [
    (re.compile(r"Mismatch between ValidationResult & ValidationReports"), ErrorType.CRASHED),
    (re.compile(r"oxigraph (binary not found|did not respond)|starting oxigraph"), ErrorType.CRASHED),
]


class ShawellRunner(SHACLRunner):
    def __init__(self):
        super().__init__(name="shawell", bin_command=BIN, command_pattern=CMD)

    def classify_error(self, stderr: str, returncode: int | None, conforms: bool | None = None, stdout: str = "") -> ErrorType | None:
        text = stderr or ""
        for pattern, error_type in _RULES:
            if pattern.search(text):
                return error_type
        return None

    def mk_command(self, data_filename: str, output_filename: str) -> list[str]:
        use_docker = os.environ.get("SHAWELL_DOCKER") == "1"
        if os.path.exists(BIN) and not use_docker:
            pattern = self.command_pattern
        elif shutil.which("docker"):
            replacements = {
                "$data_dir": os.path.dirname(os.path.abspath(data_filename)),
                "$data_basename": os.path.basename(data_filename),
                "$output_dir": os.path.dirname(os.path.abspath(output_filename)),
                "$output_basename": os.path.basename(output_filename),
            }
            command = []
            for arg in DOCKER_CMD:
                for key, value in replacements.items():
                    arg = arg.replace(key, value)
                command.append(arg)
            return command
        else:
            raise FileNotFoundError(f"shawell not found at {BIN} and docker is not available (run `make shawell` or `make shawell-docker`)")
        return [arg.replace("$data_filename", data_filename).replace("$output_filename", output_filename) for arg in pattern]

    def execute(self, params: SHACLParams, results: list) -> None:
        validation_report_file = os.path.join(params.results_folder, f"{params.name}_{self.name}_results.ttl")
        validation_output = os.path.join(params.results_folder, f"{params.name}_{self.name}_output.txt")
        # shaWell appends to --outputVR, so a stale report from a previous run must go
        if os.path.exists(validation_report_file):
            os.remove(validation_report_file)
        command = self.mk_command(params.filename, validation_report_file)
        bin_dir = os.path.abspath(os.path.join(SHAWELL_HOME, "bin"))
        env = dict(os.environ, PATH=bin_dir + os.pathsep + os.environ.get("PATH", ""))
        outcome = run(command, validation_output, TIMEOUT, env=env)
        result = resolve_result(self, outcome, lambda: self.analyze(validation_report_file, params))
        store_result(params.name, self.engine, self.name, params.description, result, results)

    def analyze(self, validation_report_file: str, params: SHACLParams) -> dict:
        with open(validation_report_file) as f:
            report = f.read()
        with open(validation_report_file, "w") as f:
            f.write(_RELATIVE_BOOLEAN.sub(_XSD_BOOLEAN, report))
        return analyze_validation_report(validation_report_file, params.nodes, params.shapes, params.pairs, params.include_message)
