from typing import List
from domain.llm_endpoint_request import LLMEndpointRequest
from domain.queue import Queue, Metadata, ThreadSafeQueue
from domain.logger import GenericLogger
from domain.worker_class import IProcessorType
from domain.llm_utils import LLMUtils
from infrastructure.openai_access_multithreaded import MultithreadedAccess, Statistics, BackoffTimeHandler
import threading
import time
from datetime import datetime
import re

class SerializedDocProcessorType(IProcessorType):
    def __init__(self, llm_request: LLMEndpointRequest, logger: GenericLogger):
        self.queue: Queue = Queue()
        self.initial_size = 0

        self.llm_request: LLMEndpointRequest = llm_request
        self.logger: GenericLogger = logger

    def add_element(self, metadata: Metadata) -> None:
        self.queue.add_element(metadata)

    def is_empty(self) -> bool:
        return self.queue.is_empty()

    def size(self) -> int:
        return self.queue.size()
 
    def pop_next_element(self) -> Metadata:
        return self.queue.pop_next_element()
    
    def pack(self) -> None:
        pass
    
    def trigger_process_start(self) -> None:
        self.initial_size: int = self.size()

    def display_remaining_effort(self):
        percent_done: int = int( 100 * (1 - self.size() / self.initial_size))
        self.logger.log_info(f"Processed {self.initial_size - self.size()} paragraphs out of {self.initial_size} paragraphs = {percent_done}%")

    def __is_context_needed(self, context: str, initial_text: str) -> bool:
        if context is not None and len(context) > 0 and initial_text is not None and len(initial_text) > 0:
            initial_text = initial_text.strip()
            context = context.strip()
            return context != initial_text
        return False
    
    def __is_single_line_heading(self, text_heading: str) -> bool:
        self.logger.log_trace(f"__is_single_line_heading Heading {text_heading} ")
        return re.match(r'^\s*#.*$', text_heading) and len(text_heading.strip().split("\n")) <= 1
    
    def __get_heading_request(self, heading_text: str) -> str:
        return f'[Process the text as per request considering it is a heading and ensure keeping one single line for the heading] {heading_text}'

    
    def process_next(self) -> None:
        metadata: Metadata = self.pop_next_element()
        text_to_transform: str = metadata.get_text_to_transform()
        context: str = metadata.get_context()
        request_type: str = metadata.get_request_type()
        request: str = ""
        request_str: str = f'[Process the text as per request] {text_to_transform}'

        if request_type == LLMUtils.HEADING_REQUEST:
            if self.__is_single_line_heading(text_to_transform) or (text_to_transform is not None and len(text_to_transform) > 0):
                request_str = self.__get_heading_request(text_to_transform)
        elif request_type == LLMUtils.TABLE_REQUEST:
            request_str = f'[Process the table as per request and ensure keeping the STRICT same number of columns and rows] {text_to_transform}'

        if self.__is_context_needed(context, text_to_transform):
            request = f"[Considering the context: {context}] {request_str}"

        elif text_to_transform is not None and len(text_to_transform) > 0:
            self.logger.log_warn(f"Request will be performed without any found context: initial_text = >{text_to_transform}<, request: {request_str}")

            request = f"{request_str}"
        else:
            self.logger.log_trace(f"Skipping request because initial_text = >{text_to_transform}<")
            return

        request_info: str = '  ' + '\n  '.join(request.replace('\n', '').replace(']', ']\n').split('\n'))
        self.logger.log_trace(f'Request preparation to LLM:\n{"-" * 20}\n\n{request_info}')

        new_text = self.llm_request.transform_text(request, request_type)
        new_text_info: str = '  ' + '\n  '.join(new_text.split('\n'))
        self.logger.log_info(f'\nLLM response:\n{"-" * 13}\n{new_text_info}\n')

        metadata.update_llm_response_in_document(new_text, request_type)
        self.logger.log_info(f'\n  >> {"=" * 15} End document update for this request {"=" * 15}\n')

    def process_all(self) -> None:
        self.trigger_process_start()
        while not self.is_empty():
            self.process_next()        

