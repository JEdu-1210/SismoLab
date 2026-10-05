from io import TextIOWrapper
from pathlib import Path
import json
from typing import Any
from src.models.Returnings import BaseReturn, DataAndMsgReturn


class Files:
    @staticmethod
    def file_exists(filename: str) -> bool:
        return Path(filename).is_file()

    @staticmethod
    def open_file(filename: str, mode: str = 'r', encoding: str = 'utf-8') -> TextIOWrapper:
        if mode == 'r' and not Files.file_exists(filename):
            return None
        return open(filename, mode, encoding=encoding)

    @staticmethod
    def read_file(filename: str) -> DataAndMsgReturn:
        __response = DataAndMsgReturn()
        file = Files.open_file(filename)

        if file:
            __response.data = file.read()
            file.close()

        return __response

    @staticmethod
    def get_filename_from_path(path: str) -> str:
        return Path(path).name

    @staticmethod
    def read_json(filename: str) -> DataAndMsgReturn:
        __response = DataAndMsgReturn()
        readed: DataAndMsgReturn = Files.read_file(filename)

        if readed.data:
            try:
                __response.data = json.loads(readed.data)
            except Exception as e:
                __response.error = str(e)
        else:
            __response.msg = f"The file '{Files.get_filename_from_path(filename)}' doesn't exist!"

        return __response

    @staticmethod
    def write_file(filename: str, data: str, mode: str = 'w') -> BaseReturn:
        __response = BaseReturn()

        if mode in ['w', 'a']:
            try:
                with Files.open_file(filename, mode) as file:
                    file.write(data)
            except Exception as e:
                __response.ok = False
                __response.error = str(e)
        else:
            __response.ok = False
            __response.error = "The mode isn't valid!"

        return __response

    @staticmethod
    def write_json(filename: str, data: dict) -> BaseReturn:
        __response: BaseReturn = BaseReturn()
        file = Files.open_file(filename, 'w')

        if file:
            try:
                json.dump(data, file, indent=2, sort_keys=True, ensure_ascii=False)
                file.close()
            except Exception as e:
                __response.ok = False
                __response.error = str(e)
        else:
            __response.ok = False
            __response.error = 'Something happened trying to write the JSON file'

        return __response


# Alias de seguridad para que funcione con ambos nombres (Files y FilesUtils)
FilesUtils = Files
