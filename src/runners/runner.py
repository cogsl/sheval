from abc import ABC, abstractmethod
import logging

from .commands import store_result, run, RunOutcome
from .error_type import ErrorType


class Runner(ABC):
    """Base class for all technology runners. Subclasses set `engine` and implement `execute`."""
    engine: str = ""

    def __init__(self, name: str, bin_command: str, command_pattern: list):
        self.name = name
        self.bin_command = bin_command
        self.command_pattern = command_pattern

    @abstractmethod
    def execute(self, params, results: list) -> None:
        raise NotImplementedError

    def run_command(self, command: list[str], stdout_file: str, report_file: str, timeout: int) -> RunOutcome:
        """Run the engine's command, with its stdout to `stdout_file`. An
        engine can override this to react to a failure (see shawell.py).
        `report_file` is where the engine writes its report, if it writes one."""
        return run(command, stdout_file, timeout, env=self.command_env())

    def command_env(self) -> dict | None:
        """Environment for the engine's process. None keeps the current one."""
        return None

    def postprocess_report(self, report_file: str) -> None:
        """Correct an engine's report file in place before it is read.
        Default: no change."""
        return None

    def classify_error(self, stderr: str, returncode: int | None, conforms: bool | None = None, stdout: str = "") -> ErrorType | None:
        """
        Engine-specific error classification hook (see error_classification.py
        for the shared control flow that calls this). Called twice per run:

        - After a successful run (returncode 0), with `conforms` set to the
          parsed result, so an engine can flag a report that came with a
          concerning warning despite exiting cleanly (e.g. jena_shacl's
          "Cycle detected").
        - After a failed/anomalous run, with `conforms=None`, so an engine can
          recognize its own crash signatures (e.g. rudof's "Dependency graph
          has cycles", pyshacl's "Validation path too deep!").

        `stdout` carries the run's captured standard output alongside `stderr`,
        for engines that report their errors there instead (e.g. shex_s prints
        its "Negative cycles" message to stdout, which `run()` redirects
        straight into the result file).

        Default: no engine-specific rules. Subclasses override as needed.
        """
        return None

    def run(self, params, results: list) -> None:
        logging.info(f"Running {self.engine} for {params.name} with technology {params.technology}")
        try:
            self.execute(params, results)
        except Exception as e:
            logging.error(f"Error running {self.engine} for {params.name} with technology {params.technology}: {e}")
            result = {'conforms': None, 'error_type': None, 'message': f"{e}"}
            store_result(params.name, self.engine, self.name, params.description, result, results)
