from abc import ABC, abstractmethod
from typing import List
from dataclasses import dataclass
import threading
from pprint import pformat

from domain.llm_utils import LLMUtils
from domain.logger import GenericLogger


class ThreadSynchronization:
    def __init__(self):
        self.running_status: bool = False
        self.thread_lock_queue = threading.Lock()

    def get_running_status(self) -> bool:
        return_value: bool = False
        self.thread_lock_queue.acquire()
        return_value = self.running_status
        self.thread_lock_queue.release()

        return return_value

class Metadata(ABC):
    
    def __init__(self, list_pointer_source_data: List, context: str, text_to_transform: str, request_type: str, logger: GenericLogger):
        self.list_pointer_source_data: List = list_pointer_source_data
        self.context = context
        self.text_to_transform: str = text_to_transform
        self.request_type = request_type
        self.logger = logger
        self.logger.log_trace(f"Add metadata of request type {request_type}, text_to_transform: {text_to_transform}")

    def get_text_to_transform(self) -> str:
        return self.text_to_transform
    
    def get_pointers(self):
        return self.list_pointer_source_data
    
    def get_context(self) -> str:
        return self.context
    
    def get_request_type(self) -> str:
        return self.request_type
    
    @abstractmethod
    def update_llm_response_in_document(self, text: str, request_tyoe: str) -> None:
        """
        """

    def _update_table(self, md_table_text: str) -> None:
        if len(self.list_pointer_source_data) > 0:
            doc_table: any = self.list_pointer_source_data[0]
            if len(self.list_pointer_source_data) > 1:
                self.logger.log_warn(f"More than one table was registerd ({len(self.list_pointer_source_data)} registered), currently assuming only one table")
            self.logger.log_debug(f"Updating table {md_table_text} in microsoft document")
            md_table_list: List = LLMUtils.md_to_lists(md_table_text, self.logger)
            self.logger.log_trace(f"Transformed text md table: \n{pformat(md_table_text)} to list based table:\n{pformat(md_table_list)}")

            for row_id, row in enumerate(doc_table.rows):
                for col_id, cell in enumerate(row.cells):
                    if row_id < len(md_table_list) and col_id < len(md_table_list[row_id]):
                        cell.text = md_table_list[row_id][col_id]
                        self.logger.log_trace(f"Updated cell (row_id:{row_id}, col_id: {col_id}) to {cell.text}")
                    else:
                        self.logger.log_error(f"Could not update cell having initial value {cell.text} because of index out of range at coordinate (Row: {row_id}, Col: {col_id}):\n"+\
                                              f"  Doc Table size: Rows: {len(doc_table.rows)} x Cols: {len(doc_table.rows[row_id].cells)} and \n"+\
                                              f"  List Table size: Rows: {len(md_table_list)} x Cols: {len(md_table_list[row_id])}")

        else:
            self.logger.log_error(f"No table was registered for the context: {self.get_context()}\n"+\
                                  "request:\n{self.get_text_to_transform()}\n")

    def _update_text(self, text:str) -> None:
        # Split LLM transformation per paragraph and ensure that the number of paragraph returned by LLM 
        # does not exceed the original number of paragraphs
        paragraphs = text.split("\n")
        while (len(paragraphs) > 1 and len(paragraphs) > len(self.list_pointer_source_data)):
            paragraphs[-2] += "\n" + paragraphs[-1]
            paragraphs = paragraphs[0:len(paragraphs) - 1]
        if len(paragraphs) > len(self.list_pointer_source_data):
            self.logger.log_warn(f"len(paragraphs) ({len(paragraphs)}) > len(self.list_pointer_source_data) ({len(self.list_pointer_source_data)})")
        for index in range(min(len(paragraphs), len(self.list_pointer_source_data))):
            self.list_pointer_source_data[index].text = paragraphs[index]
        # If the number of paragraphs returned by LLM is lower than the current number of paragraphs 
        # in the original document clear the text.
        for index in range(len(paragraphs), len(self.list_pointer_source_data)):
             self.list_pointer_source_data[index].text = ""


class MetadataDoc(Metadata):
    thread_lock_queue = threading.Lock()


    def update_llm_response_in_document(self, text: str, request_tyoe: str) -> None: 
        self.thread_lock_queue.acquire()
        self.logger.log_trace(f"Updating document with request type: {request_tyoe} and text: {text}")
        if request_tyoe != LLMUtils.TABLE_REQUEST:
            self._update_text(text)
        else:
            self._update_table(text)
        self.thread_lock_queue.release() 

class MetadataXls(Metadata):
    thread_lock_queue = threading.Lock()

    def get_text_to_transform(self) -> str:
        return str(self.list_pointer_source_data.value)
    def update_llm_response_in_document(self, text: str, request_tyoe: str) -> None: 
        self.thread_lock_queue.acquire()
        self.list_pointer_source_data.value = text
        self.thread_lock_queue.release() 

class MetadataPpt(Metadata):
    thread_lock_queue = threading.Lock()


    def update_llm_response_in_document(self, text: str, request_tyoe: str) -> None: 
        self.thread_lock_queue.acquire()
        self.logger.log_trace(f"Updating document with request type: {request_tyoe} and text: {text}")
        if request_tyoe != LLMUtils.TABLE_REQUEST:
            self._update_text(text)
        else:
            self._update_table(text)
        self.thread_lock_queue.release() 

