from src.models.Returnings import DataAndMsgReturn
from src.models.UndoAction import UndoAction

from src.services.persistencia import PersistenceService


class UndoService:

    # =========================================================
    # CAPTURAR ESTADO
    # =========================================================

    # Obtiene una fotografÃ­a COMPLETA del estado
    # operativo sin modificar todavÃ­a la pila.
    #
    # Esto es Ãºtil porque primero podemos ejecutar
    # la operaciÃ³n y solamente guardar la acciÃ³n
    # si realmente terminÃ³ correctamente.
    def capture_state(
        self,
        sismolab
    ):

        return (
            PersistenceService
            .export_state(
                sismolab
            )
        )


    # =========================================================
    # GUARDAR SNAPSHOT EN LA PILA
    # =========================================================

    def push_snapshot(
        self,
        sismolab,
        action_type,
        description,
        state_before
    ):

        if state_before is None:
            return False



        # MÃ©tricas antes de la acciÃ³n.
        before_metrics = (
            state_before.get(
                "metrics",
                {}
            )
        )


        # MÃ©tricas despuÃ©s de la acciÃ³n.
        state_after = (
            PersistenceService
            .export_state(
                sismolab
            )
        )

        after_metrics = (
            state_after.get(
                "metrics",
                {}
            )
        )


        # Guardamos solamente los contadores
        # que realmente cambiaron.
        metric_effects = {}


        all_metric_names = (
            set(before_metrics.keys())
            |
            set(after_metrics.keys())
        )


        for metric_name in all_metric_names:

            before_value = (
                before_metrics.get(
                    metric_name,
                    0
                )
            )

            after_value = (
                after_metrics.get(
                    metric_name,
                    0
                )
            )


            difference = (
                after_value
                -
                before_value
            )


            if difference != 0:

                metric_effects[
                    metric_name
                ] = difference


        action = UndoAction(
            action_type,
            state_before,
            description,
            metric_effects
        )

        sismolab.get_undo_stack().push(
            action
        )


        return True


    # =========================================================
    # REGISTRAR DIRECTAMENTE
    # =========================================================

    # Se conserva como mÃ©todo auxiliar para operaciones
    # donde sabemos que inmediatamente despuÃ©s habrÃ¡
    # una modificaciÃ³n.
    #
    # Para operaciones que pueden fallar es mejor:
    #
    # capture_state()
    # ejecutar
    # push_snapshot()
    def record_action(
        self,
        action_type,
        description,
        sismolab
    ):

        state_before = (
            self.capture_state(
                sismolab
            )
        )


        return self.push_snapshot(
            sismolab,
            action_type,
            description,
            state_before
        )


    # =========================================================
    # CONSULTAR SI HAY UNDO
    # =========================================================

    def can_undo(
        self,
        sismolab
    ):

        return not (
            sismolab
            .get_undo_stack()
            .is_empty()
        )


    # =========================================================
    # DESHACER
    # =========================================================

    def undo(
        self,
        sismolab
    ):

        response = DataAndMsgReturn()

        stack = (
            sismolab
            .get_undo_stack()
        )


        if stack.is_empty():

            response.ok = False
            response.error = (
                "There are no actions to undo"
            )

            return response


        # IMPORTANTE:
        #
        # Primero hacemos peek().
        #
        # No hacemos pop todavÃ­a porque si por
        # alguna razÃ³n la restauraciÃ³n falla,
        # no queremos perder la acciÃ³n.
        action = stack.peek()


        state_before = (
            action.get_state_before()
        )


        restore_result = (
            PersistenceService
            .apply_state(
                sismolab,
                state_before,
                success_message=(
                    "Previous state restored "
                    "successfully"
                )
            )
        )


        if not restore_result.ok:

            response.ok = False

            response.error = (
                "Undo could not restore "
                "the previous state: "
                f"{restore_result.error}"
            )

            return response


        # La restauraciÃ³n fue correcta.
        # Ahora sÃ­ retiramos la acciÃ³n.
        stack.pop()


        response.data = {

            "action_type":
                action.get_action_type(),

            "description":
                action.get_description(),

            "created_at":
                action
                .get_created_at()
                .isoformat(),

            "remaining_actions":
                stack.size(),
                
            "metric_effects":
                action.get_metric_effects(),
        }


        response.msg = (
            "Action undone successfully: "
            f"{action.get_description()}"
        )


        return response


    # =========================================================
    # HISTORIAL PARA LA GUI
    # =========================================================

    def get_undo_history(
        self,
        sismolab
    ):

        response = DataAndMsgReturn()


        actions = (
            sismolab
            .get_undo_stack()
            .get_actions()
        )


        # Mostramos primero la acciÃ³n
        # que se desharÃ­a inmediatamente.
        result = []


        for action in reversed(
            actions
        ):

            result.append({

                "action_type":
                    action.get_action_type(),

                "description":
                    action.get_description(),

                "created_at":
                    action
                    .get_created_at()
                    .isoformat(),

                "metric_effects":
                    action.get_metric_effects()
            })


        response.data = {

            "actions":
                result,

            "count":
                len(result)
        }


        response.msg = (
            f"{len(result)} undo "
            "action(s) available"
        )


        return response


    # =========================================================
    # LIMPIAR PILA
    # =========================================================

    def clear(
        self,
        sismolab
    ):

        sismolab.get_undo_stack().clear()


    # =========================================================
    # CARGA POR INSERCIONES + UNDO
    # =========================================================

    # La GUI debe utilizar ESTE mÃ©todo cuando
    # quiera cargar un archivo por inserciones.
    #
    # De esa manera toda la carga cuenta como
    # UNA sola acciÃ³n de Undo.
    def load_by_insertions(
        self,
        filepath,
        sismolab
    ):

        state_before = (
            self.capture_state(
                sismolab
            )
        )


        result = (
            PersistenceService
            .load_by_insertions(
                filepath,
                sismolab
            )
        )


        if result.ok:

            self.push_snapshot(
                sismolab,
                "LOAD_BY_INSERTIONS",
                "Load scenario by insertions",
                state_before
            )


        return result


    # =========================================================
    # CARGA POR TOPOLOGÃA + UNDO
    # =========================================================

    def load_by_topology(
        self,
        filepath,
        sismolab
    ):

        state_before = (
            self.capture_state(
                sismolab
            )
        )


        result = (
            PersistenceService
            .load_by_topology(
                filepath,
                sismolab
            )
        )


        if result.ok:

            self.push_snapshot(
                sismolab,
                "LOAD_BY_TOPOLOGY",
                "Load scenario by topology",
                state_before
            )


        return result


    # =========================================================
    # AVANZAR RELOJ + UNDO
    # =========================================================

    def advance_simulation_clock(
        self,
        sismolab,
        new_date_time
    ):

        response = DataAndMsgReturn()

        scenario = (
            sismolab.get_scenario()
        )


        state_before = (
            self.capture_state(
                sismolab
            )
        )


        if not scenario.set_simulation_clock(
            new_date_time
        ):

            response.ok = False

            response.error = (
                "Simulation clock could "
                "not be advanced"
            )

            return response


        self.push_snapshot(
            sismolab,
            "ADVANCE_CLOCK",
            "Advance simulation clock",
            state_before
        )


        response.data = {

            "simulation_clock":
                scenario
                .get_simulation_clock()
                .isoformat()
        }


        response.msg = (
            "Simulation clock advanced"
        )


        return response


    # =========================================================
    # CAMBIAR T + UNDO
    # =========================================================

    def update_archive_age(
        self,
        sismolab,
        hours
    ):

        response = DataAndMsgReturn()

        scenario = (
            sismolab.get_scenario()
        )


        state_before = (
            self.capture_state(
                sismolab
            )
        )


        if not scenario.set_archive_age_hours(
            hours
        ):

            response.ok = False

            response.error = (
                "T must be a positive "
                "finite number"
            )

            return response


        self.push_snapshot(
            sismolab,
            "CHANGE_ARCHIVE_AGE",
            "Change archive age T",
            state_before
        )


        response.data = {

            "archive_age_hours":
                scenario
                .get_archive_age_hours()
        }


        response.msg = (
            "Archive age T updated"
        )


        return response


    # =========================================================
    # CAMBIAR W/R + UNDO
    # =========================================================

    def update_association_limits(
        self,
        sismolab,
        association_service,
        w_hours=None,
        r_km=None
    ):

        state_before = (
            self.capture_state(
                sismolab
            )
        )


        (
            success,
            message,
            data
        ) = (
            association_service
            .update_limits(
                w_hours=w_hours,
                r_km=r_km
            )
        )


        if success:

            self.push_snapshot(
                sismolab,
                "CHANGE_ASSOCIATION_LIMITS",
                "Change W/R association limits",
                state_before
            )


        response = DataAndMsgReturn()

        response.ok = success
        response.data = data


        if success:

            response.msg = message

        else:

            response.error = message


        return response


    # =========================================================
    # CAMBIAR L + UNDO
    # =========================================================

    def update_access_limit(
        self,
        sismolab,
        access_service,
        access_limit
    ):

        state_before = (
            self.capture_state(
                sismolab
            )
        )


        (
            success,
            message,
            data
        ) = (
            access_service
            .update_access_limit(
                access_limit
            )
        )


        if success:

            self.push_snapshot(
                sismolab,
                "CHANGE_ACCESS_LIMIT",
                "Change access limit L",
                state_before
            )


        response = DataAndMsgReturn()

        response.ok = success
        response.data = data


        if success:

            response.msg = message

        else:

            response.error = message


        return response
