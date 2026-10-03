from business.AccessService import AccessService


class ArchiveService:

    def __init__(
        self,
        sismolab
    ):

        self.sismolab = sismolab

        self.access_service = (
            AccessService(
                sismolab
            )
        )

    # ELEGIR MEJOR CANDIDATO
    # Busca automáticamente la mejor rama elegible.
    # Retorna un diccionario con:
    # - root
    # - count
    # - depth
    # - root_id
    # o None si no existe ninguna.
    def find_best_candidate(self):

        avl_tree = self.sismolab.get_avl_tree()

        if avl_tree.is_empty():
            return None


        scenario = self.sismolab.get_scenario()

        simulation_clock = (
            scenario.get_simulation_clock()
        )

        archive_age_hours = (
            scenario.get_archive_age_hours()
        )


        (
            _,
            _,
            best_candidate
        ) = self._evaluate_subtree(
            avl_tree.get_root(),
            0,
            simulation_clock,
            archive_age_hours
        )


        return best_candidate


    # Recorre el árbol en postorden.
    # Retorna:
    # (
    #     subtree_is_eligible,
    #     node_count,
    #     best_candidate
    # )
    def _evaluate_subtree(
        self,
        node,
        depth,
        simulation_clock,
        archive_age_hours
    ):

        if node is None:
            return True, 0, None


        (
            left_eligible,
            left_count,
            left_best
        ) = self._evaluate_subtree(
            node.get_left(),
            depth + 1,
            simulation_clock,
            archive_age_hours
        )


        (
            right_eligible,
            right_count,
            right_best
        ) = self._evaluate_subtree(
            node.get_right(),
            depth + 1,
            simulation_clock,
            archive_age_hours
        )


        event = node.get_event()

        age_hours = (
            simulation_clock
            -
            event.date_time
        ).total_seconds() / 3600


        # Este Event individual cumple las reglas de archivo.
        event_is_eligible = (
            event.priority == 1
            and age_hours > archive_age_hours
        )


        # El subárbol completo solamente es
        # elegible si TODOS sus Events cumplen.
        subtree_is_eligible = (
            event_is_eligible
            and left_eligible
            and right_eligible
        )


        node_count = (
            1
            + left_count
            + right_count
        )


        # Primero conservamos el mejor candidato
        # encontrado en los descendientes.
        best_candidate = self._better_candidate(
            left_best,
            right_best
        )


        # Si todo este subárbol es elegible,
        # también lo evaluamos como candidato.
        if subtree_is_eligible:

            candidate = {
                "root": node,
                "count": node_count,
                "depth": depth,
                "root_id": event.identifier
            }


            best_candidate = (
                self._better_candidate(
                    best_candidate,
                    candidate
                )
            )


        return (
            subtree_is_eligible,
            node_count,
            best_candidate
        )


    # Decide cuál de dos candidatos gana.
    # Prioridad:
    # 1. Mayor cantidad de nodos.
    # 2. Mayor profundidad de la raíz.
    # 3. Mayor identifier de la raíz.
    def _better_candidate(
        self,
        candidate1,
        candidate2
    ):

        if candidate1 is None:
            return candidate2

        if candidate2 is None:
            return candidate1


        score1 = (
            candidate1["count"],
            candidate1["depth"],
            candidate1["root_id"]
        )

        score2 = (
            candidate2["count"],
            candidate2["depth"],
            candidate2["root_id"]
        )


        if score2 > score1:
            return candidate2

        return candidate1


    # OBTENER EVENTS DEL SUBÁRBOL

    def _collect_events(
        self,
        node,
        events
    ):

        if node is None:
            return


        events.append(
            node.get_event()
        )


        self._collect_events(
            node.get_left(),
            events
        )

        self._collect_events(
            node.get_right(),
            events
        )


    # VISTA PREVIA

    # Prepara la información que la GUI mostrará
    # antes de confirmar el archivo.
    def get_archive_preview(self):

        candidate = self.find_best_candidate()


        if candidate is None:

            return (
                False,
                "No eligible branch was found",
                None
            )


        events = []

        self._collect_events(
            candidate["root"],
            events
        )


        event_ids = sorted(
            event.identifier
            for event in events
        )


        scenario = self.sismolab.get_scenario()

        details = {
            "root_id": candidate["root_id"],
            "event_ids": event_ids,
            "count": candidate["count"],
            "depth": candidate["depth"],
            "archive_age_hours": (
                scenario.get_archive_age_hours()
            ),
            "reason": (
                "All events have priority 1 "
                "and are older than T hours. "
                "This branch was selected by "
                "node count, root depth and root ID."
            )
        }


        return (
            True,
            "Eligible branch found",
            details
        )


    # ARCHIVAR RAMA

    def archive_old_events_branch(self):

        candidate = self.find_best_candidate()


        if candidate is None:

            return (
                False,
                "No eligible branch was found",
                None
            )


        root = candidate["root"]

        events = []

        # IMPORTANTE:
        # fijamos el conjunto ANTES de modificar
        # cualquier árbol.
        self._collect_events(
            root,
            events
        )


        event_ids = [
            event.identifier
            for event in events
        ]


        avl_tree = self.sismolab.get_avl_tree()
        bst_tree = self.sismolab.get_bst_tree()

        history = self.sismolab.get_history()
        scenario = self.sismolab.get_scenario()


        # 1. Verificar primero que TODOS los Events
        #    también existan en el BST.

        for event in events:

            if bst_tree.search(
                event.get_key()
            ) is None:

                return (
                    False,
                    "An event from the selected branch "
                    "is missing from the BST",
                    None
                )


        # Aquí posteriormente registraremos
        # UN SOLO snapshot para Undo.
        # 2. Eliminar esos mismos Events del BST.
        # No archivamos una rama BST porque su
        # topología puede ser distinta a la del AVL.

        for event in events:

            deleted_event = bst_tree.delete(
                event.get_key()
            )

            if deleted_event is None:

                return (
                    False,
                    "The branch could not be removed "
                    "from the BST",
                    None
                )


        # 3. Desprender la rama COMPLETA del AVL.
        # Usamos rebalance=False para que primero
        # se desprenda exactamente el conjunto fijado.

        archived_root = avl_tree.detach_subtree(
            root,
            rebalance=False
        )


        if archived_root is None:

            return (
                False,
                "The AVL branch could not be detached",
                None
            )


        # 4. Todos esos Events dejan de ser activos
        #    y pasan al estado ARCHIVED.

        for event in events:
            event.archive()


        # 5. Guardar la raíz del subárbol
        #    dentro del History.

        history.add_archived_root(
            archived_root
        )


        # 6. Restaurar balance solamente en modo normal.
        # En estrés NO realizamos rotaciones.

        if not scenario.is_stress_mode():
            avl_tree.recover_balance()

        # Archivar una rama cambia
        # la estructura del AVL activo.
        self.access_service.update_access_marks()
        
        # IMPORTANTE:
        # - NO eliminamos estos Events de scenario._events_by_id.
        # - NO agregamos sus IDs a retired_ids.
        # - NO eliminamos sus asociaciones.
        # Siguen existiendo, pero como ARCHIVED.

        # Aquí posteriormente actualizaremos:
        # - métricas
        # - Undo
        # - GUI


        result = {
            "root_id": candidate["root_id"],
            "event_ids": sorted(event_ids),
            "count": candidate["count"]
        }


        return (
            True,
            "Branch archived successfully",
            result
        )