import openai
import time
import random
from typing import List
from infrastructure.generic_logger import GenericLogger
from domain.iml_access import IMLAccess

class OpenAIDebugAccess(IMLAccess):
    def __init__(self, logger: GenericLogger):

        self.logger: GenericLogger = logger
        self.paragraphs: List[str] = []
    
    def try_transform_line(self, line_to_transform: str, how_to_transform: str) -> str:

        if line_to_transform in self.paragraphs:
            self.logger.log_error(f"Paragraph {line_to_transform[0:50]} was already asked for being processed!")
            exit(1)
 
        time_to_sleep: int = 10 + random.randrange(10)
        self.logger.log_info(f"Fake sleeping {time_to_sleep} seconds for {line_to_transform[0:50]}")
        time.sleep(time_to_sleep)

        if random.randrange(100) > 80:
            raise Exception("Faked exception")

        return f"Successfully faked processe: {line_to_transform}"
        
    def transform_line(self, line_to_transform: str, how_to_transform: str):
        openai_response: bool = False
        sleep_time = 10
        response: dict = {}

        self.logger.log_trace(f'OpenAIDebigLineUpdateText.transform_line:\n  line_to_transform = {line_to_transform[0:50]}\n')
        while not openai_response:
            try:
                response = self.try_transform_line(line_to_transform, how_to_transform)
                openai_response = True
            except openai.error.RateLimitError as err:
                self.logger.log_warn(f"Caught exception {err=}, {type(err)=}")
                self.logger.log_warn(f"Backoff retry: Sleeping {sleep_time} seconds.")
                # openai.error.RateLimitError: Rate limit reached for 10KTPM-200RPM in organizationorg-DJFV6GAvfsqpzZTlZwFSm6De on tokens  per min. 
                # Limit: 10000 / min. Please try again in 6ms. 
                # Contact us through our help center at help.openai.com if you continue to have issues.
                # It could be the API Key needs to be rotated!
                time.sleep(sleep_time)
                if sleep_time < 30:
                    sleep_time = sleep_time * 2
            except Exception as err:
                self.logger.log_warn(f"Caught exception {err=}, {type(err)=}")
                self.logger.log_warn(f"Backoff retry: Sleeping {sleep_time} seconds.")
                time.sleep(sleep_time)
                if sleep_time < 30:
                    sleep_time = sleep_time * 2

        return response
                    
