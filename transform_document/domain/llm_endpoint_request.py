from typing import List, Dict
from domain.llm_utils import LLMUtils

from domain.iml_access import IMLAccess
from domain.logger import GenericLogger

class LLMEndpointRequest:
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
    
    def transform_text(self, text_to_transform: str, what_to_transform: str) -> str:
        request: List = LLMUtils.get_final_request(self.how_to_transform, what_to_transform, self.logger)
        new_line: str = self.ml_access.transform_line(text_to_transform, request, self.temperature, self.top_p)
        self.logger.log_debug(f"LLMEndpointRequest.update_line: Transformed:\n{text_to_transform}\nto\n{new_line}")
        return new_line

    def try_transform_text(self, text_to_transform: str, what_to_transform: str) -> str:
        request: List = LLMUtils.get_final_request(self.how_to_transform, what_to_transform, self.logger)
        self.logger.log_trace(f"LLMEndpointRequest.update_line: transforming with \n{request}\n The initial text:\n{text_to_transform}")
        new_line: str = self.ml_access.try_transform_line(text_to_transform, request, self.temperature, self.top_p)
        self.logger.log_debug(f"LLMEndpointRequest.update_line: Transformed:\n{text_to_transform}\nto\n{new_line}")
        return new_line