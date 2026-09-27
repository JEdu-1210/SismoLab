from models.Station import Station
from models.Zone import Zone


class Scenario:

    def __init__(
        self,
        simulation_clock,
        w_hours=48,
        r_km=40,
        access_limit=3,
        archive_age_hours=72,
        stress_mode=False
    ):

        self.simulation_clock = simulation_clock

        self.w_hours = float(w_hours)
        self.r_km = float(r_km)

        self.access_limit = int(access_limit)
        self.archive_age_hours = float(archive_age_hours)

        self.stress_mode = stress_mode

        # Colecciones pertenecientes al escenario.
        self.zones = []
        self.stations = []


    # Agrega una zona al escenario.
    #
    # Recibe:
    # - un objeto Zone.
    #
    # Retorna:
    # - True si se agregó correctamente.
    def add_zone(
        self,
        zone: Zone
    ):

        self.zones.append(
            zone
        )

        return True


    # Agrega una estación al escenario.
    #
    # Recibe:
    # - un objeto Station.
    #
    # Retorna:
    # - True si se agregó correctamente.
    def add_station(
        self,
        station: Station
    ):

        self.stations.append(
            station
        )

        return True


    # Retorna todas las zonas del escenario.
    def get_zones(self):

        return list(
            self.zones
        )


    # Retorna todas las estaciones del escenario.
    def get_stations(self):

        return list(
            self.stations
        )


    # Cambia el reloj de simulación.
    def set_simulation_clock(
        self,
        new_date_time
    ):

        self.simulation_clock = new_date_time


    # Retorna el reloj actual de simulación.
    def get_simulation_clock(self):

        return self.simulation_clock


    # Activa o desactiva el modo estrés.
    def set_stress_mode(
        self,
        stress_mode
    ):

        self.stress_mode = stress_mode


    # Retorna True si el escenario está en modo estrés.
    def is_stress_mode(self):

        return self.stress_mode