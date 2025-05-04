from abc import ABC, abstractmethod
from typing import List, Tuple
from dataclasses import dataclass
import threading
from pprint import pformat
import re

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
    
    def __init__(self, list_pointer_source_data: List, context: str, text_to_transform: str, request_type: str, logger: GenericLogger, document_style: List = None):
        self.list_pointer_source_data: List = list_pointer_source_data
        self.context = context
        self.text_to_transform: str = text_to_transform
        self.request_type = request_type
        self.logger = logger
        self.logger.log_trace(f"Add metadata of request type {request_type}, text_to_transform: {text_to_transform}")
        # Will have to be moved to MetadaWindows
        self.use_paragraph_style = False
        self.document_style: List = document_style

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



class MetadataWindows(Metadata):
    # Needs to be overriden if a different behaviour is expected
    def _get_pointer_to_text(self, pointer: any)-> any:
        return pointer

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
                        self.logger.log_trace(f"Updating cell (row_id:{row_id}, col_id: {col_id}) from {cell.text} to {md_table_list[row_id][col_id]}")
                        paragraph: any = cell
                        if hasattr(cell, "paragraphs"):
                            if len(cell.paragraphs) == 0:
                                paragraph = cell.add_paragraph()
                            else:
                                while len(paragraph.paragraphs) > 1:
                                    self._delete_paragraph(paragraph.paragraphs[-1])
                                paragraph = cell.paragraphs[0]
                            
                        self._update_paragraph(paragraph, md_table_list[row_id][col_id])
                        #cell.text = md_table_list[row_id][col_id]
                        self.logger.log_trace(f"Updated cell (row_id:{row_id}, col_id: {col_id}) is now {cell.text} ({md_table_list[row_id][col_id]})")
                    else:
                        error_message_list_table_row: str = len(md_table_list[row_id]) if row_id < len(md_table_list) else f"{row_id} is out of range (0 to {len(md_table_list)})"
                        self.logger.log_error(f"Could not update cell having initial value {cell.text} because of index out of range at coordinate (Row: {row_id}, Col: {col_id}):\n"+\
                                              f"  Doc Table size: Rows: {len(doc_table.rows)} x Cols: {len(doc_table.rows[row_id].cells)} and \n"+\
                                              f"  List Table size: Rows: {len(md_table_list)} x Cols: {error_message_list_table_row}.\n"+\
                                              f"  Skipping cell!")

        else:
            self.logger.log_error(f"No table was registered for the context: {self.get_context()}\n"+\
                                  "request:\n{self.get_text_to_transform()}\n")

    def _delete_paragraph(self, paragraph_pointer):
        p = paragraph_pointer._element
        parent = p.getparent()
        if parent is not None:
            self.logger.log_trace(f"Deleting element: {paragraph_pointer}: >{paragraph_pointer.text}<, pointer.element: {p}: >{p.text}<")
            self.logger.log_trace(f"Parent of element is: {parent}: >{parent.text}<")
            parent.remove(p)
            p._p = p._element = None
        else:
            self.logger.log_warn(f"Paragraph {paragraph_pointer}: {paragraph_pointer.text} could not be deleted.")
            paragraph_pointer.text = ""
    
    # TODO: Has to be part of refactoring
    def _add_runs(self, new_paragraph: any, runs: List, style: any = None):
        for want_bold, run_text in runs:
            run = new_paragraph.add_run()
            run.text = run_text
            self.logger.log_trace(f"Text >{run_text}< was added to paragraph, initial style: Font name: '{run.font.name}', Font size: {run.font.size}, Underlines: {run.font.underline}, Bold: {run.font.bold}, Italic: {run.font.italic}")
            if style is not None:
                self._set_paragraph_style_to_font(run, style)
                self.logger.log_trace(f"Style updated to: Font name: '{run.font.name}', Font size: {run.font.size}, Underlines: {run.font.underline}, Bold: {run.font.bold}, Italic: {run.font.italic}, want_bold: {want_bold}")
            if want_bold: 
                run.font.bold = True
                self.logger.log_trace(f"Text {run_text} was set to bold")
        self.logger.log_trace(f"_add_runs with style: new_paragraph.text =  {new_paragraph.text}")

    def _update_paragraph_in_place(self, paragraph_pointer: any, runs: List):
        if hasattr(paragraph_pointer, "style"):
            current_style: any = paragraph_pointer.style
            self._add_runs(paragraph_pointer, runs)    
            paragraph_pointer.style = current_style
        else:
            current_style: any = self._get_paragraph_style_from_font(paragraph_pointer)
            paragraph_pointer.text = ""
            if hasattr(paragraph_pointer, "_parent") and hasattr(paragraph_pointer._parent, "paragraphs"):
                for doc_idx, doc in enumerate(paragraph_pointer._parent.paragraphs):
                    doc.text = ""
                    # TODO: To be analyzed on the long term as this could make the file unreadable
                    if doc_idx > 0:
                        self._delete_paragraph(doc)
                    else:
                        self.logger.log_trace("Not deleting first element of pointer {}")

            self._add_runs(paragraph_pointer, runs, current_style)    

    def _transform_paragraph_to_runs(self, paragraph: str) -> Tuple:
        runs_boldstyle_text: List = []
        for current_run in paragraph.split('\n'):
            if len(current_run) == 0 or re.match('^[\s\n]*$', current_run):
                continue
            current_run += '\n'
            found_run: bool = True
            self.logger.log_trace(f"Checking for bold text in >{current_run}<.")
            while found_run:
                m_run = re.match(r'^(?P<before_bold>.*?)\*\*(?P<in_bold>.*?)\*\*(?P<after_bold>.*)$', current_run)
                if m_run is None:
                    found_run = False
                    runs_boldstyle_text.append((False, current_run))
                    self.logger.log_trace(f"The text >{current_run}< has no MD bold requirement.")
                else:
                    runs_boldstyle_text.append((False, m_run.group('before_bold')))
                    runs_boldstyle_text.append((True, m_run.group('in_bold')))
                    current_run = m_run.group('after_bold')
                    self.logger.log_trace(f"The text >{m_run.group('before_bold')}< will NOT be bold")
                    self.logger.log_trace(f"The text >{m_run.group('in_bold')}< will be bold")
                    self.logger.log_trace(f"The text >{m_run.group('after_bold')}< will NOT be bold")
            style, text = runs_boldstyle_text[-1]
            if not text.endswith('\n'):
                runs_boldstyle_text[-1] = (style, text + '\n')
                                 
        return runs_boldstyle_text

    def _get_paragraph_style_from_font(self, pointer: any) -> Tuple:
        self.logger.log_trace(f"Pointer: {dir(pointer)}")
        if not self.use_paragraph_style and hasattr(pointer, 'runs') and len(pointer.runs) > 0:
            pointer = pointer.runs[0]
            self.logger.log_trace(f"Using runs instead of initial pointer: {dir(pointer)}")

        return(pointer.font.name, 
               pointer.font.size,
               pointer.font.underline,
               pointer.font.bold,
               pointer.font.italic)

    def _set_paragraph_style_to_font(self, pointer: any, style: Tuple):
        pointer.font.name,      \
        pointer.font.size,      \
        pointer.font.underline, \
        pointer.font.bold,      \
        pointer.font.italic = style


    def _update_text(self, text:str) -> None:
        # Split LLM transformation per paragraph and ensure that the number of paragraph returned by LLM 
        # does not exceed the original number of paragraphs
        paragraphs = text.split("\n")
        self.logger.log_trace(f"len(paragraphs): {len(paragraphs)}, len(self.list_pointer_source_data): {len(self.list_pointer_source_data)}, paragraphs: {pformat(paragraphs)}")
        while (len(paragraphs) > 1 and len(paragraphs) > len(self.list_pointer_source_data)):
            paragraphs[-2] += "\n" + paragraphs[-1]
            paragraphs = paragraphs[:len(paragraphs) - 2]
            self.logger.log_trace(f"len(paragraphs): {len(paragraphs)}, len(self.list_pointer_source_data): {len(self.list_pointer_source_data)}, paragraphs: {pformat(paragraphs)}")
        if len(paragraphs) > len(self.list_pointer_source_data):
            self.logger.log_warn(f"len(paragraphs) ({len(paragraphs)}) > len(self.list_pointer_source_data) ({len(self.list_pointer_source_data)})")
        for index in range(min(len(paragraphs), len(self.list_pointer_source_data))):
            self.list_pointer_source_data[index].text = paragraphs[index]
        # If the number of paragraphs returned by LLM is lower than the current number of paragraphs 
        # in the original document clear the text.
        for index in range(len(paragraphs), len(self.list_pointer_source_data)):
             self.list_pointer_source_data[index].text = ""

    def _update_paragraph(self, paragraph_pointer: any, new_paragraph_text: str) -> any:
        updated_paragraph_pointer = self._get_pointer_to_text(paragraph_pointer)
        if hasattr(updated_paragraph_pointer, "text"):
            self.logger.log_trace(f"Updating paragraph from {updated_paragraph_pointer.text} to {new_paragraph_text}")
        if updated_paragraph_pointer is not None:
            runs_style_text: List = self._transform_paragraph_to_runs(new_paragraph_text)
            self._update_paragraph_in_place(updated_paragraph_pointer, runs_style_text)
        else:
            self.logger.log_warn(f"New text: {new_paragraph_text} could not be updated, pointer is {paragraph_pointer}")


