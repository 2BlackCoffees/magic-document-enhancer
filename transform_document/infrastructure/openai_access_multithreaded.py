from enum import StrEnum
from dataclasses import dataclass
from datetime import datetime
import threading
from typing import List, Tuple
import time

from domain.logger import GenericLogger
from domain.queue import MultithreadedMetadata
from domain.llm_endpoint_request import LLMEndpointRequest


class ThreadStatus(StrEnum):
    THREAD_CREATED = "Thread created: Step 1  out of 8"
    THREAD_STARTED = "Thread started: Step 2  out of 8"
    METADATA_NONE = "Meta data none skipping thread"
    ACCESSING_PARAGRAPH_FROM_DOCUMENT = "Before calling openAI: Step 3  out of 8"
    READY_TO_CALL_OPENAI = "Before calling openAI: Step 5  out of 8"
    CALLING_OPENAI_THREAD_SKIPPED = "Thread was requested to skip modifying source document: Step 5  out of 8"
    READY_TO_UPDATE_PARAGRAPH = "Done with OpenAI updating results: Step 6  out of 8"
    FINISHED_UPDATING_PARAGRAPH = "Data updated: Step 7  out of 8"
    EXCEPTION_ARISED = "Exception arose will lead to backoff"
    THREAD_FINISHED = "Thread finished: Step 8  out of 8"
    STILL_RIUNNING = "Still running status"

@dataclass
class TimingDiffInformation:
    from_status: ThreadStatus
    to_status: ThreadStatus
    elapsed_time: float
    last_epoch: datetime.date
    line_to_transform: str
    thread_id: str


class Statistics:
    def __init__(self, logger: GenericLogger):
        self.thread_lock = threading.Lock()
        self.timing_information: List[TimingDiffInformation] = []
        self.logger: GenericLogger = logger

    def add_statistic(self, from_status: ThreadStatus, to_status: ThreadStatus, last_epoch: datetime.date, line_to_transform: str, thread_id: str) -> None:
        self.thread_lock.acquire()
        if from_status in [ ThreadStatus.THREAD_CREATED, 
                            ThreadStatus.THREAD_STARTED, 
                            ThreadStatus.ACCESSING_PARAGRAPH_FROM_DOCUMENT ]:
            for information in self.timing_information:
                if information.line_to_transform == line_to_transform and\
                   information.to_status == ThreadStatus.FINISHED_UPDATING_PARAGRAPH:
                    self.logger.log_warn(f"Paragraph: {line_to_transform}, from thread {thread_id} was already successfully processed in thread {information.thread_id}!!")
        self.timing_information.append(TimingDiffInformation(from_status, to_status, (datetime.now() - last_epoch).total_seconds(), datetime.now(), line_to_transform, thread_id))
        self.thread_lock.release()

    def get_statistics(self) -> str:
        self.thread_lock.acquire()
        tmp_sorted_list: List[TimingDiffInformation] = []
        for elt in self.timing_information:
            tmp_sorted_list.append(elt)
            # if elt.to_status != ThreadStatus.THREAD_FINISHED:
            #     tmp_sorted_list.append(TimingDiffInformation(elt.to_status, ThreadStatus.STILL_RIUNNING, (datetime.now() - elt.last_epoch).total_seconds(), datetime.now(), elt.comment))
        self.thread_lock.release()
        sorted_list = sorted(tmp_sorted_list, key=lambda x: x.elapsed_time)
        string_return: str = "\n".join(f'Statistic: {item.elapsed_time} s, From: {item.from_status}, To: {item.to_status}, Line to transform: {item.line_to_transform[0:50]}..., threadId: {item.thread_id}' for item in sorted_list[-10:])
        return f'\nStatitics:\n\n{string_return}'

class BackoffTimeHandler:
    def __init__(self):
        self.time: int = 5
        self.max_time = 40
        self.thread_lock = threading.Lock()

    def increase_backoff_time(self) -> None:
        self.thread_lock.acquire()
        self.time = int(self.time * 2) % self.max_time
        self.thread_lock.release()

    def reset(self) -> None:
        self.thread_lock.acquire()
        self.time = 5
        self.thread_lock.release()

    def get_backoff_time(self) -> int:
        self.thread_lock.acquire()
        return_value: int = self.time
        self.thread_lock.release()

        return return_value

