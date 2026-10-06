from math import hypot, isfinite

from src.models.Association import Association
from src.models.Status import CatalogStatus


class AssociationService:

    def __init__(
        self,
        sismolab
    ):

        self.sismolab = sismolab


    # EVENTOS DISPONIBLES PARA ASOCIACIONES
    # Las asociaciones consideran eventos
    # ACTIVE y ARCHIVED.
    # Los DELETED nunca participan.
    def _is_available_event(
        self,
        event
    ):

        return event.catalog_status in (
            CatalogStatus.ACTIVE,
            CatalogStatus.ARCHIVED
        )


    # DISTANCIA
    # Distancia euclidiana entre
    # los epicentros de dos Events.
    def calculate_distance(
        self,
        event_a,
        event_b
    ):

        return hypot(
            event_a.x - event_b.x,
            event_a.y - event_b.y
        )


    # DIFERENCIA DE TIEMPO
    # Retorna cuántas horas después ocurrió B
    # con respecto a A.
    def calculate_time_difference_hours(
        self,
        event_a,
        event_b
    ):

        difference = (
            event_b.date_time
            -
            event_a.date_time
        )

        return (
            difference.total_seconds()
            /
            3600
        )


    # VALIDAR CANDIDATO
    # Determina si event_a puede ser
    # referencia de event_b.
    def is_candidate(
        self,
        event_a,
        event_b
    ):

        scenario = self.sismolab.get_scenario()


        # Un Event nunca puede ser
        # referencia de sí mismo.
        if (
            event_a.identifier
            ==
            event_b.identifier
        ):
            return False


        # Solo ACTIVE y ARCHIVED participan.
        if not self._is_available_event(
            event_a
        ):
            return False

        if not self._is_available_event(
            event_b
        ):
            return False


        # A debe tener magnitud
        # estrictamente mayor que B.
        if (
            event_a.magnitude
            <=
            event_b.magnitude
        ):
            return False


        # A debe haber ocurrido
        # estrictamente antes que B.
        if (
            event_a.date_time
            >=
            event_b.date_time
        ):
            return False


        time_difference = (
            self.calculate_time_difference_hours(
                event_a,
                event_b
            )
        )


        # La diferencia temporal
        # puede ser como máximo W.
        if (
            time_difference
            >
            scenario.get_w_hours()
        ):
            return False


        distance = self.calculate_distance(
            event_a,
            event_b
        )


        # La distancia puede ser
        # como máximo R.
        if (
            distance
            >
            scenario.get_r_km()
        ):
            return False


        return True


    # OBTENER CANDIDATOS
    # Retorna todos los Events que pueden
    # funcionar como referencia del Event recibido.
    def get_candidates(
        self,
        event
    ):

        scenario = self.sismolab.get_scenario()

        candidates = []


        for candidate in (
            scenario
            .get_events_by_id()
            .values()
        ):

            if self.is_candidate(
                candidate,
                event
            ):

                candidates.append(
                    candidate
                )


        return candidates


    # SELECCIONAR REFERENCIA
    # Criterio determinista:
    # 1. Menor distancia.
    # 2. Si empatan, menor identifier.
    def choose_reference(
        self,
        event
    ):

        candidates = self.get_candidates(
            event
        )


        if len(candidates) == 0:
            return None


        return min(
            candidates,
            key=lambda candidate: (
                self.calculate_distance(
                    candidate,
                    event
                ),
                candidate.identifier
            )
        )


    # ASOCIACIÓN ACTUAL DE UN EVENTO
    # Busca la asociación donde el Event recibido
    # funciona como posible réplica.
    # Cada B tiene como máximo una
    # referencia elegida.
    def get_association_for_event(
        self,
        event
    ):

        for association in (
            self.sismolab.get_associations()
        ):

            aftershock_event = (
                association
                .get_aftershock_event()
            )


            if (
                aftershock_event.identifier
                ==
                event.identifier
            ):

                return association


        return None


    # RECALCULAR TODAS LAS ASOCIACIONES
    # Volvemos a calcular todas las relaciones
    # utilizando los datos vigentes.
    # Esto simplifica las altas, correcciones,
    # eliminaciones y cambios de W/R.
    def recalculate_all(self):

        scenario = self.sismolab.get_scenario()

        events = []


        # Solo ACTIVE y ARCHIVED.
        for event in (
            scenario
            .get_events_by_id()
            .values()
        ):

            if self._is_available_event(
                event
            ):

                events.append(
                    event
                )


        # Las asociaciones anteriores
        # dejan de ser válidas como conjunto.
        self.sismolab.clear_associations()


        # Cada Event B busca su mejor
        # referencia A.
        for event in events:

            reference_event = (
                self.choose_reference(
                    event
                )
            )


            if reference_event is None:
                continue


            association = Association(
                reference_event,
                event
            )


            self.sismolab.add_association(
                association
            )


        return len(
            self.sismolab.get_associations()
        )


    # DATOS PARA LA GUI
    # Prepara los candidatos de un Event
    # para que la GUI pueda mostrarlos.
    def get_candidate_details(
        self,
        identifier
    ):

        scenario = self.sismolab.get_scenario()


        try:
            identifier = int(identifier)

        except (TypeError, ValueError):

            return (
                False,
                "Invalid identifier",
                None
            )


        event = scenario.get_event_by_id(
            identifier
        )


        if event is None:

            return (
                False,
                "Event not found",
                None
            )


        if not self._is_available_event(
            event
        ):

            return (
                False,
                "Deleted events do not have associations",
                None
            )


        candidates = self.get_candidates(
            event
        )

        selected_reference = (
            self.choose_reference(
                event
            )
        )


        details = []


        for candidate in candidates:

            distance = (
                self.calculate_distance(
                    candidate,
                    event
                )
            )

            time_difference = (
                self.calculate_time_difference_hours(
                    candidate,
                    event
                )
            )


            details.append({
                "identifier": (
                    candidate.identifier
                ),
                "magnitude": (
                    candidate.magnitude
                ),
                "catalog_status": (
                    candidate.catalog_status.value
                ),
                "distance_km": distance,
                "time_difference_hours": (
                    time_difference
                ),
                "selected": (
                    selected_reference is not None
                    and
                    candidate.identifier
                    ==
                    selected_reference.identifier
                )
            })


        # Los mostramos usando el mismo criterio
        # con el que seleccionamos la referencia.
        details.sort(
            key=lambda candidate: (
                candidate["distance_km"],
                candidate["identifier"]
            )
        )


        return (
            True,
            "Candidates calculated successfully",
            details
        )


    # CAMBIAR W Y R
    # Puede cambiar W, R o ambos.
    # Si alguno cambia, las asociaciones se recalculan automáticamente.
    def update_limits(
        self,
        w_hours=None,
        r_km=None
    ):

        scenario = self.sismolab.get_scenario()


        if (
            w_hours is None
            and
            r_km is None
        ):

            return (
                False,
                "No association limits were provided",
                None
            )


        new_w = (
            scenario.get_w_hours()
            if w_hours is None
            else w_hours
        )

        new_r = (
            scenario.get_r_km()
            if r_km is None
            else r_km
        )


        try:
            new_w = float(new_w)
            new_r = float(new_r)

        except (TypeError, ValueError):

            return (
                False,
                "Invalid association limits",
                None
            )


        # Validamos ambos ANTES
        # de cambiar cualquiera.
        if (
            not isfinite(new_w)
            or new_w <= 0
            or not isfinite(new_r)
            or new_r <= 0
        ):

            return (
                False,
                "W and R must be positive",
                None
            )


        scenario.set_w_hours(
            new_w
        )

        scenario.set_r_km(
            new_r
        )


        self.recalculate_all()


        return (
            True,
            "Association limits updated successfully",
            {
                "w_hours": new_w,
                "r_km": new_r
            }
        )
