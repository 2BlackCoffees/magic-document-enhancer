from typing import Dict, List
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pprint import pprint, pformat
from pathlib import Path
class PPTReader:

    @staticmethod  
    def __check_recursively_for_text(shape, json_shape):
        for cur_shape in shape.shapes:
            if cur_shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                PPTReader.__check_recursively_for_text(cur_shape, json_shape)
            else:
                if hasattr(cur_shape, "text"):
                    json_shape["text"].append(cur_shape.text)
                    json_shape["pointers"].append(cur_shape)
        
        return  json_shape
    
    @staticmethod  
    def _get_shape_infos(shape: Dict, type: MSO_SHAPE_TYPE) -> Dict:

        if hasattr(shape, 'text_frame'):
            return  {
                    'y': shape.top, 'x': shape.left, 
                    "text": [str(shape.text_frame.text)],
                    "pointers": [shape.text_frame],
                    "is_title": "False",
                    "type": str(type)
            }

        return None
    
    @staticmethod  
    def _get_shape_group_infos(shape: Dict, type: MSO_SHAPE_TYPE) -> Dict:
        text: List = []
        pointers: List = []
        if hasattr(shape, 'text_frame'):
            text = [str(shape.text_frame.text)]
            pointers = [shape.text_frame]

        return  {
                'y': shape.top, 'x': shape.left, 
                "text": text,
                "pointers": pointers,
                "is_title": "False",
                "type": str(type)
        }

        return None
    
    @staticmethod  
    def _get_title_infos(shape: Dict, type: MSO_SHAPE_TYPE) -> Dict:

        if hasattr(shape, 'text'):
            return  {
                    'y': shape.top, 'x': shape.left, 
                    "text": [str(shape.text)],
                    "pointers": [shape],
                    "is_title": "True",
                    "type": str(type)
            }

        return None

    @staticmethod  
    def _get_shape_table_infos(shape: Dict, pointer_list:List, type: MSO_SHAPE_TYPE) -> Dict:

        return  {
                'y': shape.top, 'x': shape.left, 
                "text": [text_frame.text for text_frame in pointer_list],
                "pointers": pointer_list,
                "is_title": "False",
                "type": str(type)
        }

    @staticmethod  
    def __encapsulate_shape(slide_number: int, json_shape: Dict, raw_text: str = None) -> Dict:
        if json_shape is not None:
            new_json = json_shape.copy()
            return {
                'y': json_shape['y'], 
                'json': new_json,
                'raw_text': " ".join(new_json["text"]) if raw_text is None else raw_text,
                'slide_number': slide_number
            }
        else:
            return None

    @staticmethod  
    def get_text_box_info(slide_number: int, shape: Dict) -> Dict:
        json_shape: Dict = PPTReader._get_shape_infos(shape, MSO_SHAPE_TYPE.TEXT_BOX)
        return PPTReader.__encapsulate_shape(slide_number, json_shape)
    
    @staticmethod  
    def get_group_info(slide_number: int, shape: Dict) -> Dict:
        json_shape: Dict = PPTReader._get_shape_group_infos(shape, MSO_SHAPE_TYPE.GROUP)
        json_shape = PPTReader.__check_recursively_for_text(shape, json_shape)
        return PPTReader.__encapsulate_shape(slide_number, json_shape)
    
    @staticmethod  
    def get_table_info(slide_number: int, shape: Dict, table_str: str, pointer_list: List) -> Dict:
        json_shape: Dict = PPTReader._get_shape_table_infos(shape, pointer_list, MSO_SHAPE_TYPE.TABLE)
        return PPTReader.__encapsulate_shape(slide_number, json_shape, table_str)

    @staticmethod  
    def get_shape_type_info(slide_number: int, shape: Dict) -> Dict:
        json_shape: Dict = PPTReader._get_shape_infos(shape, MSO_SHAPE_TYPE.MIXED)
        return PPTReader.__encapsulate_shape(slide_number, json_shape)

    @staticmethod  
    def create_title(slide_number: int, shape: Dict) -> Dict:
        json_shape: Dict = PPTReader._get_title_infos(shape, MSO_SHAPE_TYPE.TEXT_BOX)
        return PPTReader.__encapsulate_shape(slide_number, json_shape)

    @staticmethod  
    def get_sorted_shapes_by_pos_y(shapes: List) -> List:
        return sorted(shapes, key = lambda shape_dict: shape_dict['y'])

