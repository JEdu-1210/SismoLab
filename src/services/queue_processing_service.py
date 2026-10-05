from time import sleep

from src.business.AccessService import AccessService
from src.business.ReportService import ReportService

from src.models.Report import Report
from src.models.Returnings import DataAndMsgReturn

from src.services.audit_service import AuditService
from src.services.undo_service import UndoService
from src.services.persistencia import PersistenceService

class QueueProcessingService:

    def __init__(
        self,
        sismolab,
        undo_service=None
    ):

        self.sismolab = sismolab

        # ReportService contiene TODAS las reglas
        # del punto 6.
        self.report_service = (
            ReportService(
                sismolab
            )
        )

        self.access_service = (
            AccessService(
                sismolab
            )
        )

        # Cuando terminemos el punto 13
        # pasaremos aquÃ­ el UndoService corregido.
        self.undo_service = (
            undo_service
            if undo_service is not None
            else UndoService()
        )


    # =========================================================
    # PREPARAR RÃFAGA
    # =========================================================

    # Agrega N reportes sin procesarlos.
    #
    # Todos se validan primero para evitar
    # agregar solamente una parte de la rÃ¡faga.
    def enqueue_burst(
        self,
        reports
    ):

        response = DataAndMsgReturn()


        if (
            not isinstance(
                reports,
                (list, tuple)
            )
            or
            len(reports) == 0
        ):

            response.ok = False
            response.error = (
                "A burst must contain "
                "at least one report"
            )

            return response


        # Validar TODA la rÃ¡faga primero.
        for report in reports:

            if not isinstance(
                report,
                Report
            ):

                response.ok = False
                response.error = (
                    "All burst elements "
                    "must be Report objects"
                )

                return response


        report_queue = (
            self.sismolab
            .get_report_queue()
        )


        # Ahora sÃ­ se agregan todos,
        # conservando exactamente su orden.
        for report in reports:

            report_queue.enqueue(
                report
            )


        response.data = {
            "added": len(reports),

            "queue_size":
                report_queue.size(),

            "queue":
                self.get_queue_view()
        }


        response.msg = (
            "Report burst added "
            "to FIFO queue"
        )


        return response


    # =========================================================
    # VISUALIZAR COLA
    # =========================================================

    # Prepara el contenido para que posteriormente
    # la GUI pueda mostrar el orden FIFO.
    def get_queue_view(self):

        result = []


        reports = (
            self.sismolab
            .get_report_queue()
            .get_reports()
        )


        for position, report in enumerate(
            reports,
            start=1
        ):

            result.append({
                "position": position,

                "station":
                    self._station_name(
                        report
                    ),

                "event_id":
                    report.identifier,

                "revision":
                    report.revision,

                "decision":
                    report.decision
            })


        return result


    # =========================================================
    # PROCESAR UN REPORTE
    # =========================================================

    # Ejecuta exactamente UN paso FIFO.
    def process_next_report(self):

        response = DataAndMsgReturn()

        report_queue = (
            self.sismolab
            .get_report_queue()
        )


        if report_queue.is_empty():

            response.ok = False
            response.error = (
                "The report queue is empty"
            )

            return response


        state_before = (
            self.undo_service
            .capture_state(
                self.sismolab
            )
        )

        avl_tree = (
            self.sismolab
            .get_avl_tree()
        )


        # Queremos saber solamente las
        # rotaciones de ESTE reporte.
        avl_tree.clear_rotation_log()


        # FIFO:
        # se procesa exactamente el primero.
        report = report_queue.dequeue()


        try:

            (
                success,
                message,
                processed_report
            ) = (
                self.report_service
                .process_report(
                    report
                )
            )


        except Exception as exc:

            PersistenceService.apply_state(
                self.sismolab,
                state_before
            )

            response.ok = False
            response.error = str(exc)

            return response


        if not success:

            PersistenceService.apply_state(
                self.sismolab,
                state_before
            )

            response.ok = False
            response.error = message

            return response


        rotations = (
            avl_tree.get_rotation_log()
        )


        # Actualizar contadores LL/RR/LR/RL
        # y giros elementales.
        self._register_rotation_metrics(
            rotations
        )

        self.undo_service.push_snapshot(
            self.sismolab,
            "PROCESS_REPORT",
            (
                f"Process report for "
                f"SIS-{processed_report.identifier:06d} "
                f"revision "
                f"{processed_report.revision}"
            ),
            state_before
        )

        if processed_report is None:

            processed_report = report


        scenario = (
            self.sismolab
            .get_scenario()
        )


        response.data = {

            "station":
                self._station_name(
                    processed_report
                ),

            "event_id":
                processed_report.identifier,

            "revision":
                processed_report.revision,

            "decision":
                processed_report.decision,

            "message":
                message,

            # Casos y giros exactos producidos
            # durante este paso.
            "rotations":
                rotations,

            "rotation_count":
                len([
                    rotation
                    for rotation in rotations
                    if rotation.get("kind")
                    == "rotation"
                ]),

            "stress_mode":
                scenario.is_stress_mode(),

            "remaining_reports":
                report_queue.size()
        }


        response.msg = (
            "Report processed successfully"
        )


        return response


    # =========================================================
    # PROCESAMIENTO CONTINUO
    # =========================================================

    # Procesa reportes uno por uno,
    # manteniendo una pausa entre pasos.
    #
    # max_steps es Ãºtil para pruebas.
    def process_continuous(
        self,
        pause_seconds=0.5,
        max_steps=None
    ):

        response = DataAndMsgReturn()


        try:
            pause_seconds = float(
                pause_seconds
            )

        except (
            TypeError,
            ValueError
        ):

            response.ok = False

            response.error = (
                "pause_seconds "
                "must be numeric"
            )

            return response


        if pause_seconds < 0:

            response.ok = False
            response.error = (
                "pause_seconds "
                "cannot be negative"
            )

            return response


        if max_steps is not None:

            if (
                isinstance(
                    max_steps,
                    bool
                )
                or
                not isinstance(
                    max_steps,
                    int
                )
                or
                max_steps <= 0
            ):

                response.ok = False

                response.error = (
                    "max_steps must be "
                    "a positive integer "
                    "or None"
                )

                return response


        report_queue = (
            self.sismolab
            .get_report_queue()
        )

        results = []


        while not report_queue.is_empty():

            if (
                max_steps is not None
                and
                len(results) >= max_steps
            ):

                break


            step_result = (
                self.process_next_report()
            )


            results.append(
                step_result.to_dict()
            )


            # Un error tÃ©cnico detiene
            # procesamiento continuo.
            if not step_result.ok:
                break


            # Pausa visible entre pasos.
            if (
                pause_seconds > 0
                and
                not report_queue.is_empty()
            ):

                sleep(
                    pause_seconds
                )


        response.data = {

            "processed_steps":
                len(results),

            "remaining_reports":
                report_queue.size(),

            "steps":
                results
        }


        response.msg = (
            "Continuous processing finished"
        )


        return response


    # =========================================================
    # ENTRAR EN MODO ESTRÃ‰S
    # =========================================================

    def enter_stress_mode(self):

        response = DataAndMsgReturn()

        scenario = (
            self.sismolab
            .get_scenario()
        )


        if scenario.is_stress_mode():

            response.data = {
                "stress_mode": True
            }

            response.msg = (
                "Stress mode is already enabled"
            )

            return response


        state_before = (
            self.undo_service
            .capture_state(
                self.sismolab
            )
        )


        scenario.set_stress_mode(
            True
        )


        self.undo_service.push_snapshot(
            self.sismolab,
            "CHANGE_STRESS_MODE",
            "Enable stress mode",
            state_before
        )


        response.data = {
            "stress_mode": True
        }


        response.msg = (
            "Stress mode enabled. "
            "AVL rotations are deferred"
        )


        return response


    # =========================================================
    # RECUPERACIÃ“N GLOBAL
    # =========================================================

    def recover_avl_balance(self):

        response = DataAndMsgReturn()

        scenario = (
            self.sismolab
            .get_scenario()
        )

        avl_tree = (
            self.sismolab
            .get_avl_tree()
        )


        # Esta operaciÃ³n corresponde
        # especÃ­ficamente al modo estrÃ©s.
        if not scenario.is_stress_mode():

            response.ok = False

            response.error = (
                "Global recovery is only "
                "required while stress mode "
                "is active"
            )

            return response

        state_before = (
            self.undo_service
            .capture_state(
                self.sismolab
            )
        )

        avl_tree.clear_rotation_log()


        # IMPORTANTE:
        #
        # recover_balance NO vacÃ­a el Ã¡rbol.
        # Trabaja sobre la estructura existente.
        recovery_cost = (
            avl_tree.recover_balance()
        )


        rotations = (
            avl_tree.get_rotation_log()
        )


        self._register_rotation_metrics(
            rotations
        )


        # Rotaciones modifican profundidades.
        self.access_service \
            .update_access_marks()


        # Primera protecciÃ³n:
        # comprobar estructuralmente el balance.
        if not avl_tree.is_balanced():

            response.ok = False

            response.error = (
                "Global recovery did not "
                "restore the AVL balance condition"
            )

            response.data = {

                "recovery_completed": False,

                "rotations":
                    rotations,

                "cost":
                    recovery_cost
            }

            PersistenceService.apply_state(
                self.sismolab,
                state_before
            )
            # Sigue en modo estrÃ©s.
            return response


        # Probamos temporalmente el modo normal
        # para que la auditorÃ­a exija balance AVL.
        scenario.set_stress_mode(
            False
        )


        try:

            audit_result = (
                AuditService
                .verify_structure(
                    self.sismolab
                )
            )

        except Exception as exc:

            PersistenceService.apply_state(
                self.sismolab,
                state_before
            )

            response.ok = False

            response.error = (
                "Recovery finished, but "
                "audit could not be completed: "
                f"{exc}"
            )

            response.data = {

                "recovery_completed":
                    False,

                "rotations":
                    rotations,

                "cost":
                    recovery_cost
            }

            return response

        audit_data = (
            audit_result.data
            or
            {}
        )


        # Solamente permanecemos en modo normal
        # cuando AuditService confirma validez.
        if not audit_data.get(
            "is_valid",
            False
        ):


            response.ok = False

            response.error = (
                "Audit rejected the "
                "recovered AVL. "
                "Stress mode remains active"
            )


            response.data = {

                "recovery_completed":
                    False,

                "rotations":
                    rotations,

                "cost":
                    recovery_cost,

                "audit":
                    audit_data
            }

            PersistenceService.apply_state(
                self.sismolab,
                state_before
            )
            return response


        # La auditorÃ­a confirmÃ³ el Ã¡rbol.
        response.data = {

            "recovery_completed":
                True,

            "stress_mode":
                False,

            "rotations":
                rotations,

            "rotation_count":
                len([
                    rotation
                    for rotation in rotations
                    if rotation.get("kind")
                    == "rotation"
                ]),

            "cost":
                recovery_cost,

            "audit":
                audit_data
        }


        response.msg = (
            "Global AVL recovery completed "
            "and confirmed by audit"
        )

        self.undo_service.push_snapshot(
            self.sismolab,
            "GLOBAL_RECOVERY",
            "Recover AVL balance after stress mode",
            state_before
        )

        return response


    # =========================================================
    # AUXILIARES
    # =========================================================

    def _station_name(
        self,
        report
    ):

        station = report.station


        if station is None:
            return None


        if hasattr(
            station,
            "name"
        ):

            return station.name


        return str(
            station
        )


    # Registra mÃ©tricas de balanceo utilizando
    # el log generado por AVLTree.
    def _register_rotation_metrics(
        self,
        rotations
    ):

        metrics = (
            self.sismolab
            .get_metrics()
        )


        for item in rotations:

            if item.get("kind") == "case":

                case = item.get(
                    "case"
                )


                if case == "LL":

                    metrics.increment_ll_case()


                elif case == "RR":

                    metrics.increment_rr_case()


                elif case == "LR":

                    metrics.increment_lr_case()


                elif case == "RL":

                    metrics.increment_rl_case()


            elif (
                item.get("kind")
                ==
                "rotation"
            ):

                direction = item.get(
                    "direction"
                )


                if direction == "LEFT":

                    metrics \
                        .increment_left_rotation()


                elif direction == "RIGHT":

                    metrics \
                        .increment_right_rotation()
                    