class MultithreadedAccess(threading.Thread):
    init_value = 1
    def __init__(self, llm_request: LLMEndpointRequest, metadata: MultithreadedMetadata, backofftime_handler: BackoffTimeHandler, statistics: Statistics, logger: GenericLogger):
        threading.Thread.__init__(self, )
        self.llm_request: LLMEndpointRequest = llm_request
        self.backoff_retry_needed_value = False
        self.metadata: MultithreadedMetadata = metadata
        self.thread_lock = threading.Lock()
        self.thread_lock_update_document = threading.Lock()
        self.thread_lock_update_status = threading.Lock()
        self.logger: GenericLogger = logger
        self.thread_status: ThreadStatus = ThreadStatus.THREAD_CREATED
        self.statistics = statistics
        self.last_epoch: datetime.date = datetime.now()
        self.backofftime_handler: BackoffTimeHandler = backofftime_handler
        self.thread_lock.acquire()
        self.thread_id = str(MultithreadedAccess.init_value)
        self.want_to_skip_this_thread: bool = False
        MultithreadedAccess.init_value += 1 
        self.thread_lock.release()

    def get_thread_id(self) -> str:
        return self.thread_id
    
    def get_status(self) -> Tuple[str, datetime.date]:
        return self.thread_status, self.last_epoch
    
    def update_thread_status(self, thread_status: ThreadStatus, comment: str = "") -> None:
        self.statistics.add_statistic(self.thread_status, thread_status, self.last_epoch, comment, self.thread_id)
        self.thread_lock_update_status.acquire()
        self.last_epoch = datetime.now()
        self.thread_status = thread_status
        self.thread_lock_update_status.release()

    def get_thread_status(self) -> ThreadStatus:
        self.thread_lock_update_status.acquire()
        thread_status: ThreadStatus = self.thread_status
        self.thread_lock_update_status.release()
        return thread_status
    
    def skip_this_thread(self) -> None:
        self.thread_lock_update_status.acquire()
        self.thread_status = ThreadStatus.CALLING_OPENAI_THREAD_SKIPPED
        self.want_to_skip_this_thread = True
        self.thread_lock_update_status.release()
    
    def skip_requested(self):
        want_to_skip_this_thread: bool = False
        self.thread_lock_update_status.acquire()
        want_to_skip_this_thread = self.want_to_skip_this_thread
        self.thread_lock_update_status.release()
        return want_to_skip_this_thread

    def get_metadata(self) -> MultithreadedMetadata:
        return self.metadata
    
    def get_transformed_text(self) -> str:
        return self.metadata.metadata.get_text_to_transform()
    
    def run(self) -> None:
        self.update_thread_status(ThreadStatus.THREAD_STARTED)
        if self.metadata is not None:
            self.update_thread_status(ThreadStatus.ACCESSING_PARAGRAPH_FROM_DOCUMENT)
            line_to_transform: str = self.metadata.metadata.get_text_to_transform()
            paragraph_updated: bool = False
            backoff_requested: bool = False
            while not paragraph_updated and not self.skip_requested():
                try:
                    self.update_thread_status(ThreadStatus.READY_TO_CALL_OPENAI, line_to_transform)
                    new_paragraph: str = self.llm_request.try_transform_text(line_to_transform, self.metadata.metadata.get_request_type())
                    if not self.skip_requested():
                        self.update_thread_status(ThreadStatus.READY_TO_UPDATE_PARAGRAPH, line_to_transform)
                        self.metadata.metadata.update_llm_response_in_document(new_paragraph, self.metadata.metadata.get_request_type())
                        self.update_thread_status(ThreadStatus.FINISHED_UPDATING_PARAGRAPH, line_to_transform)
                    paragraph_updated = True
                    if backoff_requested:
                        self.backofftime_handler.reset()
                except Exception as err:
                    if not self.skip_requested():
                        self.update_thread_status(ThreadStatus.EXCEPTION_ARISED, line_to_transform)
                        self.logger.log_debug(f"Caught exception {err=}, {type(err)=},")
                        self.logger.log_warn(f"Exception (Possibly due to throttling), Line to transform was:\n   {line_to_transform}.")
                        #self.set_backoff_retry_needed(True)
                        self.backofftime_handler.increase_backoff_time()
                        self.logger.log_info(f"Backoff requested by thread handling {line_to_transform[0:50]} : sleeping now {self.backofftime_handler.get_backoff_time()} seconds")
                        time.sleep(self.backofftime_handler.get_backoff_time())
                        backoff_requested = True
        else:
            self.update_thread_status(ThreadStatus.METADATA_NONE, line_to_transform)
        self.update_thread_status(ThreadStatus.THREAD_FINISHED, line_to_transform)


     

                    

            

            
