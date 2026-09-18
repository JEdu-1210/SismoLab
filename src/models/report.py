

from dataclasses import dataclass
from datetime import datetime

from models.evento import Evento
from models.station import Station


@dataclass()
class Report:
    identifier: int
    revision: int
    station: str
    magnitude: float
    depth: float
    x: float
    y: float
    date_time : datetime

    def show_report(self)-> str:

        return(f"Report(Station: {self.station} | Rev: {self.revision} | "
               f"Event SIS-{self.identifier:06d} | Mag: {self.magnitude}"
               f"Depth: {self.depth}km | Coord: ({self.x},{self.y}) | "
               f"Date: {self.date_time.strftime('%Y-%m-%dT%H:%M:%SZ')})")
        
        

