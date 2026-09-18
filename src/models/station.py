

from dataclasses import dataclass


@dataclass(frozen=True)
class Station:

    name:str
    x: float
    y: float


    def __str__(self)->str:

        return f"Station: ({self.name}, Coord:({self.x},{self.y}))"
