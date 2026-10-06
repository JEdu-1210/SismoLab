from datetime import datetime

from src.models.Station import Station
from src.models.Zone import Zone
from math import isfinite

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
        if (
            not isfinite(self.w_hours)
            or self.w_hours <= 0
        ):
            raise ValueError(
                "W must be positive"
            )

        if (
            not isfinite(self.r_km)
            or self.r_km <= 0
        ):
            raise ValueError(
                "R must be positive"
            )

        if (
            isinstance(access_limit, bool)
            or
            not isinstance(access_limit, int)
            or
            access_limit < 0
        ):

            raise ValueError(
                "Access limit must be "
                "a non-negative integer"
            )


        self.access_limit = access_limit


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

        # Diccionario auxiliar para localizar eventos
        # directamente mediante su identificador.
        #
        # Conserva eventos activos, archivados
        # y eliminados.
        self._events_by_id = {}

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

    # Busca una estación utilizando su nombre.
    def get_station_by_name(
        self,
        station_name
    ):

        for station in self._stations:

            if station.name == station_name:
                return station

        return None

    # Busca un evento mediante su identificador.
    #
    # Puede retornar un evento activo,
    # archivado o eliminado.
    def get_event_by_id(
        self,
        identifier
    ):

        return self._events_by_id.get(
            int(identifier)
        )


    # Comprueba si un identificador
    # ya fue registrado alguna vez.
    def has_event_id(
        self,
        identifier
    ):

        return (
            int(identifier)
            in
            self._events_by_id
        )


    # Registra un Event dentro del escenario.
    #
    # Un identificador nunca puede
    # registrarse dos veces.
    def register_event(
        self,
        event
    ):

        if event.identifier in self._events_by_id:
            return False

        self._events_by_id[
            event.identifier
        ] = event

        return True


    # Retorna una copia del diccionario
    # de eventos registrados.
    def get_events_by_id(self):

        return dict(
            self._events_by_id
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

    # Retorna el limite de antiguedad utilizado para archivar ramas.
    def get_archive_age_hours(self):

        return self.archive_age_hours


    # Cambia T.
    # Debe ser un valor positivo.
    def set_archive_age_hours(
        self,
        hours
    ):

        try:
            hours = float(hours)

        except (TypeError, ValueError):
            return False


        if not isfinite(hours) or hours <= 0:
            return False

        self.archive_age_hours = hours

        return True


    # seccion de parametros del escenario, W y R, que son utilizados para determinar si 
    # un evento es relevante o no, y si un evento es relevante o no depende 
    # de la distancia y el tiempo transcurrido desde el evento.
    # Retorna W en horas.
    def get_w_hours(self):

        return self.w_hours


    # Cambia W.
    # Debe ser un número positivo y finito.
    def set_w_hours(
        self,
        hours
    ):

        try:
            hours = float(hours)

        except (TypeError, ValueError):
            return False

        if not isfinite(hours) or hours <= 0:
            return False

        self.w_hours = hours
        return True


    # Retorna R en kilómetros.
    def get_r_km(self):

        return self.r_km


    # Cambia R.
    # Debe ser un número positivo y finito.
    def set_r_km(
        self,
        km
    ):

        try:
            km = float(km)

        except (TypeError, ValueError):
            return False

        if not isfinite(km) or km <= 0:
            return False

        self.r_km = km
        return True

    # ACCESS LIMIT
    # Retorna el límite L.
    def get_access_limit(self):

        return self.access_limit

    # Cambia el límite L.
    # Debe ser un entero no negativo.
    def set_access_limit(
        self,
        access_limit
    ):

        if (
            isinstance(access_limit, bool)
            or
            not isinstance(access_limit, int)
            or
            access_limit < 0
        ):

            return False


        self.access_limit = access_limit

        return True
