from infrastructure.generic_logger import GenericLogger
from enum import Enum

class LoggerType(Enum):
    NONE = 0
    INFO = 1
    DEBUG = 2
    TRACE = 3


class Logger(GenericLogger):
    def __init__(self, logger_type: LoggerType):
        self.info   = logger_type == LoggerType.TRACE or logger_type == LoggerType.DEBUG or logger_type == LoggerType.INFO
        self.debug  = logger_type == LoggerType.TRACE or logger_type == LoggerType.DEBUG
        self.trace  = logger_type == LoggerType.TRACE     

    def set_debug(self) -> None:
        self.debug = True

    def set_trace(self) -> None:
        self.trace = True

    def __print_splitted(self, logger_type: str, line: str):
        for sub_line in line.split('\n'):
            try:
                print(f'{logger_type}: {sub_line}')
            except Exception as inst:
                print(f'{inst}, printing in UTF-8:')
                print(f'{logger_type}: In UTF-8: {sub_line.encode("utf-8")}')
                

    def log_info(self, line: str) -> None:
        if self.info:
            self.__print_splitted('INFO', line)

    def log_error(self, line: str) -> None:
        self.__print_splitted('ERROR', line)

    def log_warn(self, line: str) -> None:
        self.__print_splitted('WARN', line)

    def log_debug(self, line: str) -> None:
        if self.debug:
            self.__print_splitted('DEBUG', line)


    def log_trace(self, line: str) -> None:
        if self.trace:
            self.__print_splitted('TRACE', line)