class MetadataDoc(MetadataWindows):

    thread_lock_queue = threading.Lock()

    def _update_paragraph_in_place(self, paragraph_pointer: any, runs: List):
        current_style: any = paragraph_pointer.style
        self._add_runs(paragraph_pointer, runs)    
        paragraph_pointer.style = current_style

    def _add_runs(self, new_paragraph: any, runs: List):
        for want_bold, run_text in runs:
            # Skip empty lines (Will lead to more dense document)
            if not re.match(r'^\s*$', run_text):
                run_text = run_text.replace('\n', ' ')
                run = new_paragraph.add_run(run_text)
                if want_bold: 
                    run.bold = True
                    self.logger.log_trace(f"Text {run_text} was set to bold")
        self.logger.log_trace(f"_add_runs without style: new_paragraph.text =  {new_paragraph.text}")

    def __paragraph_index(self, paragraph_pointer):
        "Get the index of the paragraph in the document"
        parent_doc = paragraph_pointer._parent
        # the paragraphs elements are being generated on the fly,
        # they change all the time
        # so in order to index, we must use the elements
        for p_idx, p in enumerate(parent_doc.paragraphs):
            if p._element == paragraph_pointer._element:
                return p_idx

        self.logger.log_warn(f'Could not find paragraph {paragraph_pointer._element} (Text: {paragraph_pointer.text}) from list: {parent_doc.paragraphs} (Text: {pformat([p.text for p in parent_doc.paragraphs])})')
        return -1
        # l_elements = [p._element for p in doc.paragraphs]
        # return l_elements.index(paragraph_pointer._element)

                    
    def __insert_paragraph_after(self, paragraph_pointer: any, runs: List, style=None):
        self.logger.log_trace(f"Entering __insert_paragraph_after with {paragraph_pointer} = paragraph_pointer.text = {paragraph_pointer.text}")
        parent_doc = paragraph_pointer._parent
        self.logger.log_trace(f"__insert_paragraph_after, parent = {parent_doc}")
        i = self.__paragraph_index(paragraph_pointer) + 1 # next
        if i < len(parent_doc.paragraphs) and i > 0:
            # we find the next paragraph and we insert before:
            next_paragraph = parent_doc.paragraphs[i]
            self.logger.log_trace(f"next_paragraph = {next_paragraph}, next_paragraph.text = {next_paragraph.text}")
            new_paragraph = next_paragraph.insert_paragraph_before('', style)
        else:
            # we reached the end, so we need to create a new one:
            new_paragraph = parent_doc.add_paragraph('', style)
        self._add_runs(new_paragraph, runs)

        return new_paragraph

    def __split_paragraph(self, paragraphs: List, idx_paragraph: int, split_char: str = '.'):
        paragraph: str = paragraphs[idx_paragraph]
        first_paragraphs: List = paragraph.split(split_char)
        self.logger.log_trace(f"Heading {paragraph} index {idx_paragraph} divided in {first_paragraphs}")
        if len(first_paragraphs) > 1:
            paragraphs[idx_paragraph] = '.'.join(first_paragraphs[1:])
            paragraphs.insert(idx_paragraph, first_paragraphs[0])
            self.logger.log_trace(f"Heading reduced to {paragraphs[0]}")
            # We shoud not have a ':' in a heading
            if ':' in paragraphs[0]: 
                self.__split_paragraph(paragraphs, idx_paragraph, ':')

    def __get_style_from_style_name(self, style_required_names: List):
        # Use style normal per default
        if "normal" not in style_required_names:
            style_required_names.append("normal")
        for style_required_name in style_required_names:
            for style in self.document_style:
                if style.name.lower().startswith(style_required_name.lower()):
                    self.logger.log_trace(f"Using style {style} as found from {style_required_name}")
                    return style
            self.logger.log_trace(f"Style {style_required_name} not found in {self.document_style}")


        self.logger.log_trace(f"None of the requested styles: {style_required_names} were found in {self.document_style}")
        return None
    
    def _update_text(self, text: str) -> None:

        paragraphs: List = text.split("\n")
        # Sometimes LLM returms a very long heading that should actually be a heading followed by a paragraph
        for idx_paragraph in range(len(paragraphs)-1, -1, -1):
            paragraph: str = paragraphs[idx_paragraph]
            self.logger.log_trace(f"Checking {paragraph} index {idx_paragraph}, checking if it is a title")
            if re.search(r'^\s*#', paragraph):
                self.logger.log_trace(f"Yes {paragraph} is a title")
                self.__split_paragraph(paragraphs, idx_paragraph)
        
        self.logger.log_trace(f"Initial data: len(paragraphs) {len(paragraphs)}, {paragraphs} len(self.list_pointer_source_data) {len(self.list_pointer_source_data)}, {pformat([str(pointer) + ': ' + pointer.text for pointer in self.list_pointer_source_data], width=200)}")
        if len(paragraphs) > 0 and len(self.list_pointer_source_data) > 0:
            self.list_pointer_source_data[0].text = ""
            self.logger.log_trace(f"Checking style of existing paragraph {paragraph} style {self.list_pointer_source_data[0].style.name}")
            if(self.list_pointer_source_data[0].style.name.lower().startswith("heading ")):
                self.__split_paragraph(paragraphs, 0)

        if len(self.list_pointer_source_data) > 1:
            for paragraph_pointer in self.list_pointer_source_data[1:]:
                self._delete_paragraph(paragraph_pointer)
        if len(self.list_pointer_source_data) <= 0:
            self.logger.log_warn(f"Was expecting at least one element in array of pointer but got {len(self.list_pointer_source_data)}: {self.list_pointer_source_data}")
        self.logger.log_trace(f"This pointer will not be deleted {self.list_pointer_source_data[0]}:  {self.list_pointer_source_data[0].text}")

        self.logger.log_trace(f"After deletion of the pointers: len(paragraphs) {len(paragraphs)}, {paragraphs} len(self.list_pointer_source_data) Deleted are: {len(self.list_pointer_source_data) - 1}, {pformat([str(pointer) + ': ' + pointer.text for pointer in self.list_pointer_source_data[1:]], width=200)}")
        next_paragraph_pointer: any = self.list_pointer_source_data[0]
        next_paragraph_style = next_paragraph_pointer.style
      
        for paragraph_id, paragraph in enumerate(paragraphs):

            # We keep style of first paragraph
            if paragraph_id > 0:

                style_required_names: List = ['normal']

                match_heading = re.search(r'^\s*(?P<heading_deepness>[#]+)[^#]+', paragraph)
                if match_heading:
                    heading_class: int = len(match_heading.group('heading_deepness'))
                    if heading_class > 0:
                        style_required_names = [f'heading {heading_class}']

                elif re.search(r'^\s*[\*\-]([^\*]+|$)', paragraph):
                    style_required_names = ['bullet ', 'list ']

                new_style: any = self.__get_style_from_style_name(style_required_names)
                if new_style is not None: 
                    next_paragraph_style = new_style

                self.logger.log_trace(f"The paragraph >{paragraph}< has style >{next_paragraph_style}< as defined by >{style_required_names}<")
            paragraph = re.sub(r'^\s*[#]+\s*', '', paragraph)
            self.logger.log_trace(f"The paragraph >{paragraph}< was cleaned of heading marking if any were present")
            
            runs_style_text: List = self._transform_paragraph_to_runs(paragraph)

            if paragraph_id > 0:
                next_paragraph_pointer = self.__insert_paragraph_after(next_paragraph_pointer, runs_style_text, next_paragraph_style)
            else:
                self._update_paragraph_in_place(next_paragraph_pointer, runs_style_text)

    def update_llm_response_in_document(self, text: str, request_tyoe: str) -> None: 
        self.thread_lock_queue.acquire()
        self.logger.log_trace(f"Updating document with request type: {request_tyoe} and text: {text}")
        if request_tyoe != LLMUtils.TABLE_REQUEST:
            self._update_text(text)
        else:
            self._update_table(text)
        self.thread_lock_queue.release() 