class SerializedSynchronizedDocProcessorType(IProcessorType):
    class Metadata:
        thread_access: MultithreadedAccess
        

    def __init__(self, line_updater: LLMEndpointRequest, logger: GenericLogger, max_parallel_thread: int = 10):
        threading.Thread.__init__(self, )
        self.thread_stop_thread = threading.Lock()
        self.stop_now: bool = False        
        self.queue: ThreadSafeQueue = ThreadSafeQueue(logger)

        self.line_updater: LLMEndpointRequest = line_updater
        self.logger: GenericLogger = logger
        self.max_parallel_thread: int = max_parallel_thread
        self.running_thread_ids: List[MultithreadedAccess] = []
        self.statistics: Statistics = Statistics(logger)
 
    def add_element(self, metadata: Metadata) -> None:
        self.queue.add_element(metadata)

    def is_empty(self) -> bool:
        return self.queue.is_empty()

    def size(self) -> int:
        return self.queue.size()
 
    def pop_next_element(self) -> Metadata:
        return self.queue.pop_next_element()

    def pack(self) -> None:
        pass

    def trigger_process_start(self) -> None:
        pass
    def join_all(self) -> None:
      while(not self.queue.is_empty()):
          time.sleep(1)
      for thread_id in self.running_thread_ids:
          thread_id.join()

    def stop(self):
        self.thread_stop_thread.acquire()
        self.stop_now = True
        self.thread_stop_thread.release()

    def __get_stop_now(self) -> bool:
        stop_now: bool = False

        self.thread_stop_thread.acquire()
        stop_now = self.stop_now
        self.thread_stop_thread.release()

        return stop_now

    def process_all(self) -> None:
        initial_size: int = self.queue.size()
        last_informed_statistics = datetime.now()
        backofftime_handler: BackoffTimeHandler = BackoffTimeHandler()
        for queue_element_id in range(self.queue.size()):
            paragraph: str = self.queue.get_element(queue_element_id).metadata.get_text_to_transform()
            if len(paragraph) > 0:
                self.logger.log_info(f"Pragraph {queue_element_id} saved in queue: {paragraph[0:50]}...")
            else:
                self.logger.log_debug(f"Pragraph {queue_element_id} saved in queue is empty...")


        old_information: str = ""
        while not self.__get_stop_now() and ((not self.queue.is_empty()) or len(self.running_thread_ids) > 0):
            #queue_element_id_list: List[int] = range(min(self.queue.size(), self.max_parallel_thread - len(self.running_thread_ids))) #self.queue.get_not_processing_metadata()[0: self.max_parallel_thread - len(self.running_thread_ids)]
            for queue_element_id in range(min(self.queue.size(), self.max_parallel_thread - len(self.running_thread_ids))):
                self.logger.log_debug(f"Adding to thread {queue_element_id}: {self.queue.get_next_element().metadata.get_text_value()[0:50]}")
                thread_id: MultithreadedAccess = MultithreadedAccess(self.line_updater,
                                                     self.queue.get_next_element(), 
                                                     backofftime_handler,
                                                     self.statistics,
                                                     self.logger)
                self.queue.delete_next_element()
                self.running_thread_ids.append(thread_id)
                thread_id.start()
            
            new_information: str = f"Remaining number of parapgraphs to send to threads {self.queue.size()} (Out of {initial_size} paragraphs = {100 - int(100 * self.queue.size() / initial_size)} % done), number of threads running: {len(self.running_thread_ids)}"
            if new_information != old_information:
                self.logger.log_info(new_information)
            old_information = new_information
            threads_to_forget: List[MultithreadedAccess] = []
            if (datetime.now() - last_informed_statistics).total_seconds() > 10:
                self.logger.log_debug(self.statistics.get_statistics())
                self.logger.log_debug(f'self.queue.is_empty(): {self.queue.is_empty()} ({self.queue.size()}),  len(self.running_thread_ids): {len(self.running_thread_ids)}')
                for cur_thread_id in self.running_thread_ids:
                    thread_status, last_epoch = cur_thread_id.get_status()
                    difftime: datetime.date = datetime.now() - last_epoch
                    current_metadata: str = cur_thread_id.get_metadata().metadata
                    line: str = f'cur_thread_id: {cur_thread_id}, status: {thread_status} since {difftime}, paragraph: {current_metadata.get_text_value()[0:50]}'
                    if difftime.total_seconds() > 15:
                        self.logger.log_info(line)
                        # Recreate and forget threads taking too much time
                        if difftime.total_seconds() > 180:
                            self.queue.add_element(current_metadata)
                            self.logger.log_warn(f"Skipping and thread {cur_thread_id} and preparing its recreation:{current_metadata.get_text_value()[0:50]} ")
                            cur_thread_id.skip_this_thread()
                            threads_to_forget.append(cur_thread_id)
                    else:
                        self.logger.log_debug(line)

                last_informed_statistics = datetime.now()
            for index in range(len(self.running_thread_ids)):
                if index < len(self.running_thread_ids):
                    if not self.running_thread_ids[index].is_alive() or self.running_thread_ids[index] in threads_to_forget:
                        self.logger.log_debug(f"Thread id {self.running_thread_ids[index].get_thread_id()} finished or was running too long!\n" +\
                                              f"  - text transformed: {self.running_thread_ids[index].get_transformed_text()[0:50]}... ")

                        del self.running_thread_ids[index]

            time.sleep(0.1)
        
        for thread_ptr in self.running_thread_ids:
            self.logger.log_info(f"Joining thread {thread_ptr.get_thread_id()}")            
            thread_ptr.join()
        self.logger.log_info(self.statistics.get_statistics())
        self.logger.log_info("Done!")