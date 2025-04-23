#!/usr/bin/env python
import os
import sys
import argparse
from pstats import SortKey
from pathlib import Path
import signal
from datetime import datetime
from functools import partial
from typing import List

from services.application_service import ApplicationService
from domain.logger import Logger, LoggerType
from domain.llm_utils import LLMUtils

logger: Logger = Logger(LoggerType.INFO)
application_service: ApplicationService = None

# def signal_handler(sig, frame):
#     logger.log_error('Request to stop the program!')
#     if application_service is not None:
#         logger.log_warn('Trying emergency save before exiting!')
#         application_service.emergency_save()
#     else:
#         logger.log_warn('No emergency save possible before exiting!')
#     logger.log_warn('Exiting')
#     sys.exit(0)

# signal.signal(signal.SIGINT,    signal_handler)
# signal.signal(signal.SIGABRT,   signal_handler)
# signal.signal(signal.SIGSEGV,   signal_handler)
# signal.signal(signal.SIGTERM,   signal_handler)
# signal.signal(signal.SIGILL,    signal_handler)

def main() -> None:
    program_name = os.path.basename(sys.argv[0])
    paragraph_start_min_word_numbers: int = 1
    paragraph_start_min_word_length: int = 2
    max_number_threads: int = 1 #math.floor(max((os.cpu_count() - 1), 2) * 1.2)
    from_document: str = None 
    to_document: str = None 
    transformation: int = 0 
    from_language: str = "english" 
    to_language: str = "" 
    engine="llama3-70b"
    required_parameters_activation: bool = True
    from_language="english" 
    logger_type: LoggerType = LoggerType.INFO
    use_debugger_ai: bool = False
    csv_ = partial(str.split, sep=',')

    debug: bool = True
    if debug:
        #engine="gpt-4"
        base_name: str = "Simple"
        suffix:str = "docx"
        transformation = 0 
        from_document = f"{base_name}.{suffix}"
        required_parameters_activation = False
        #logger_type = LoggerType.DEBUG
    logger = Logger(logger_type)
    llm_utils: LLMUtils = LLMUtils(os.getenv("MAGIC_ADDITIONAL_REQUEST", default=""), from_language, logger)
    parser = argparse.ArgumentParser(prog=program_name)
    parser.add_argument('--from_document', type=str, help='Specify the document to open: If document name ends with doc(x), consider a Microsoft Word document, consider PowerPoint if document name ends with ppt(x).', required=required_parameters_activation)
    parser.add_argument('--to_document', type=str, help='Specify the document to save', required=False)
    parser.add_argument('--transformation', type=int, help=f'Specify one transformation request to process from the following list: [[ {llm_utils.get_all_requests_and_ids_str()} ]]')
    parser.add_argument('--skip_slides', type=csv_, help='For ppt(x) documents only: Specify slides to skip: 1,2-5,8: Cannot be used with only_slides')
    parser.add_argument('--only_slides', type=csv_, help='For ppt(x) documents only: Specify slides to keep: 1,2-5,8: Cannot be used with skip_slides')

    parser.add_argument('--paragraph_start_min_word_numbers', type=str, help=f'When defining the start of a line or paragraph this defines the minimum number of words ({paragraph_start_min_word_numbers} per default)', required=False)
    parser.add_argument('--paragraph_start_min_word_length', type=str, help=f'When defining the start of a line or paragraph this defines the minimum number of chars in each of the initial words ({paragraph_start_min_word_length} per default)', required=False)
    parser.add_argument('--use_debugger_ai', action="store_true", help='Use a fake ML engine to debug application')
    parser.add_argument('--debug', action="store_true", help='Set logging to debug')
    parser.add_argument('--trace', action="store_true", help='Set logging to trace')
    parser.add_argument('--max_number_threads', type=int, help=f'Specify the maximum number of parallel thread (Default {max_number_threads})', required=False)
    parser.add_argument('--language', type=str, help='Specify the language of your text', required=False)

    parser.add_argument('--engine', type=str, help='LLM Engine name.', required=False)

    args = parser.parse_args()
    
    if args.trace:# or debug:
        logger_type = LoggerType.TRACE
    elif args.debug:
        logger_type = LoggerType.DEBUG
    logger = Logger(logger_type)

    if args.skip_slides and args.only_slides:
        print("ERROR: Please either use option skip_slides or only_slides but not both!")
        sys.exit(0)

    slides_to_skip: List = []
    if args.skip_slides:
        slides_to_skip = LLMUtils.get_list_parameters(args.skip_slides)
    slides_to_keep: List = []
    if args.only_slides:
        slides_to_keep = LLMUtils.get_list_parameters(args.only_slides)

    if args.transformation:
        transformation = args.transformation           

    if args.from_document:
        from_document = args.from_document
    path = Path(from_document)
    if not path.is_file():
        logger.log_error(f'The file {from_document} does not seem to exist ({os.getcwd()}).')
        exit(1)
  
    if args.paragraph_start_min_word_numbers: 
        paragraph_start_min_word_numbers = args.paragraph_start_min_word_numbers
    
    if args.paragraph_start_min_word_length: 
        paragraph_start_min_word_numbers = args.paragraph_start_min_word_length

    if args.max_number_threads:
        max_number_threads = args.max_number_threads
        
    if args.language:
        from_language = args.language

    if args.engine:
        engine = args.engine

    if args.use_debugger_ai:
        use_debugger_ai = args.use_debugger_ai

    if args.to_document:
        to_document = args.to_document
    else:
        base_name: str = '.'.join(from_document.split('.')[0:-1])
        suffix: str = from_document.split('.')[-1]
        to_lang: str = f'-to-{to_language}' if to_language != "" else ""
        debugger_ai:str = '-use_debugger_ai' if use_debugger_ai else ""
        to_document = f"{base_name}{debugger_ai}-transformation-{transformation}-from-{from_language}{to_lang}-min_words_paragraph-{paragraph_start_min_word_numbers}-min_letters_word-{paragraph_start_min_word_length}-engine-{engine}-threads-{max_number_threads}.{suffix}"

    logger.log_info(f"Please make sure {args.from_document} is not opened.")
    started_epoch: datetime.date = datetime.now()

    application_service = ApplicationService(
        from_document, 
        to_document,
        transformation, 
        llm_utils,
        from_language,
        paragraph_start_min_word_numbers,
        paragraph_start_min_word_length,
        engine,
        max_number_threads,
        logger,
        use_debugger_ai,
        slides_to_skip,
        slides_to_keep)
    
    application_service.process()
    ended_epoch: datetime.date = datetime.now()
    logger.log_warn(f"Total run time: {ended_epoch - started_epoch}")
    logger.log_warn("It could be the script now stalls because of one to many threads that were skipped: Python might be wating they finish which typically depends on the timeout of the APIGW of OpenAI and is usually around 10 minutes.")

if __name__ == "__main__":
    main()
