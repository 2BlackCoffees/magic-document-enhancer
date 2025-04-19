from typing import List, Dict

from domain.iml_access import IMLAccess
from domain.logger import GenericLogger

class LineUpdater:
    how_to_transform: List[str] = []
    def __init__(self, 
                 ml_access: IMLAccess,
                 how_to_transform: Dict,
                 logger: GenericLogger):
        self.ml_access: IMLAccess = ml_access
        self.logger: GenericLogger = logger
        self.temperature: float = 0.4
        self.top_p: float = 0.3
        self.how_to_transform = how_to_transform
          
    def get_ml_access(self) -> IMLAccess:
        return self.ml_access
    
    def update_line(self, text_to_transform: str) -> str:
        new_line: str = self.ml_access.transform_line(text_to_transform, self.how_to_transform, self.temperature, self.top_p)
        self.logger.log_debug(f"ILineUpdater.update_line: Transformed:\n{text_to_transform}\nto\n{new_line}")
        return new_line

    def try_update_line(self, text_to_transform: str) -> str:
        self.logger.log_trace(f"ILineUpdater.update_line: transforming with \n{self.how_to_transform}\n The initial text:\n{text_to_transform}")
        new_line: str = self.ml_access.try_transform_line(text_to_transform, self.how_to_transform, self.temperature, self.top_p)
        self.logger.log_debug(f"ILineUpdater.update_line: Transformed:\n{text_to_transform}\nto\n{new_line}")
        return new_line