from typing import Dict, List
import json
import sys
import re
import csv
from pprint import pprint, pformat
from pathlib import Path
from infrastructure.generic_logger import GenericLogger

class LLMUtils:
    HOW_TO_TRANSFORM: str = 'how_to_transform'
    REQUEST: str = 'request'
    TEMPERATURE: str = "temperature"
    TOP_P: str = "top_p"
    DEFAULT_REQUEST: str = "default_request"
    TABLE_REQUEST: str = "table_request"
    HEADING_REQUEST: str = "heading_request"
    ALL_REQUESTS: str = "all_requests"

    def __init__(self, additional_requests_file_name: str, language: str, logger: GenericLogger):
        self.logger = logger
        self.additional_requests: List = self.__read_json(additional_requests_file_name)
        self.set_requests(language)

    def set_requests(self, language: str):
        default_rules: str = f"- Use the context as additional information but DO NOT REPHRASE ITS CONTENT. "+\
                              "The context is used to provide more details to the request and help you improve your response."+\
                            f"- Provide NO explanation of any change you perform.\n"+\
                            f"- Provide NO comment regarding any change.\n" +\
                            f"- Do NOT modify the meaning of the text.\n"
        table_cell_rules: str = "- Return a MD table only.\n"+\
                        "- Ensure the number of rows and columns is kept strictly identical to the table provided in input.\n"

        heading_rules: str = "- Keep around 20% of the initial number of words or up to 5 words\n" +\
                        "- Consider this is the text of a heading.\n"

        self.all_requests = [
            {'request_name': 'Improve document for technical stakeholders', 
             self.HOW_TO_TRANSFORM: [
                { "role": "system", 
                  "content": f"You are a native {language} writer higly skilled to improve the readability of technical {language} text.\n"
                },
                { "role": "user", 
                  self.ALL_REQUESTS: {
                    self.DEFAULT_REQUEST: 
                            "- Improve the formulation of the text to make it very clear for deep technical people. \n"+\
                            "- Enhance technical explanations or technical words.\n"+\
                            "- Ensure the text can be shared with a large technical audience.\n" +\
                            default_rules,
                    self.TABLE_REQUEST: 
                            table_cell_rules + \
                            "- Improve the formulation of the text for each cell to make it very clear for deep technical people.\n" +\
                            default_rules,
                    self.HEADING_REQUEST: 
                            heading_rules + \
                            "- Improve the formulation of the text to make it very clear for deep technical people.\n" +\
                            default_rules,
                  }
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
                  self.ALL_REQUESTS: {
                    self.DEFAULT_REQUEST: 
                            "- Create text taking into account the inputs provided.\n"+\
                            "- Create a detailed and comprehensive text.\n"+\
                            "- Ensure technical explanations or technical words of the text can be shared with a large technical audience.\n" +\
                            default_rules,
                    self.TABLE_REQUEST: 
                            table_cell_rules + \
                            "- Create text for each cell taking into account the inputs provided.\n"+\
                            "- Improve text formulation.\n"+\
                            "- Ensure technical explanations or technical words of the text can be shared with a large technical audience.\n" +\
                            default_rules,
                    self.HEADING_REQUEST: 
                            heading_rules + \
                            "- Create text taking into account the inputs provided.\n"+\
                            "- Improve text formulation.\n"+\
                            "- Ensure technical explanations or technical words of the text can be shared with a large technical audience.\n" +\
                            default_rules,
                  }
                }
             ],
             self.TEMPERATURE: 0.6, self.TOP_P: 0.6 
            },
            {'request_name': 'Improve document for sales and non technical stakeholders', 
             self.HOW_TO_TRANSFORM: [
                { "role": "system", 
                  "content": 
                        f"- You are a native {language} writer\n"+\
                         "- You are higly skilled to IMPROVE the readability of technical {language} text for non technical stakeholders.\n"+\
                         "- Target audience are sales professionals and non technical stakeholders.",
                },
                { "role": "user", 
                  self.ALL_REQUESTS: {
                    self.DEFAULT_REQUEST: 
                            "- IMPROVE the formulation of the text targetting sales people.\n"+\
                            "- Ensure the rephrased text helps sales people understand and sell our services, platforms, tools and accelerators.\n"+\
                            "- The text must be rephrased taking into account a higher level technical view, simplifying technical details\n" +\
                            default_rules,
                    self.TABLE_REQUEST: 
                            table_cell_rules + \
                            "- IMPROVE the formulation of the text of each cell targetting sales people.\n"+\
                            default_rules,
                    self.HEADING_REQUEST: 
                            heading_rules + \
                            "- IMPROVE the formulation of the text targetting sales people.\n"+\
                            default_rules,
                  }
                }
             ],
             self.TEMPERATURE: 0.2, self.TOP_P: 0.6
            },
            {'request_name': 'Create document document for sales and non technical stakeholders', 
             self.HOW_TO_TRANSFORM: [
                { "role": "system", 
                  "content": 
                        f"- You are a native {language} writer\n"+\
                        "- You are higly skilled to CREATE readable technical {language} text for non technical stakeholders.\n"+\
                        "- Target audience are sales professionals and non technical stakeholders.",
                },
                { "role": "user", 
                  self.ALL_REQUESTS: {

                    self.DEFAULT_REQUEST: 
                            "- CREATE text targetting sales people.\n"+\
                            "- Ensure the CREATED text helps sales people understand and sell our services, platforms, tools and accelerators.\n"+\
                            "- The text must be CREATED taking into account a higher level technical view, simplifying technical details\n" +\
                            default_rules,
                    self.TABLE_REQUEST: 
                            table_cell_rules + \
                            "- Ensure the CREATED text helps sales people understand and sell our services, platforms, tools and accelerators.\n"+\
                            default_rules,
                    self.HEADING_REQUEST: 
                            heading_rules + \
                            "- Ensure the CREATED text helps sales people understand and sell our services, platforms, tools and accelerators.\n"+\
                            default_rules,
                  }
                }
             ],
             self.TEMPERATURE: 0.6, self.TOP_P: 0.6 
            },
            {'request_name': 'Translate document', 
             self.HOW_TO_TRANSFORM: [
                { "role": "system", 
                  "content": 
                        f"You are a native {language} writer higly skilled to translate technical and non technical text.\n"+\
                         "- You can ensure a very accurate translation.",
                },
                { "role": "user", 
                  self.ALL_REQUESTS: {
                    self.DEFAULT_REQUEST: 
                            f"Translate the text to {language} accurately.\n" +\
                            default_rules,
                    self.TABLE_REQUEST: 
                            table_cell_rules + \
                            f"Translate the text to {language} accurately.\n" +\
                            default_rules,
                    self.HEADING_REQUEST: 
                            heading_rules + \
                            f"Translate the text to {language} accurately.\n" +\
                            default_rules,
                  }
                }
             ],
             self.TEMPERATURE: 0.4, self.TOP_P: 0.6 
            }
        ]
        self.all_requests.extend(self.additional_requests)
    
    def get_final_request(how_to_transform: Dict, what_to_transform: str, logger: GenericLogger) -> List:
        final_request: List = []
        role: str = "role"
        logger.log_trace(f"Transforming request\n{pformat(how_to_transform)}\n, leveraging {pformat(what_to_transform)}\n")
        for request in how_to_transform:
            if role in request and LLMUtils.ALL_REQUESTS in request:
                if what_to_transform in request[LLMUtils.ALL_REQUESTS]:
                    context: str = "\n".join( f"[{req}]" for req in request[LLMUtils.ALL_REQUESTS][what_to_transform].split('\n'))
                    final_request.append({
                        role: request[role], 
                        "content": context
                    })
                else:
                    logger.log_error(f"Request type {pformat(what_to_transform)} does not exist in {pformat(how_to_transform)}, skipping it.")
            else:
                final_request.append(request)
        logger.log_trace(f"Request creation: {pformat(final_request)} from templated request: {pformat(request)}")
        return final_request
             
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

    def md_to_lists(md_table_str: str, logger: GenericLogger) -> List:
        logger.log_trace(f"Transforming MD table to list: {md_table_str}")
        #lines: List = [re.sub(r'\|\s*$', '', re.sub(r'\|\|', '| |', line.strip())) for line in md_table_str.split("\n")]
        lines = [re.sub(r'^\s*\|', '', re.sub(r'\|\s*$', '', "| ".join(line.strip().split("|")))) for line in md_table_str.split("\n")]
        logger.log_trace(f"Table simplified to: {lines}")

        csv_reader = list(csv.reader(lines, delimiter="|"))
        table_from_csv: List = [reader for id, reader in enumerate(csv_reader) if id != 1]
        logger.log_trace(f"CSV Reader: {table_from_csv}")
        md_table_list = []

        for row_id, row in enumerate(table_from_csv):
            logger.log_trace(f"Analyzing row: {pformat(row)}")
            # if not saved_headers:
            #     md_table_list.append([value.strip() for value in list(row.keys())])
            #     logger.log_trace(f"Appended headers {md_table_list}")
            #     saved_headers = True
            row_values: List = []
            logger.log_trace(f"Updating row (row_id:{row_id}) from {list(row)}")
            for col_id, value in enumerate(row):
                if isinstance(value, str): 
                    row_values.append(value.strip())
                    logger.log_trace(f"Updated element (row_id:{row_id}, col_id: {col_id}) to {value.strip()}")

                else:
                    logger.log_warning(f"Skipping value that was expected to be a string but is a type {type(value)}: {pformat(value)}")
            md_table_list.append(row_values)
            logger.log_trace(f"Appended row {md_table_list}")

        logger.log_trace(f"Transformed table to list: {md_table_list}")

        return md_table_list

