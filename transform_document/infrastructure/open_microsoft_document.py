import re
from openpyxl import load_workbook
from pptx import Presentation
from typing  import List, Dict
from pprint import pprint, pformat
import sys

from domain.iopen_document import IOpenDocument
from domain.worker_class import Worker
from domain.queue import MetadataDoc, MetadataXls, MetadataPpt
from infrastructure.generic_logger import GenericLogger

class IOpenAndUpdateDocument(IOpenDocument):
    def __init__(self, document_path: str, 
                 worker: Worker, 
                 paragraph_start_min_word_numbers: int, paragraph_start_min_word_length: int,  
                 logger: GenericLogger):
        self.document_path = document_path
        self.worker = worker
        self.logger = logger
        self.paragraph_start_min_word_length = paragraph_start_min_word_length
        self.paragraph_start_min_word_numbers = paragraph_start_min_word_numbers
        self.worker: Worker = worker

    def is_paragraph(self, text: str):
        minwords: int = int(self.paragraph_start_min_word_numbers) - 1 if int(self.paragraph_start_min_word_numbers) - 1 >= 0 else 0
        return re.search(r'(\w{' + str(self.paragraph_start_min_word_length) + r',}\b\s+)'+\
                            r'{' + str(minwords) + r',}' +\
                                r'\w{' + str(self.paragraph_start_min_word_length) + r',}\b', text)
        
    def save(self, filename: str) -> None:
        self.document.save(filename)
        self.logger.log_info(f"Saved final document as {filename}")


class OpenXLSDocument(IOpenAndUpdateDocument):
    def __init__(self, document_path: str, 
                 worker: Worker, 
                 paragraph_start_min_word_numbers: int,
                 paragraph_start_min_word_length: int, 
                 logger: GenericLogger):
        super().__init__(document_path, 
                         worker, 
                         paragraph_start_min_word_numbers, paragraph_start_min_word_length, 
                         logger)
        self.document =  load_workbook(document_path)
    
    def __fill_tasks(self, xls_obj: any):
        for ws in xls_obj.worksheets:

            for row in range(1,ws.max_row + 1):
                for col in range(1,ws.max_column + 1):
                    current_text = str(ws.cell(row,col).value)
                    if current_text is not None and current_text != 'None' and self.is_paragraph(current_text): 
                        self.worker.add_work_element(MetadataXls(ws.cell(row,col)))

    def process(self):
        self.__fill_tasks(self.document)
        self.worker.process_all()

# class OpenPPTDocument(IOpenAndUpdateDocument):
#     def __init__(self, document_path: str, 
#                  worker: Worker, 
#                  paragraph_start_min_word_numbers: int,
#                  paragraph_start_min_word_length: int, 
#                  slides_to_keep: List,
#                  slides_to_skip: List,
#                  logger: GenericLogger):
#         super().__init__(document_path, 
#                          worker, 
#                          paragraph_start_min_word_numbers, paragraph_start_min_word_length, 
#                          logger)
#         self.document =  Presentation(document_path)
#         self.slides_to_keep = slides_to_keep
#         self.slides_to_skip = slides_to_skip

#     def __extract_ppt(self):

#         deck_content: List = []
#         for slide_idx, slide in enumerate(self.document.slides):

#             slide_number: int = slide_idx + 1
#             if slide_number in self.slides_to_skip:
#                 self.__print_slide_keep_skip_info(f"Skipped slide number {slide_number} as per request.")
#                 continue

#             if self.slides_to_keep is not None and len(self.slides_to_keep) > 0:
#                 if slide_number not in self.slides_to_keep:
#                     continue              

#             if slide.element.get('show', '1' == '0'):
#                 self.__print_slide_keep_skip_info(f"Skipped hidden slide number {slide_number}.")
#                 continue
 
#             self.logger.info(f"Analyzing slide number {slide_number}")
 
#             shape_descriptions: list = [] 
#             for shape in slide.shapes:
#                 if shape.has_text_frame:
#                     shape_descriptions.append(PPTReader.get_text_box_info(slide_number, shape))
 
