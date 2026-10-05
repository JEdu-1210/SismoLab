from datetime import datetime
from math import isfinite

from src.models.Status import (
    AttentionStatus,
    CatalogStatus
)


class Event:

    def __init__(
        self,
        identifier,
        magnitude,
        depth,
        x,
        y,
        date_time,
        revision,
        priority,
        is_populated_zone
    ):

        self.identifier = int(identifier)

        self.magnitude = float(magnitude)
        self.depth = float(depth)

        self.x = float(x)
        self.y = float(y)

        self.date_time = date_time

        self.revision = int(revision)

        self.priority = int(priority)

        self.is_populated_zone = is_populated_zone

        # Todo evento nuevo inicia pendiente.
        self.attention_status = (
            AttentionStatus.PENDING
        )

        # Todo evento nuevo inicia activo.
        self.catalog_status = (
            CatalogStatus.ACTIVE
        )

        # Guarda las estaciones cuyos reportes
        # han sido aceptados para este evento.
        #
        # Se usa set para evitar estaciones repetidas.
        self.accepted_stations = set()


    # Retorna la clave utilizada por el AVL y el BST.
    #
    # K = (
    #     prioridad,
    #     magnitud,
    #     identificador
    # )
    def get_key(self):

        return (
            self.priority,
            self.magnitude,
            self.identifier
        )


    # Agrega una estaciÃ³n al conjunto de estaciones
    # que han enviado reportes aceptados.
    def add_accepted_station(
        self,
        station_name
    ):

        if not isinstance(
            station_name,
            str
        ):
            return False

        if station_name.strip() == "":
            return False

        self.accepted_stations.add(
            station_name
        )

        return True


    # Marca el evento como revisado.
    def mark_as_reviewed(self):

        self.attention_status = (
            AttentionStatus.REVIEWED
        )


    # Devuelve el evento al estado pendiente.
    #
    # Esto se utilizarÃ¡ cuando una correcciÃ³n
    # sea aceptada.
    def mark_as_pending(self):

        self.attention_status = (
            AttentionStatus.PENDING
        )


    # Marca el evento como archivado.
    def archive(self):

        self.catalog_status = (
            CatalogStatus.ARCHIVED
        )


    # Marca el evento como activo.
    #
    # SerÃ¡ Ãºtil cuando un evento archivado
    # sea reactivado.
    def activate(self):

        self.catalog_status = (
            CatalogStatus.ACTIVE
        )


    # Marca el evento como eliminado.
    #
    # El objeto Event puede seguir existiendo,
    # aunque ya no se encuentre dentro del AVL.
    def delete(self):

        self.catalog_status = (
            CatalogStatus.DELETED
        )


    # Verifica que un nÃºmero tenga
    # como mÃ¡ximo un decimal.
    def _has_max_one_decimal(
        self,
        value
    ):

        return (
            value
            ==
            round(
                value,
                1
            )
        )


    # Valida Ãºnicamente reglas que dependen
    # de los atributos propios del evento.
    #
    # Las reglas que necesitan informaciÃ³n
    # del escenario o de otras estructuras
    # se validarÃ¡n desde negocio.
    def validateAttributes(self):

        # Identificador:
        # debe estar entre 1 y 999999.
        if (
            self.identifier < 1
            or
            self.identifier > 999999
        ):

            print(
                f"Error: identifier "
                f"{self.identifier} "
                f"is out of range "
                f"[1, 999999]"
            )

            return False


        # Magnitud:
        # debe ser un nÃºmero finito.
        if not isfinite(
            self.magnitude
        ):

            print(
                "Error: magnitude "
                "must be a finite number"
            )

            return False


        # Magnitud:
        # rango permitido [-2.0, 10.0].
        if (
            self.magnitude < -2.0
            or
            self.magnitude > 10.0
        ):

            print(
                f"Error: magnitude "
                f"{self.magnitude} "
                f"is out of range "
                f"[-2.0, 10.0]"
            )

            return False


        # Magnitud:
        # mÃ¡ximo un decimal.
        if not self._has_max_one_decimal(
            self.magnitude
        ):

            print(
                "Error: magnitude can have "
                "at most one decimal"
            )

            return False


        # Profundidad del hipocentro:
        # debe ser un nÃºmero finito.
        if not isfinite(
            self.depth
        ):

            print(
                "Error: depth "
                "must be a finite number"
            )

            return False


        # Profundidad:
        # rango permitido [0.0, 700.0].
        if (
            self.depth < 0.0
            or
            self.depth > 700.0
        ):

            print(
                f"Error: depth "
                f"{self.depth} "
                f"is out of range "
                f"[0.0, 700.0]"
            )

            return False


        # Profundidad:
        # mÃ¡ximo un decimal.
        if not self._has_max_one_decimal(
            self.depth
        ):

            print(
                "Error: depth can have "
                "at most one decimal"
            )

            return False


        # Coordenada X:
        # debe ser un nÃºmero finito.
        if not isfinite(
            self.x
        ):

            print(
                "Error: x "
                "must be a finite number"
            )

            return False


        # Coordenada X:
        # rango permitido [0.0, 1000.0].
        if (
            self.x < 0.0
            or
            self.x > 1000.0
        ):

            print(
                f"Error: x "
                f"{self.x} "
                f"is out of range "
                f"[0.0, 1000.0]"
            )

            return False


        # Coordenada X:
        # mÃ¡ximo un decimal.
        if not self._has_max_one_decimal(
            self.x
        ):

            print(
                "Error: x can have "
                "at most one decimal"
            )

            return False


        # Coordenada Y:
        # debe ser un nÃºmero finito.
        if not isfinite(
            self.y
        ):

            print(
                "Error: y "
                "must be a finite number"
            )

            return False


        # Coordenada Y:
        # rango permitido [0.0, 1000.0].
        if (
            self.y < 0.0
            or
            self.y > 1000.0
        ):

            print(
                f"Error: y "
                f"{self.y} "
                f"is out of range "
                f"[0.0, 1000.0]"
            )

            return False


        # Coordenada Y:
        # mÃ¡ximo un decimal.
        if not self._has_max_one_decimal(
            self.y
        ):

            print(
                "Error: y can have "
                "at most one decimal"
            )

            return False


        # La fecha debe ser realmente
        # un objeto datetime.
        if not isinstance(
            self.date_time,
            datetime
        ):

            print(
                f"Error: date_time "
                f"{self.date_time} "
                f"is not a valid "
                f"datetime object"
            )

            return False


        # El proyecto trabaja con precisiÃ³n
        # de segundos.
        #
        # Por eso no se permiten microsegundos.
        if (
            self.date_time.microsecond
            != 0
        ):

            print(
                "Error: date_time "
                "must have second precision"
            )

            return False


        # La fecha debe contener
        # informaciÃ³n de zona horaria.
        if (
            self.date_time.tzinfo is None
            or
            self.date_time.utcoffset() is None
        ):

            print(
                "Error: date_time "
                "must use UTC timezone"
            )

            return False


        # UTC debe tener desplazamiento 0.
        if (
            self.date_time
            .utcoffset()
            .total_seconds()
            != 0
        ):

            print(
                "Error: date_time "
                "must be in UTC"
            )

            return False


        # La revisiÃ³n debe ser
        # un entero positivo.
        if self.revision <= 0:

            print(
                f"Error: revision "
                f"{self.revision} "
                f"must be positive"
            )

            return False


        # La prioridad vÃ¡lida dentro
        # del sistema solo puede ser:
        #
        # 1 = Baja
        # 2 = Media
        # 3 = Alta
        #
        # Event NO calcula la prioridad.
        # Solamente verifica que el valor
        # recibido sea vÃ¡lido.
        if self.priority not in (
            1,
            2,
            3
        ):

            print(
                f"Error: priority "
                f"{self.priority} "
                f"must be 1, 2 or 3"
            )

            return False


        # La pertenencia a zona poblada
        # debe ser un valor booleano.
        if not isinstance(
            self.is_populated_zone,
            bool
        ):

            print(
                "Error: is_populated_zone "
                "must be True or False"
            )

            return False


        # El estado de atenciÃ³n debe ser
        # uno de los definidos en Status.py.
        if not isinstance(
            self.attention_status,
            AttentionStatus
        ):

            print(
                "Error: invalid "
                "attention status"
            )

            return False


        # El estado del catÃ¡logo debe ser
        # uno de los definidos en Status.py.
        if not isinstance(
            self.catalog_status,
            CatalogStatus
        ):

            print(
                "Error: invalid "
                "catalog status"
            )

            return False


        # Las estaciones aceptadas
        # deben conservarse en un set.
        if not isinstance(
            self.accepted_stations,
            set
        ):

            print(
                "Error: accepted_stations "
                "must be a set"
            )

            return False


        # Cada estaciÃ³n aceptada debe
        # estar representada por su nombre.
        for station_name in (
            self.accepted_stations
        ):

            if not isinstance(
                station_name,
                str
            ):

                print(
                    "Error: accepted station "
                    "names must be strings"
                )

                return False

            if station_name.strip() == "":

                print(
                    "Error: accepted station "
                    "name cannot be empty"
                )

                return False


        # Si llegÃ³ hasta aquÃ­,
        # todos sus atributos propios
        # son vÃ¡lidos.
        return True


    def __str__(self):

        return (
            f"Event("
            f"SIS-{self.identifier:06d}, "
            f"K={self.get_key()}, "
            f"Revision={self.revision}"
            f")"
        )


    # Convierte el evento a un diccionario.
    #
    # SerÃ¡ utilizado posteriormente
    # para JSON, versiones y persistencia.
    def to_dict(self):

        date_time_text = (
            self.date_time.isoformat(
                timespec="seconds"
            )
        )

        # ISO 8601 representa UTC
        # utilizando Z.
        if date_time_text.endswith(
            "+00:00"
        ):

            date_time_text = (
                date_time_text[:-6]
                +
                "Z"
            )


        return {
            "identifier": (
                self.identifier
            ),

            "magnitude": (
                self.magnitude
            ),

            "depth": (
                self.depth
            ),

            "x": (
                self.x
            ),

            "y": (
                self.y
            ),

            "date_time": (
                date_time_text
            ),

            "revision": (
                self.revision
            ),

            "priority": (
                self.priority
            ),

            "is_populated_zone": (
                self.is_populated_zone
            ),

            "attention_status": (
                self.attention_status.value
            ),

            "catalog_status": (
                self.catalog_status.value
            ),

            "accepted_stations": (
                sorted(
                    self.accepted_stations
                )
            )
        }

    
