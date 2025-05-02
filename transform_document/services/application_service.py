import re
import os
from typing import Dict, List
from pathlib import Path

from domain.iopen_document import IOpenDocument
from domain.llm_endpoint_request import LLMEndpointRequest
from domain.worker_class import IProcessorType, Worker, MultithreadedWorkers
from domain.llm_utils import LLMUtils
from domain.iml_access import IMLAccess
from infrastructure.open_microsoft_document import OpenXLSDocument
from infrastructure.open_ppt_document import OpenPPTDocument
from infrastructure.open_doc_document import OpenDOCDocument
from infrastructure.processors import SerializedDocProcessorType, SerializedSynchronizedDocProcessorType
from infrastructure.generic_logger import GenericLogger
from infrastructure.openai_access import OpenAIAccess
from infrastructure.openai_debug_access import OpenAIDebugAccess

class ApplicationService:
    def __init__(self, 
                 document_path: str, to_document: str, 
                 transformation: int, 
                 llm_utils: LLMUtils,
                 from_language: str,  
                 paragraph_start_min_word_numbers: int,
                 paragraph_start_min_word_length: int,
                 engine_name: str,
                 max_parallel_thread: int,
                 logger: GenericLogger,
                 use_debugger_ai: bool = False,
                 slides_to_skip: List = None,
                 slides_to_keep: List = None,
                 context_path: str = None):
        
        self.logger: GenericLogger = logger
        self.to_document = to_document
        self.open_document: IOpenDocument = None
        self.llm_utils = llm_utils
        llm_requester: LLMEndpointRequest = self.__create_line_udater(
            transformation, from_language, 
            engine_name,
            use_debugger_ai
        )
        worker: Worker = ApplicationService.__create_worker(llm_requester, logger, max_parallel_thread)
        logger.log_info(f'Transforming from {document_path} to {to_document}.')
        if len(slides_to_skip) > 0: logger.log_info(f'Slides to skip: {slides_to_skip}.')
        if len(slides_to_keep) > 0: logger.log_info(f'Slides to keep: {slides_to_keep}.')
        force_context_content: List = None
        if context_path is not None:
            logger.log_info("Handling word document")
            path = Path(context_path)
            if path.is_file():
                self.logger.log_info(f"Opening external request file: {context_path}")
                with open(context_path) as f:
                    force_context_content = f.readlines()
                    self.logger.log_info(f"Using context provided in command line through filename {context_path}:\n{force_context_content}")
            else:
                self.logger.log_warn(f"File {context_path} could not be read.")

        if force_context_content is None:
            self.logger.log_info(f"Headings of the document will be used as context.")

        if re.search(r'\.doc[\w]*$', document_path):

            self.open_document = OpenDOCDocument(document_path, 
                                                 worker, 
                                                 paragraph_start_min_word_numbers, paragraph_start_min_word_length, 
                                                 logger,
                                                 force_context_content)
        elif re.search(r'\.xls[\w]*$', document_path):
            logger.log_info("Handling XLS document")
            self.open_document = OpenXLSDocument(document_path, 
                                                 worker, 
                                                 paragraph_start_min_word_numbers, paragraph_start_min_word_length, 
                                                 logger)        
        elif re.search(r'\.ppt[\w]*$', document_path):
            logger.log_info("Handling PPT document")

            self.open_document = OpenPPTDocument(document_path, 
                                                 worker, 
                                                 paragraph_start_min_word_numbers, paragraph_start_min_word_length, 
                                                 slides_to_skip, slides_to_keep, 
                                                 logger, llm_utils)

    @staticmethod
    def __create_worker(line_updater: LLMEndpointRequest, logger: GenericLogger, max_parallel_thread: int) -> Worker:
        processor_type: IProcessorType = None
        worker: Worker = None
        if max_parallel_thread <= 1:
            processor_type = SerializedDocProcessorType(line_updater, logger)
            worker = Worker(processor_type, logger) 
            logger.log_info("Running in a single thread") 
        else:
            processor_type = SerializedSynchronizedDocProcessorType(line_updater, logger, max_parallel_thread)
            worker = MultithreadedWorkers(processor_type, logger) 
            logger.log_info(f"Running in {max_parallel_thread} threads") 
        return worker
    
    def __create_line_udater(self, transformation: int,  from_language: str,  
                             engine_name: str,
                             use_debugger_ai: bool) -> LLMEndpointRequest:
        line_updater: LLMEndpointRequest = None
        mlaccess: IMLAccess = OpenAIAccess(self.logger, engine_name) if not use_debugger_ai else OpenAIDebugAccess(logger)
        request: Dict = self.llm_utils.get_request(transformation)
        self.llm_utils.set_requests(from_language)
        line_updater: LLMEndpointRequest = LLMEndpointRequest(mlaccess, request[self.llm_utils.HOW_TO_TRANSFORM], self.logger)

        return line_updater
    
    def process(self):
        self.open_document.process()
        self.open_document.save(self.to_document)

    def emergency_save(self):
        emergency_file_name = f'{self.to_document}-emergency-saved'
        self.logger.log_warn(f'Trying to emergency save the filw to {emergency_file_name}')
        self.open_document.save(emergency_file_name)

