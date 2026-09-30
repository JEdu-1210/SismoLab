from typing import Any

class BaseReturn:
    def __init__(self, ok: bool = True, error: Any | None = None):
        self.ok = ok
        self.error = error

    def __str__(self):
        return f'OK: {self.ok}\nError: {self.error}'
    
    def to_dict(self):
        return{
            "ok": self.ok,
            "error": self.error
        }

class DataAndMsgReturn(BaseReturn):
    def __init__(self, ok: bool = True, msg: str = '', data: dict | None = None, error: Any | None = None):
        super().__init__(ok, error)
        self.msg = msg
        self.data = data

    def __str__(self):
        return f'{super().__str__()}\nMessage: {self.msg}\nData: {self.data}\nError: {self.error}'
    
    def to_dict(self):
        return{**super().to_dict(),
            "msg": self.msg,
            "data": self.data if self.data else {},
        }