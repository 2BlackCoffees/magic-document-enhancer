from abc import ABC, abstractmethod
from domain.queue import Metadata
from domain.logger import GenericLogger
class IProcessorType(ABC):
    def process_next(self) -> None:
        pass
        
    @abstractmethod
    def add_element(self, metadata: Metadata) -> None:
        """
        """
    @abstractmethod
    def is_empty(self) -> bool:
        """
        """
    @abstractmethod
    def size(self) -> int:
        """
        """
    @abstractmethod
    def pop_next_element(self) -> Metadata:
        """
        """
    @abstractmethod
    def trigger_process_start(self) -> None:
        """
        """
    @abstractmethod
    def process_all(self) -> None:
        """
        """
    def join_all(self) -> None:
        pass

    @abstractmethod
    def pack(self) -> None:
        """
        Factor all paragraphs linked togeter: Currently the library 
        does not seem to be able to offer the option to distinguish 
        bullet points from other styles.

        See here for the documentation:
        https://python-docx.readthedocs.io/en/latest/api/text.html#paragraph-objects
        """

class Worker:
    def __init__(self, processor_type: IProcessorType, logger: GenericLogger):
        self.processor_type: IProcessorType = processor_type
        self.logger = logger

    def add_work_element(self, metadata: Metadata) -> None:
        self.processor_type.add_element(metadata)

    def process_all(self) -> None:
        self.processor_type.process_all()


class MultithreadedWorkers(Worker):

    def process_all(self) -> None:
        self.processor_type.pack()
        self.processor_type.process_all()





