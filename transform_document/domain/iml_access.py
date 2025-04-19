from abc import ABC, abstractmethod

class IMLAccess(ABC):
    @abstractmethod
    def try_transform_line(self, text_to_transform: str, how_to_transform: str, temperature: float, top_p: float) -> str:
        """
        """
    @abstractmethod
    def transform_line(self, text_to_transform: str, how_to_transform: str, temperature: float, top_p: float) -> str:
        """
        """