from abc import ABC, abstractmethod

class GenericLogger(ABC):
    @abstractmethod
    def log_debug(self, line: str) -> None:
        """
        """
    @abstractmethod
    def log_trace(self, line: str) -> None:
        """
        """    
    @abstractmethod
    def log_error(self, line: str) -> None:
        """
        """
    @abstractmethod
    def log_info(self, line: str) -> None:
        """
        """
    @abstractmethod
    def log_warn(self, line: str) -> None:
        """
        """
