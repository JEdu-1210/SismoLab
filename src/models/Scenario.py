from datetime import datetime

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

        # Validamos primero el reloj.
        if not self._is_valid_clock(
            simulation_clock
        ):

            raise ValueError(
                "Invalid simulation clock"
            )


        self._simulation_clock = (
            simulation_clock
        )


        # Estos parámetros serán
        # trabajados en sus respectivos
        # puntos del proyecto.
        self.w_hours = float(
            w_hours
        )

        self.r_km = float(
            r_km
        )

        self.access_limit = int(
            access_limit
        )

        self.archive_age_hours = float(
            archive_age_hours
        )

        self.stress_mode = (
            stress_mode
        )


        # Las zonas y estaciones
        # forman parte del escenario.
        self._zones = []
        self._stations = []


    # ==================================================
    # ZONES
    # ==================================================

    # Agrega una zona solamente si
    # no se superpone con otra existente.
    def add_zone(
        self,
        zone: Zone
    ):

        if not isinstance(
            zone,
            Zone
        ):

            print(
                "Error: zone must be "
                "a Zone object"
            )

            return False


        # Como usamos el nombre para
        # identificar visualmente las zonas,
        # no permitiremos nombres repetidos.
        for current_zone in (
            self._zones
        ):

            if (
                current_zone.name
                ==
                zone.name
            ):

                print(
                    f"Error: zone "
                    f"{zone.name} "
                    f"already exists"
                )

                return False


        # Una zona puede compartir
        # borde o esquina con otra,
        # pero no compartir área interior.
        # recorre todas las zonas existentes y verifica si la nueva zona se superpone con alguna de ellas.
        #  Si encuentra una superposición, imprime un mensaje de error y retorna False.
        #  Si no hay superposición, agrega la nueva zona a la lista de zonas del escenario y retorna True.
        for current_zone in (
            self._zones
        ):

            if zone.overlaps_with(
                current_zone
            ):

                print(
                    f"Error: zone "
                    f"{zone.name} "
                    f"overlaps with "
                    f"{current_zone.name}"
                )

                return False


        self._zones.append(
            zone
        )

        return True


    # Retorna una copia para evitar
    # modificar directamente la lista
    # interna del escenario.
    def get_zones(self):

        return list(
            self._zones
        )


    # Retorna todas las zonas que
    # contienen unas coordenadas.
    #
    # Normalmente será una.
    #
    # Puede haber más de una cuando
    # el punto está sobre un borde
    # compartido.
    def get_zones_containing_point(
        self,
        x,
        y
    ):

        x = float(x)
        y = float(y)


        matching_zones = []


        for zone in self._zones:

            if zone.contains_point(
                x,
                y
            ):

                matching_zones.append(
                    zone
                )


        return matching_zones


    # Determina si unas coordenadas
    # pertenecen a una zona poblada.
    #
    # Si el punto pertenece a más
    # de una zona por estar en un borde,
    # basta con que una sea poblada.
    def is_point_in_populated_zone(
        self,
        x,
        y
    ):

        zones = (
            self
            .get_zones_containing_point(
                x,
                y
            )
        )

        # si la lista de zonas que tienen un punto dentro existe, recorremos zoona por zona
        # para ver si de esas que tiene el punto dentro es poblada o no, si si, el 
        # epicentro del terremoto esta en una zona poblada, si no, no lo esta.
        for zone in zones:

            if zone.is_populated:

                return True


        return False


    # ==================================================
    # STATIONS
    # ==================================================

    def add_station(
        self,
        station: Station
    ):

        if not isinstance(
            station,
            Station
        ):

            print(
                "Error: station must be "
                "a Station object"
            )

            return False


        # Los nombres de estación serán
        # únicos porque los utilizaremos
        # para identificar la procedencia
        # de los reportes.
        for current_station in (
            self._stations
        ):

            if (
                current_station.name
                ==
                station.name
            ):

                print(
                    f"Error: station "
                    f"{station.name} "
                    f"already exists"
                )

                return False


        self._stations.append(
            station
        )

        return True


    def get_stations(self):

        return list(
            self._stations
        )


    # SIMULATION CLOCK
    # Comprueba que el reloj sea
    # un datetime válido en UTC
    # y con precisión de segundos.
    def _is_valid_clock(
        self,
        date_time
    ):

        if not isinstance(
            date_time,
            datetime
        ):

            print(
                "Error: simulation clock "
                "must be a datetime object"
            )

            return False


        if (
            date_time.microsecond
            != 0
        ):

            print(
                "Error: simulation clock "
                "must have second precision"
            )

            return False


        if (
            date_time.tzinfo is None
            or
            date_time.utcoffset()
            is None
        ):

            print(
                "Error: simulation clock "
                "must use UTC timezone"
            )

            return False


        if (
            date_time
            .utcoffset()
            .total_seconds()
            != 0
        ):

            print(
                "Error: simulation clock "
                "must be in UTC"
            )

            return False


        return True


    # El reloj solamente puede avanzar.
    #
    # No puede mantenerse igual
    # ni retroceder.
    def set_simulation_clock(
        self,
        new_date_time
    ):

        if not self._is_valid_clock(
            new_date_time
        ):

            return False


        if (
            new_date_time
            <=
            self._simulation_clock
        ):

            print(
                "Error: simulation clock "
                "can only move forward"
            )

            return False


        self._simulation_clock = (
            new_date_time
        )

        return True


    def get_simulation_clock(self):

        return (
            self._simulation_clock
        )


    # STRESS MODE

    def set_stress_mode(
        self,
        stress_mode
    ):

        self.stress_mode = (
            stress_mode
        )


    def is_stress_mode(self):

        return (
            self.stress_mode
        )