class MetadataXls(MetadataWindows):
    thread_lock_queue = threading.Lock()

    def get_text_to_transform(self) -> str:
        return str(self.list_pointer_source_data.value)
    def update_llm_response_in_document(self, text: str, request_tyoe: str) -> None: 
        self.thread_lock_queue.acquire()
        self.list_pointer_source_data.value = text
        self.thread_lock_queue.release() 

class MetadataPpt(MetadataWindows):
    thread_lock_queue = threading.Lock()


    def update_llm_response_in_document(self, text: str, request_tyoe: str) -> None: 
        self.thread_lock_queue.acquire()
        self.logger.log_trace(f"Updating document with request type: {request_tyoe} and text: {text}")
        if request_tyoe != LLMUtils.TABLE_REQUEST:
            self._update_text(text)
        else:
            self._update_table(text)
        self.thread_lock_queue.release() 

    def _get_pointer_to_text(self, pointer: any)-> any:
        self.logger.log_trace(f"_get_pointer_to_text, pointer has attributes {format(dir(pointer))}")
        new_pointer: any = None
        if hasattr(pointer, "title"): 
            new_pointer =  pointer.title
            self.logger.log_trace(f"Found title as pointer with attributes {format(dir(new_pointer))}")
        if hasattr(pointer, "text_frame"): 
            self.logger.log_trace(f"_get_pointer_to_text, pointer.text_frame has attributes {format(dir(pointer.text_frame))}")
            pointer = pointer.text_frame
        if hasattr(pointer, "paragraphs") and len(pointer.paragraphs) > 0:
            new_pointer = pointer.paragraphs[0]
            self.logger.log_trace(f"Found paragraph as pointer with attributes: {format(dir(new_pointer))}")

        return new_pointer
                
    def _update_text(self, text:str) -> None:
        # Split LLM transformation per paragraph and ensure that the number of paragraph returned by LLM 
        # does not exceed the original number of paragraphs
        paragraphs = text.split("\n")
        self.logger.log_trace(f"len(paragraphs): {len(paragraphs)}, len(self.list_pointer_source_data): {len(self.list_pointer_source_data)}, paragraphs: {pformat(paragraphs)}")
        while (len(paragraphs) > 1 and len(paragraphs) > len(self.list_pointer_source_data)):
            paragraphs[-2] += "\n" + paragraphs[-1]
            paragraphs = paragraphs[:-1]
            self.logger.log_trace(f"len(paragraphs): {len(paragraphs)}, len(self.list_pointer_source_data): {len(self.list_pointer_source_data)}, paragraphs: {pformat(paragraphs)}")
        self.logger.log_trace(f"Processing {len(paragraphs)} paragraphs adapted to number of pointers: {len(self.list_pointer_source_data)}")
        if len(paragraphs) > len(self.list_pointer_source_data):
            self.logger.log_warn(f"len(paragraphs) ({len(paragraphs)}) > len(self.list_pointer_source_data) ({len(self.list_pointer_source_data)})")
        # If the number of paragraphs returned by LLM is lower than the current number of paragraphs 
        # in the original document delete the remaining paragraphs.
        for index in range(len(paragraphs), len(self.list_pointer_source_data)):
             self.logger.log_trace(f"Deleting paragraph index: {index}, initial text: {self.list_pointer_source_data[index].text}")
             self._delete_paragraph(self.list_pointer_source_data[index])
        for index in range(len(paragraphs)):
            dbg_paragraph: str = paragraphs[index].replace('\n', '\\n')
            self.logger.log_trace(f"Processing paragraph index: {index}, initial text: {self.list_pointer_source_data[index].text}, new text: {dbg_paragraph}")
            self._update_paragraph(self.list_pointer_source_data[index], paragraphs[index])

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
    
    @abstractmethod
    def get_all_queue_content(self) -> List[Metadata]:
        """
        """
    
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

    def get_all_queue_content(self) -> List[Metadata]:
        return self.queue.copy()

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

    
    def get_all_queue_content(self) -> List[Metadata]:
        self.thread_lock_queue.acquire()
        queue_copy = self.queue.copy()
        self.thread_lock_queue.release()
        return queue_copy

