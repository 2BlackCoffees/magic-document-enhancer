from abc import ABC, abstractmethod

class IOpenDocument(ABC):
    document: any = None
    @abstractmethod
    def process(self) -> None:
        """
        """



