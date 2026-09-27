from models.Station import Station
from models.Event import Event


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
        # todavía no haya sido procesado.
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