from src.models.Event import Event
from src.models.Report import Report
from src.models.Status import CatalogStatus

from src.business.EventService import EventService


class ReportService:

    def __init__(
        self,
        sismolab
    ):

        self.sismolab = sismolab

        self.event_service = EventService(
            sismolab
        )


    # ESTACIÓN EMISORA

    def _get_registered_station(
        self,
        report
    ):

        scenario = self.sismolab.get_scenario()


        if report.station is None:
            return None


        if not hasattr(
            report.station,
            "name"
        ):
            return None


        return scenario.get_station_by_name(
            report.station.name
        )


    # IGUALDAD DE DATOS

    # El proyecto define igualdad únicamente con:
    #
    # - magnitude
    # - depth
    # - epicentro (x, y)
    # - date_time
    #
    # La estación no participa.
    def same_event_data(
        self,
        event,
        report
    ):

        return (
            event.magnitude
            ==
            report.magnitude

            and

            event.depth
            ==
            report.depth

            and

            event.x
            ==
            report.x

            and

            event.y
            ==
            report.y

            and

            event.date_time
            ==
            report.date_time
        )


    # PREPARAR EVENT CANDIDATO
    # Construye cómo quedaría el Event
    # si los datos del reporte fueran aceptados.
    #
    # Todavía NO modifica ninguna estructura.
    def _build_candidate(
        self,
        report
    ):

        try:

            (
                is_populated_zone,
                priority
            ) = (
                self.event_service
                .calculate_event_data(
                    report.magnitude,
                    report.depth,
                    report.x,
                    report.y
                )
            )


            candidate = Event(
                report.identifier,
                report.magnitude,
                report.depth,
                report.x,
                report.y,
                report.date_time,
                report.revision,
                priority,
                is_populated_zone
            )


        except (
            TypeError,
            ValueError
        ):

            return None


        if not (
            self.event_service
            .validate_event(
                candidate
            )
        ):

            return None


        return candidate


    # DECISIONES

    def _finish(
        self,
        report,
        decision,
        message,
        event=None
    ):

        report.decision = decision
        report.event = event


        return (
            True,
            message,
            report
        )


    # PROCESAR REPORTE
    def process_report(
        self,
        report
    ):

        scenario = self.sismolab.get_scenario()
        metrics = self.sismolab.get_metrics()


        # 1. El objeto debe ser realmente un Report.

        if not isinstance(
            report,
            Report
        ):

            return (
                False,
                "Invalid Report object",
                None
            )


        # 2. Validaciones básicas.

        if (
            report.identifier < 1
            or report.identifier > 999999
        ):

            metrics.increment_discarded_reports()

            return self._finish(
                report,
                "INVALID",
                "Invalid report identifier"
            )


        if report.revision <= 0:

            metrics.increment_discarded_reports()

            return self._finish(
                report,
                "INVALID",
                "Report revision must be positive"
            )


        station = self._get_registered_station(
            report
        )


        if station is None:

            metrics.increment_discarded_reports()

            return self._finish(
                report,
                "INVALID",
                "The reporting station does not exist"
            )


        # 3. Un ID eliminado jamás puede reactivarse
        #    mediante reportes.

        if self.sismolab.is_retired_id(
            report.identifier
        ):

            event = scenario.get_event_by_id(
                report.identifier
            )

            metrics.increment_discarded_reports()

            return self._finish(
                report,
                "REJECTED_DELETED",
                "Reports for deleted identifiers are rejected",
                event
            )


        # 4. Buscar identidad ANTES de mirar K.
        #
        # Esto garantiza que nunca creemos
        # dos nodos para el mismo terremoto.

        event = scenario.get_event_by_id(
            report.identifier
        )


        # CASO 1:
        # IDENTIFICADOR DESCONOCIDO

        if event is None:

            candidate = self._build_candidate(
                report
            )


            if candidate is None:

                metrics.increment_discarded_reports()

                return self._finish(
                    report,
                    "INVALID",
                    "Invalid data for new event"
                )


            (
                success,
                message,
                new_event
            ) = (
                self.event_service
                .create_event_from_report(
                    candidate,
                    station
                )
            )


            if not success:

                return (
                    False,
                    message,
                    report
                )


            return self._finish(
                report,
                "CREATED",
                "New event registered from report",
                new_event
            )


        # CASO 2:
        # REVISIÓN MENOR

        if (
            report.revision
            <
            event.revision
        ):

            metrics.increment_discarded_reports()

            return self._finish(
                report,
                "OLD_REPORT",
                "Report discarded because its revision is old",
                event
            )


        # CASO 3:
        # MISMA REVISIÓN

        if (
            report.revision
            ==
            event.revision
        ):

            # ---------------------------------------------
            # Mismos datos -> confirmación.
            # ---------------------------------------------

            if self.same_event_data(
                event,
                report
            ):

                (
                    success,
                    message,
                    confirmed_event
                ) = (
                    self.event_service
                    .confirm_event_report(
                        event,
                        station
                    )
                )


                if not success:

                    return (
                        False,
                        message,
                        report
                    )


                # IMPORTANTE:
                # Si estaba ARCHIVED,
                # sigue ARCHIVED.
                return self._finish(
                    report,
                    "CONFIRMED",
                    "Event confirmed by station",
                    confirmed_event
                )


            # Misma revisión + datos diferentes
            # -> CONFLICTO.

            metrics.increment_conflicts()


            return self._finish(
                report,
                "CONFLICT",
                "Same revision with different event data",
                event
            )


        # CASO 4:
        # REVISIÓN MAYOR

        candidate = self._build_candidate(
            report
        )


        # Primero validamos TODO.
        # Si falla, no se modifica el Event vigente.
        if candidate is None:

            metrics.increment_discarded_reports()

            return self._finish(
                report,
                "INVALID",
                "Invalid data in newer revision",
                event
            )


        # EVENTO ACTIVO:
        # corregir sus datos vigentes.

        if (
            event.catalog_status
            ==
            CatalogStatus.ACTIVE
        ):

            (
                success,
                message,
                updated_event
            ) = (
                self.event_service
                .update_event_from_report(
                    event,
                    candidate,
                    station
                )
            )


            if not success:

                return (
                    False,
                    message,
                    report
                )


            return self._finish(
                report,
                "UPDATED",
                "Newer revision accepted",
                updated_event
            )


        # EVENTO ARCHIVADO:
        # una revisión mayor válida lo reactiva.

        if (
            event.catalog_status
            ==
            CatalogStatus.ARCHIVED
        ):

            (
                success,
                message,
                reactivated_event
            ) = (
                self.event_service
                .reactivate_archived_event_from_report(
                    event,
                    candidate,
                    station
                )
            )


            if not success:

                return (
                    False,
                    message,
                    report
                )


            return self._finish(
                report,
                "REACTIVATED",
                "Archived event reactivated by newer revision",
                reactivated_event
            )


        # Un DELETED normalmente ya quedó
        # atrapado mediante retired_ids.
        #
        # Esto es solo una protección adicional.
        metrics.increment_discarded_reports()

        return self._finish(
            report,
            "REJECTED_DELETED",
            "Deleted event cannot be reactivated",
            event
        )
