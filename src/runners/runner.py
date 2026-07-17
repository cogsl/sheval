from abc import ABC, abstractmethod
import logging

from .commands import store_result


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

    def run(self, params, results: list) -> None:
        logging.info(f"Running {self.engine} for {params.name} with technology {params.technology}")
        try:
            self.execute(params, results)
        except Exception as e:
            logging.error(f"Error running {self.engine} for {params.name} with technology {params.technology}: {e}")
            result = {'conforms': None, 'error_type': None, 'message': f"{e}"}
            store_result(params.name, self.engine, self.name, params.description, result, results)
