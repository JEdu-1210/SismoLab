from io import TextIOWrapper
from pathlib import Path
import json
from typing import Any
from src.models.Returnings import BaseReturn, DataAndMsgReturn


class FilesUtils:
    @staticmethod
    def file_exists(filename: str) -> bool:
        return Path(filename).is_file()
    
    @staticmethod
    def open_file(filename: str, mode: str = 'r', encoding: str = 'utf-8') -> TextIOWrapper:
        file = None
        if mode == 'r' and not FilesUtils.file_exists(filename):
            # Requires that the file exists, but don't exists...
            return None
        
        # When mode is 'w' creates file automatically
        file = open(filename, mode, encoding=encoding)
        return file
    
    @staticmethod
    def read_file(filename: str) -> DataAndMsgReturn:
        __response = DataAndMsgReturn()
        file = FilesUtils.open_file(filename)

        if file:
            __response.data = file.read()
            file.close()
        
        return __response
    
    @staticmethod
    def get_filename_from_path(path: str) -> str:
        filename:str = Path(path).name
        return filename

    @staticmethod
    def read_json(filename: str) -> DataAndMsgReturn:
        __response = DataAndMsgReturn()
        readed: DataAndMsgReturn = FilesUtils.read_file(filename)

        if readed.data:
            try:
                __response.data = json.loads(readed.data)
            except Exception as e:
                __response.error = e
        else:
            __response.msg = f"The file '{FilesUtils.get_filename_from_path(filename)}' don't exists!"

        return __response
    
    @staticmethod
    def write_file(filename: str, data: str, mode: str = 'w') -> BaseReturn:
        __response = BaseReturn()

        if mode in ['w', 'a']:
            try:
                with FilesUtils.open_file(filename, mode) as file:
                    file.write(data)
            except Exception as e:
                __response.ok = False
                __response.error = e.__str__()
        else:
            __response.ok = False
            __response.error = "The mode isn't valid!"

        return __response

    @staticmethod
    def write_json(filename, data: dict) -> BaseReturn:
        __response: BaseReturn = BaseReturn()
        file = FilesUtils.open_file(filename, 'w')

        if file:
            try:
                json.dump(data, file, indent=2, sort_keys=True, ensure_ascii=False)
            except Exception as e:
                __response.ok = False
                __response.error = e.__str__()
        else:
            __response.ok = False
            __response.error = 'Something happend trying write the JSON file'

        return __response