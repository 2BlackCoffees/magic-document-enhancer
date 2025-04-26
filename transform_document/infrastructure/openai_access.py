from openai import OpenAI
import time
import os
import re 
from typing import List

from infrastructure.generic_logger import GenericLogger
from domain.iml_access import IMLAccess
from pprint import pformat

class OpenAIAccess(IMLAccess):
    client = OpenAI(
        base_url=os.getenv("OPENAI_BASE_URL"),
        # base_url="https://api.openai.com/v1"
        # api_key=os.getenv("OPENAI_API_KEY") is default
    )
    def __init__(self, logger: GenericLogger, model_name: str = 'llama3-70b'):
        logger.log_trace(f"Using OpenAI model: {model_name}")
        self.logger: GenericLogger = logger
        self.model_name = model_name
    
    def try_transform_line(self, text_to_transform: str, how_to_transform: List, temperature: float, top_p: float) -> str:
        user_assistant_msgs = [
            {"role": "user", 
            "content": f'[Transform the text following strictly the associated requests] {text_to_transform}'} 
        ]

        messages: List = how_to_transform
        messages.extend(user_assistant_msgs)

        self.logger.log_trace(f'OpenAILineUpdateText.try_transform_line:\n'+\
                              f' text_to_transform = {text_to_transform}\n '+\
                              f' how_to_transform = {how_to_transform}')

        review = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            top_p=top_p
        )

        return_message = re.sub(r'\'\s+.*refusal=.*,.*role=.*\)', '', re.sub(r'ChatCompletionMessage\(content=', '', str(review.choices[0].message.content.strip())))

        return return_message
        
    def transform_line(self, line_to_transform: str, how_to_transform: str, temperature: float, top_p: float):
        openai_response: bool = False
        sleep_time = 10
        response: dict = {}

        self.logger.log_trace(f'OpenAILineUpdateText.transform_line:\n model = {self.model_name}\n line_to_transform = {line_to_transform}\n how_to_transform = {how_to_transform}')
        while not openai_response:
            try:
                response = self.try_transform_line(line_to_transform, how_to_transform, temperature, top_p)
                openai_response = True
            except Exception as err:                    
                self.logger.log_warn(f"Caught exception {err=}, {type(err)=}\nMessage: {pformat(line_to_transform)}")
                if "ContextWindowExceededError" in str(err):
                    self.logger.log_error(f"It seems your request is too big.")
                    #raise ContextWindowExceededError(f"{request_name}: It seems the size of your request is too big.")
                self.logger.log_warn(f"Backoff retry: Sleeping {sleep_time} seconds.")
                time.sleep(sleep_time)
                if sleep_time < 30:
                    sleep_time = sleep_time * 2
        return response
                    
