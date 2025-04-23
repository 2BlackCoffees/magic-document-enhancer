from typing import Dict, List
import json
import sys
from pprint import pprint, pformat
from pathlib import Path
from infrastructure.generic_logger import GenericLogger
class LLMUtils:
    HOW_TO_TRANSFORM: str = 'how_to_transform'
    REQUEST: str = 'request'
    TEMPERATURE: str = "temperature"
    TOP_P: str = "top_p"
    def __init__(self, additional_requests_file_name: str, language: str, logger: GenericLogger):
        self.logger = logger
        self.additional_requests: List = self.__read_json(additional_requests_file_name)
        self.set_requests(language)

    def set_requests(self, language: str):
        self.all_requests = [
            {'request_name': 'Improve document for technical stakeholders', 
             self.HOW_TO_TRANSFORM: [
                { "role": "system", 
                  "content": f"You are a native {language} writer higly skilled to improve the readability of technical {language} text.\n"
                },
                { "role": "user", 
                  "content": 
                        "- Please improve the formulation of the text to make it very clear for deep technical people. Please enhance technical explanations or technical words ensuring the text can be shared with a large technical audience.\n" +\
                        f"- Provide NO explanation of any change you perform.\n"+\
                        f"- Provide NO comment regarding any change.\n" +\
                        f"- Do NOT modify the meaning of the text.\n" +\
                        f"- If you cannot improve then provide the same text.\n"
                }
             ],
             self.TEMPERATURE: 0.2, self.TOP_P: 0.4 
            },
            {'request_name': 'Create document document for technical stakeholders', 
             self.HOW_TO_TRANSFORM: [
                { "role": "system", 
                  "content": 
                        f"You are a native {language} writer higly skilled to create technical " +\
                        f"{language} text.\n"
                      
                },
                { "role": "user", 
                  "content": 
                        "- Please create text taking into account the inputs creating a detailed and comprehensive document. Please ensure technical explanations or technical words of the text can be shared with a large technical audience.\n" +\
                        f"- Provide NO explanation of any change you perform.\n"+\
                        f"- Provide NO comment regarding any change.\n" +\
                        f"- Do NOT modify the meaning of the text.\n" +\
                        f"- If you cannot improve then provide the same text.\n",
                }
             ],
             self.TEMPERATURE: 0.6, self.TOP_P: 0.6 
            },
            {'request_name': 'Improve document for sales and non technical stakeholders', 
             self.HOW_TO_TRANSFORM: [
                { "role": "system", 
                  "content": 
                        f"You are a native {language} writer higly skilled to improve the readability of technical " +\
                        f"{language} text for sales an non technical stakeholders.",
                },
                { "role": "user", 
                  "content": 
                        "Please improve the formulation of the text helping sales people better selling our services, platforms, tools and accelerators. The text must be rephrased with a higher level view, skipping technical details\n" +\
                        f"- Provide NO explanation of any change you perform.\n"+\
                        f"- Provide NO comment regarding any change.\n" +\
                        f"- Do NOT modify the meaning of the text.\n" +\
                        f"- If you cannot improve then provide the same text.\n",
                }
             ],
             self.TEMPERATURE: 0.2, self.TOP_P: 0.6
            },
            {'request_name': 'Create document document for sales and non technical stakeholders', 
             self.HOW_TO_TRANSFORM: [
                { "role": "system", 
                  "content": 
                        f"You are a native {language} writer higly skilled to create technical " +\
                        f"{language} text for non technical audience selling our products.\n",
                },
                { "role": "user", 
                  "content": 
                        "- Please create text taking into account the inputs creating a detailed and comprehensive document. Please ensure descriptions of the text can target a large non technical audience.\n" +\
                        f"- Provide NO explanation of any change you perform.\n"+\
                        f"- Provide NO comment regarding any change.\n" +\
                        f"- Do NOT modify the meaning of the text.\n" +\
                        f"- If you cannot improve then provide the same text.\n",
                }
             ],
             self.TEMPERATURE: 0.6, self.TOP_P: 0.6 
            },
            {'request_name': 'Translate document', 
             self.HOW_TO_TRANSFORM: [
                { "role": "system", 
                  "content": 
                        f"You are a native {language} writer higly skilled to translate technical and non technical ensuring a very accurate translation.",
                },
                { "role": "user", 
                  "content": 
                       "Please translate the text to {language} accurately.\n" +\
                        f"- Provide NO explanation of any change you perform.\n"+\
                        f"- Provide NO comment regarding any change.\n" +\
                        f"- Do NOT modify the meaning of the text.\n" +\
                        f"- If you cannot improve then provide the same text.\n",
                }
             ],
             self.TEMPERATURE: 0.4, self.TOP_P: 0.6 
            }
        ]
        self.all_requests.extend(self.additional_requests)
    
    def set_default_temperature_top_p_requests(self, list_requests: List, new_temperature: float, new_top_p: float) -> None:
        for request in list_requests:
            if new_temperature is not None:
                request['temperature'] = new_temperature
            if new_top_p is not None:
                request['top_p'] = new_top_p


    def set_default_temperature(self, new_temperature: float) -> None:
        """
        @brief Sets the temperature for all LLM requests.
        @param new_temperature The new temperature value.
        """
        self.set_default_temperature_top_p_requests(self.all_requests, new_temperature, None)
        
    def set_default_top_p(self, new_top_p: float) -> None:
        """
        @brief Sets the top_p value for all LLM requests.
        @param new_top_p The new top_p value.
        """
        self.set_default_temperature_top_p_requests(self.all_requests, None, new_top_p)

    def __read_json(self, filename: str):
        path = Path(filename)
        if path.is_file():
            with open(filename) as f:
                return json.load(f)
        return []

    def __get_all_requests(self, request_list: List, from_list: List = None):
        if from_list is None:
            return request_list
        else:
            return [ request_list[idx] for idx in from_list ]
    
    def get_request(self, request_index: int) -> Dict: 
        if 0 <= request_index < len(self.all_requests):
            return self.all_requests[request_index]

        self.logger.log_error(f"You set transformation {request_index} but it must be comprised between 0 and {len(self.all_requests)}")
        sys.exit(1)

    def get_all_requests(self, from_list: List = None):
        return self.__get_all_requests(self.all_requests, from_list)
    
    def __get_all_requests_and_ids(self, request_list: List, from_list: List = None):
        all_requests: List = []
        for idx, llm_request in enumerate(request_list):
            if from_list is None or idx in from_list:
                all_requests.append({'idx': idx, 'llm_request': llm_request['request_name']})
        return all_requests    
    
    def get_all_requests_and_ids(self, from_list: List = None):
        return self.__get_all_requests_and_ids(self.all_requests, from_list)
        
    def get_all_requests_and_ids_str(self, from_list: List = None, separator: str = " *** "):
        all_requests = self.get_all_requests_and_ids(from_list)
        return separator.join([f"{req['idx']}: {req['llm_request']}" for req in all_requests])

    @staticmethod
    def get_list_parameters(parameters):
        parameter_list: List = []
        for parameter in parameters:
            if '-' in parameter:
                parameter_range = parameter.split('-')
                for parameter_nb in range(int(parameter_range[0]), int(parameter_range[1]) + 1):
                    parameter_list.append(int(parameter_nb))
            else:
                parameter_list.append(int(parameter))
        return parameter_list
    
    @staticmethod
    def get_list_parameters(parameters):
        parameter_list: List = []
        for parameter in parameters:
            if '-' in parameter:
                parameter_range = parameter.split('-')
                for parameter_nb in range(int(parameter_range[0]), int(parameter_range[1]) + 1):
                    parameter_list.append(int(parameter_nb))
            else:
                parameter_list.append(int(parameter))
        return parameter_list
