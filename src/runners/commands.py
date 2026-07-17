import logging
import re
import subprocess
from dataclasses import dataclass

from .command_result import CommandResult

_ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')


def _strip_ansi(text) -> str:
    if not text:
        return ""
    if isinstance(text, bytes):
        text = text.decode(errors="replace")
    return _ANSI_ESCAPE.sub('', text)


@dataclass
class RunOutcome:
    """Result of running a command: the high-level status plus whatever
    stderr/returncode could be captured, so callers can classify failures
    beyond the coarse OK/TIMEOUT/EXCEPTION status (see error_classification.py)."""
    status: CommandResult
    stderr: str = ""
    returncode: int | None = None


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
    try:
        with open(output_filename, "w") as output:
            command_str = " ".join(command) + " > " + str(output_filename)
            logging.info(f"Command: {command_str}")
            completed = subprocess.run(command, stdout=output, stderr=subprocess.PIPE, timeout=timeout, text=True)
            return RunOutcome(status=CommandResult.OK, stderr=_strip_ansi(completed.stderr), returncode=completed.returncode)
    except subprocess.TimeoutExpired as timeoutErr:
        print("Timeout expired running command: %s" % (command))
        return RunOutcome(status=CommandResult.TIMEOUT, stderr=_strip_ansi(timeoutErr.stderr))
    except subprocess.CalledProcessError as callProcessErr:
        cmdErrStr = str(callProcessErr)
        print("Error %s running command: %s" % (cmdErrStr, command))
        return RunOutcome(status=CommandResult.EXCEPTION)


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