#                 elif shape.has_table: 
#                     table = shape.table
#                     table_elements: list = []
#                     table_str: str = ""
#                     for row_idx, row in enumerate(table.rows, start = 1):
#                         table_str += "\n|"
#                         for col_idx, cell in enumerate(row.cells, start=1):
#                             if cell.text_frame is not None:
#                               text: str = cell.text_frame.text.replace("\n", " ")
#                               table_elements.append({'row': row_idx, 'col': col_idx, 'text': text})
#                               table_str += text + "|"
 
#                     shape_descriptions.append(PPTReader.get_table_info(slide_number, shape, table, table_elements, table_str))
 
#                 elif shape.shape_type == MSO_SHAPE_TYPE.GROUP: 
#                     shape_descriptions.append(PPTReader.get_group_info(slide_number, shape))
               
#                 else: 
#                     shape_descriptions.append(PPTReader.get_shape_type_info(slide_number, shape))
 
#             title_value: str = None
#             shape_title: Dict = None
#             title_found: bool = False
#             if hasattr(slide.shapes, "title") and hasattr(slide.shapes.title, "text") and slide.shapes.title.text is not None and len(slide.shapes.title.text) > 0:
#                 title_value = slide.shapes.title.text
#                 for shape_description in shape_descriptions:
#                     if shape_description["raw_text"] == title_value:
#                         shape_title = shape_description
#                         shape_title["json"]["shape"]["is_title"] = True
#                         title_found = True
#                 if not title_found:
#                     shape_description: Dict = PPTReader.create_title(slide_number, title_value)
#                     shape_title = shape_description
#                     shape_descriptions.append(shape_description)

#             sorted_shapes: List = PPTReader.get_sorted_shapes_by_pos_y(shape_descriptions)

#             slide_shapes_content, title, slide_info, reduced_slide_text = self.__get_slide_details(sorted_shapes, slide_number, shape_title)
#             slide_content: Dict = {
#                 "slide_info": slide_info,
#                 "title": title,
#                 "shapes": slide_shapes_content,
#                 "reduced_slide_text": reduced_slide_text
#             }

#             if self.want_selected_text_slide_requests or self.want_selected_artistic_slide_requests:
#                 self.content_out.add_title(1, f"Analyzing slide {slide_number} {title}")

#                 if self.want_selected_text_slide_requests:
#                     self.content_out.add_title(2, f"Check of text content for slide {slide_number}")
#                     checker: IChecker = TextSlideChecker(self.llm_utils, self.selected_text_slide_requests, f' (Slide {slide_idx + 1})', f' (Slide {slide_idx + 1})')
#                     self.llm_access.set_checker(checker)
#                     self.__send_llm_requests_and_expand_output(slide_content["shapes"], False)

#                 if self.want_selected_artistic_slide_requests:
#                     self.content_out.add_title(2, f"Check of artistic content for slide {slide_number}")
#                     checker: IChecker = ArtisticSlideChecker(self.llm_utils, self.selected_artistic_slide_requests, f' (Slide {slide_idx + 1})', f' (Slide {slide_idx + 1})')
#                     self.llm_access.set_checker(checker)
#                     self.__send_llm_requests_and_expand_output(slide_content["shapes"], False)
                    
#             deck_content.append(slide_content)

#         if len(self.selected_deck_requests) > 0:
#             self.content_out.add_title(1, f"Check of text content and flow for the whole deck")
#             formatted_deck_content_list: List = [ f'Slide {slide_number + 1}, {slide_content["title"]}:\n{json.dumps(slide_content["reduced_slide_text"])}' \
#                                                   for slide_number, slide_content in enumerate(deck_content) ]
#             checker: IChecker = DeckChecker(self.llm_utils, self.selected_deck_requests, f' (Deck)', f' (Deck)')
#             self.llm_access.set_checker(checker)
#             self.__send_llm_requests_and_expand_output(formatted_deck_content_list, True)

#     def __fill_tasks(self, ppt_slides: any):
#         # To get shapes in your slides
#         for slide in  ppt_slides.slides:
#             for shape in slide.shapes:
#                 if shape.has_text_frame:
#                     text_frame = shape.text_frame
#                     for paragraph in text_frame.paragraphs:
#                         current_text: str = paragraph.text
#                         if current_text is not None and self.is_paragraph(current_text): 
#                             self.worker.add_work_element(MetadataPpt(paragraph))

#     def process(self):
#         self.__fill_tasks(self.document)
#         self.worker.process_all()

