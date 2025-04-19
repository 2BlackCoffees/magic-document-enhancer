from abc import ABC, abstractmethod
from typing import List
from dataclasses import dataclass
import threading
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
    
    def __init__(self, list_pointer_source_data: List, context: str, text_to_transform: str):
        self.list_pointer_source_data: List = list_pointer_source_data
        self.context = context
        self.text_to_transform: str = text_to_transform

    #@abstractmethod
    def get_text_value(self) -> str:
        return self.text_to_transform
    
    def get_pointers(self):
        return self.list_pointer_source_data
    
    def get_context(self) -> str:
        return self.context
    
    @abstractmethod
    def set_text_value(self, text: str) -> None:
        """
        """

class MetadataDoc(Metadata):
    thread_lock_queue = threading.Lock()


    #def get_text_value(self) -> str:
    #    return "\n".join([ source_data.text for source_data in self.list_pointer_source_data ])
    
    def set_text_value(self, text: str) -> None: 
        self.thread_lock_queue.acquire()
        # Split LLM transformation per paragraph and ensure that the number of paragraph returned by LLM 
        # does not exceed the original number of paragraphs
        parapgrahs = text.split("\n")
        while (len(parapgrahs) > 1 and len(parapgrahs) > len(self.list_pointer_source_data)):
            parapgrahs[-2] += "\n" + parapgrahs[-1]
            parapgrahs = parapgrahs[0:len(parapgrahs) - 1]
        for index in range(len(parapgrahs)):
            self.list_pointer_source_data[index].text = parapgrahs[index]
        # If the number of paragraphs returned by LLM is lower than the current number of paragraphs 
        # in the original document clear the text.
        for index in range(len(parapgrahs), len(self.list_pointer_source_data)):
             self.list_pointer_source_data[index].text = ""
        #self.pointer_source_data.text = text
        self.thread_lock_queue.release() 

class MetadataXls(Metadata):
    thread_lock_queue = threading.Lock()

    def get_text_value(self) -> str:
        return str(self.list_pointer_source_data.value)
    def set_text_value(self, text: str) -> None: 
        self.thread_lock_queue.acquire()
        self.list_pointer_source_data.value = text
        self.thread_lock_queue.release() 

class MetadataPpt(MetadataDoc):
    pass

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
            if element.metadata.get_text_value() == metadata.get_text_value():
                #TODO: Instead of processing several time the same input, 
                # the pointers should be stored in a container and be all updated after the AI processing of one
                self.logger.log_warn(f"Saving a second time the same text {element.metadata.get_text_value()}")
                break
        self.queue.append(MultithreadedMetadata(metadata, ThreadSynchronization()))
        self.logger.log_info(f"Added paragraph {len(self.queue)}: {metadata.get_text_value()[0:50]}...")
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
                                f"    Text: {self.queue[index].metadata.get_text_value()},\n" +\
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
            self.logger.log_debug(f"Tried to remove {metadata.metadata.get_text_value()}\nBut it was not present!")
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

    
    