@dataclass
class MultithreadedMetadata:
    metadata: Metadata = None
    thread_synchronization: ThreadSynchronization = None

class IQueue(ABC):
    @abstractmethod
    def add_element(self, metadata: Metadata) -> None:
        """
        """
    @abstractmethod
    def get_element(self, index: int) -> Metadata:
        """
        """
       
    @abstractmethod
    def pop_next_element(self) -> Metadata:
        """
        """
    
    @abstractmethod
    def get_next_element(self) -> Metadata:
        """
        """
       
    @abstractmethod
    def delete_next_element(self) -> None:
        """
        """
       
    @abstractmethod
    def del_element(self, index: int) -> None:
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
    def pop_next_element(self) -> Metadata:
        return_value = self.get_next_element()
        self.delete_next_element()
        return return_value
    
class Queue(IQueue):
    def __init__(self):
        self.queue: List[Metadata] = []
     
    def add_element(self, metadata: Metadata) -> None:
        self.queue.append(metadata)

    def get_element(self, index: int) -> Metadata:
        return_value = None
        if index < len(self.queue):
           return_value = self.queue[index] 
        return return_value
          
    def get_next_element(self) -> Metadata:
        return_value = None
        if len(self.queue) > 0:
           return_value = self.queue[0] 
        return return_value
       
    def delete_next_element(self) -> None:
        if len(self.queue) > 0:
           del self.queue[0] 
       
    def del_element(self, index: int) -> None:
        if index < len(self.queue):
          del self.queue[index]
    
    def is_empty(self) -> bool:
        is_empty_status: bool = True
        is_empty_status = len(self.queue) == 0

        return is_empty_status
    
    def size(self) -> int:
        queue_size: int = len(self.queue)
        return queue_size


# TODO: This queue needs to be refactored, 
# it does not need to be threadsafe anymore.
class ThreadSafeQueue(IQueue):
    def __init__(self, logger: GenericLogger):
        self.queue: List[MultithreadedMetadata] = []
        self.thread_lock_queue = threading.Lock()
        self.sync_queue: ThreadSynchronization = ThreadSynchronization()
        self.logger = logger
        self.detailed_debug = False
     
    def add_element(self, metadata: Metadata) -> None:

        self.thread_lock_queue.acquire()
        for element in self.queue:
            if element.metadata.get_text_to_transform() == metadata.get_text_to_transform():
                #TODO: Instead of processing several time the same input, 
                # the pointers should be stored in a container and be all updated after the AI processing of one
                self.logger.log_warn(f"Saving a second time the same text {element.metadata.get_text_to_transform()}")
                break
        self.queue.append(MultithreadedMetadata(metadata, ThreadSynchronization()))
        self.logger.log_info(f"Added paragraph {len(self.queue)}: {metadata.get_text_to_transform()[0:50]}...")
        self.thread_lock_queue.release()

    def get_element(self, index: int) -> MultithreadedMetadata:

        return_value: MultithreadedMetadata = None
        self.thread_lock_queue.acquire()
        self.logger.log_trace(f'Queue::get_element index: {index},  len(self.queue): { len(self.queue)}')
        if index < len(self.queue):
          return_value = self.queue[index]
        self.thread_lock_queue.release()

        return return_value
    
    def del_element(self, index: int) -> None:
        self.thread_lock_queue.acquire()
        del self.queue[index]
        self.thread_lock_queue.release()

    def get_not_processing_metadata(self) -> List[int]:
        threads_not_processing: List[str] = []

        self.thread_lock_queue.acquire()
        threads_not_processing = \
            [key for key in range(len(self.queue)) \
               if not self.queue[key].thread_synchronization.get_running_status()]

        self.thread_lock_queue.release()

        return threads_not_processing
    
    def is_empty(self) -> bool:
        is_empty_status: bool = True
        self.thread_lock_queue.acquire()
        if self.detailed_debug:
            self.logger.log_trace("\n  ".join([f"(is_empty method call): Thread index: {index},\n" + \
                                f"    Text: {self.queue[index].metadata.get_text_to_transform()},\n" +\
                                f"    Thread running status: {self.queue[index].thread_synchronization.get_running_status()}" \
                                    for index in range(len(self.queue))]))

        is_empty_status = len(self.queue) == 0
        self.thread_lock_queue.release()

        return is_empty_status
    
    def remove(self, metadata: MultithreadedMetadata) -> None:
        self.thread_lock_queue.acquire()
        if metadata in self.queue:
            self.queue.remove(metadata)
        else:
            self.logger.log_debug(f"Tried to remove {metadata.metadata.get_text_to_transform()}\nBut it was not present!")
        self.thread_lock_queue.release()

    def size(self) -> int:
        self.thread_lock_queue.acquire()
        queue_size: int = len(self.queue)
        self.thread_lock_queue.release()

        return queue_size
          
    def get_next_element(self) -> Metadata:
         return self.get_element(0)
       
    def delete_next_element(self) -> None:
        self.thread_lock_queue.acquire()
        if len(self.queue) > 0:
           del self.queue[0] 
        self.thread_lock_queue.release()

    
    

