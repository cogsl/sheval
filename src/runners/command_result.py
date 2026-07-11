from enum import Enum


class CommandResult(Enum):
    OK = 0
    TIMEOUT = 1
    ERROR = 2
    EXCEPTION = 3
