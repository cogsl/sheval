import logging
import subprocess

from .command_result import CommandResult


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
