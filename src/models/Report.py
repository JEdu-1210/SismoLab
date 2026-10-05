from src.models.Event import Event
from src.models.Station import Station

class Report:

    def __init__(
        self,
        identifier,
        revision,
        station: Station,
        magnitude,
        depth,
        x,
        y,
        date_time,
        event: Event = None
    ):

        self.identifier = int(identifier)
        self.revision = int(revision)

        self.station = station

        self.magnitude = float(magnitude)
        self.depth = float(depth)

        self.x = float(x)
        self.y = float(y)

        self.date_time = date_time

        # Puede ser None mientras el reporte
        # todavÃ­a no haya sido procesado.
        self.event = event

        self.decision = None


    def show_report(self):

        return (
            f"Report("
            f"Station: {self.station.name} | "
            f"Revision: {self.revision} | "
            f"Event: SIS-{self.identifier:06d} | "
            f"Magnitude: {self.magnitude} | "
            f"Depth: {self.depth} km | "
            f"Coordinates: ({self.x}, {self.y}) | "
            f"Date: {self.date_time}"
            f")"
        )
    def to_dict(self) -> dict:
        return {
            "identifier": self.identifier,
            "revision": self.revision,
            # Se convierte la estaciÃ³n a diccionario
            "station": self.station.to_dict() if hasattr(self.station, "to_dict") else self.station,
            "magnitude": self.magnitude,
            "depth": self.depth,
            "x": self.x,
            "y": self.y,
            "date_time": self.date_time.isoformat() if hasattr(self.date_time, "isoformat") else str(self.date_time),
            # Se incluyen el evento asociado y la decisiÃ³n tomada
            "event": self.event.to_dict() if self.event and hasattr(self.event, "to_dict") else None,
            "decision": self.decision
        }
