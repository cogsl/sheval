from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
import logging
import subprocess


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


class CommandResult(Enum):
    OK = 0
    TIMEOUT = 1
    ERROR = 2
    EXCEPTION = 3


def run_args(command: list[str]):
    logging.debug(f"Before running command: {command}")
    result = CommandResult.ERROR
    try:
        result = subprocess.run(command, check=True)
    except subprocess.CalledProcessError as callProcessErr:
        cmdErrStr = str(callProcessErr)
        print("Error %s running command: %s" % (cmdErrStr, command))
        result = CommandResult.EXCEPTION
    except Exception as e:
        logging.error(f"Error running command {command}: {e}")
        result = CommandResult.EXCEPTION
    return result


def run(command, output_filename, timeout=2):
    result = CommandResult.ERROR
    try:
        with open(output_filename, "w") as output:
            command_str = " ".join(command) + " > " + str(output_filename)
            logging.info(f"Command: {command_str}")
            subprocess.run(command, stdout=output, timeout=timeout)
            result = CommandResult.OK
    except subprocess.TimeoutExpired as timeoutErr:
        print("Timeout expired running command: %s" % (command))
        result = CommandResult.TIMEOUT
    except subprocess.CalledProcessError as callProcessErr:
        cmdErrStr = str(callProcessErr)
        print("Error %s running command: %s" % (cmdErrStr, command))
        result = CommandResult.EXCEPTION
    return result


def mk_command_shacl(command, filename, output):
    return list(map(lambda x:
                       x.replace("$data_filename", filename)
                       .replace("$validation_report_file", output)
                       .replace("$output_filename", output)
                       , command))


def mk_command_shex(command, data_filename, shex_filename, shapemap_filename, output):
    return list(map(lambda x:
                       x.replace("$data_filename", data_filename)
                       .replace("$shex_filename", shex_filename)
                       .replace("$shapemap_filename", shapemap_filename)
                       .replace("$output_filename", output), command))


def store_result(name, engine, technology_name, descr, result, results):
    results.append({
        "name": name,
        "engine_name": engine,
        "technology_name": technology_name,
        "description": descr,
        "result": result
    })


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
            result = {'conforms': "Exception", 'failures': f"{e}"}
            store_result(params.name, self.engine, self.name, params.description, result, results)


class SHACLRunner(Runner):
    engine = "shacl"


class ShExRunner(Runner):
    engine = "shex"
