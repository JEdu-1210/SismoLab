from datetime import datetime
from math import isfinite

from src.business.AssociationService import AssociationService

from src.models.Returnings import DataAndMsgReturn
from src.models.Status import (
    AttentionStatus,
    CatalogStatus
)

from src.structures.AVLTree import AVLTree
from src.structures.BSTTree import BSTTree


class QueryService:

    def __init__(
        self,
        sismolab
    ):

        self.sismolab = sismolab

        self.association_service = (
            AssociationService(
                sismolab
            )
        )


    # =========================================================
    # AUXILIARES
    # =========================================================

    def _event_data(
        self,
        event
    ):

        data = event.to_dict()

        data["key"] = event.get_key()

        return data


    def _error(
        self,
        message,
        data=None
    ):

        response = DataAndMsgReturn()

        response.ok = False
        response.error = message
        response.data = data

        return response


    def _parse_datetime(
        self,
        value
    ):

        if isinstance(
            value,
            datetime
        ):

            result = value

        else:

            result = datetime.fromisoformat(
                str(value).replace(
                    "Z",
                    "+00:00"
                )
            )


        # Las fechas del proyecto trabajan en UTC.
        if (
            result.tzinfo is None
            or
            result.utcoffset() is None
        ):

            raise ValueError(
                "Dates must include UTC timezone"
            )


        if (
            result
            .utcoffset()
            .total_seconds()
            != 0
        ):

            raise ValueError(
                "Dates must use UTC timezone"
            )


        return result


    # =========================================================
    # CONSULTA 1
    # PRIMEROS K PENDIENTES EN ORDEN DESCENDENTE DE K
    # =========================================================

    def get_top_k_pending(
        self,
        k
    ):

        if (
            isinstance(k, bool)
            or
            not isinstance(k, int)
            or
            k <= 0
        ):

            return self._error(
                "k must be a positive integer"
            )


        avl_tree = (
            self.sismolab
            .get_avl_tree()
        )


        results = []

        examined_nodes = 0


        # Recorremos:
        #
        # derecha - raíz - izquierda
        #
        # porque las K mayores están
        # hacia la derecha.
        def visit(
            node
        ):

            nonlocal examined_nodes


            if (
                node is None
                or
                len(results) >= k
            ):

                return

            examined_nodes += 1
            
            visit(
                node.get_right()
            )


            if len(results) >= k:
                return




            event = (
                node.get_event()
            )


            if (
                event.attention_status
                ==
                AttentionStatus.PENDING
            ):

                results.append(
                    self._event_data(
                        event
                    )
                )


            if len(results) >= k:
                return


            visit(
                node.get_left()
            )


        visit(
            avl_tree.get_root()
        )


        response = DataAndMsgReturn()


        response.data = {

            "events":
                results,

            "count_retrieved":
                len(results),

            "k_requested":
                k,

            "examined_nodes":
                examined_nodes,

            "cost_analysis": {

                "worst_case":
                    "O(n)",

                "safe_pruning":
                    (
                        "The traversal stops once k "
                        "pending events are found in "
                        "descending K order. "
                        "Attention status is not part "
                        "of K, so no other subtree can "
                        "be safely discarded."
                    )
            }
        }


        response.msg = (
            f"Found {len(results)} "
            f"pending events after examining "
            f"{examined_nodes} AVL nodes"
        )


        return response


    # =========================================================
    # CONSULTA 2A
    # RANGO INCLUSIVO DE MAGNITUD
    # =========================================================

    def get_events_by_magnitude_range(
        self,
        min_magnitude,
        max_magnitude
    ):

        try:

            min_magnitude = float(
                min_magnitude
            )

            max_magnitude = float(
                max_magnitude
            )


        except (
            TypeError,
            ValueError
        ):

            return self._error(
                "Magnitude limits must be numeric"
            )


        if (
            not isfinite(
                min_magnitude
            )
            or
            not isfinite(
                max_magnitude
            )
            or
            min_magnitude
            >
            max_magnitude
        ):

            return self._error(
                "Invalid inclusive magnitude range"
            )


        avl_tree = (
            self.sismolab
            .get_avl_tree()
        )


        results = []

        examined_nodes = 0


        # Magnitud NO es el primer componente de K.
        #
        # K = (P, M, I)
        #
        # Por eso no podemos descartar
        # globalmente una rama usando solamente M.
        def visit(
            node
        ):

            nonlocal examined_nodes


            if node is None:
                return


            visit(
                node.get_left()
            )


            examined_nodes += 1


            event = (
                node.get_event()
            )


            if (
                min_magnitude
                <=
                event.magnitude
                <=
                max_magnitude
            ):

                results.append(
                    self._event_data(
                        event
                    )
                )


            visit(
                node.get_right()
            )


        visit(
            avl_tree.get_root()
        )


        response = DataAndMsgReturn()


        response.data = {

            "events":
                results,

            "min_magnitude":
                min_magnitude,

            "max_magnitude":
                max_magnitude,

            "examined_nodes":
                examined_nodes,

            "cost_analysis": {

                "worst_case":
                    "O(n)",

                "safe_pruning":
                    (
                        "No global subtree can be "
                        "discarded using magnitude "
                        "alone because K=(P,M,I) is "
                        "ordered first by priority."
                    )
            }
        }


        response.msg = (
            f"Found {len(results)} "
            f"active events in the "
            f"inclusive magnitude range"
        )


        return response


    # =========================================================
    # CONSULTA 2B
    # PROFUNDIDAD DEL HIPOCENTRO + RANGO DE FECHAS
    # =========================================================

    def get_events_by_depth_and_date_range(
        self,
        max_depth,
        start_date,
        end_date
    ):

        try:

            max_depth = float(
                max_depth
            )

            start_date = (
                self._parse_datetime(
                    start_date
                )
            )

            end_date = (
                self._parse_datetime(
                    end_date
                )
            )


        except (
            TypeError,
            ValueError
        ) as exc:

            return self._error(
                str(exc)
            )


        if (
            not isfinite(
                max_depth
            )
            or
            max_depth < 0
        ):

            return self._error(
                "Depth limit must be "
                "finite and non-negative"
            )


        if start_date > end_date:

            return self._error(
                "The start date cannot be "
                "later than the end date"
            )


        avl_tree = (
            self.sismolab
            .get_avl_tree()
        )


        results = []

        examined_nodes = 0


        # Ni profundidad del hipocentro
        # ni fecha pertenecen a K.
        #
        # Por eso debemos recorrer
        # todos los nodos activos.
        def visit(
            node
        ):

            nonlocal examined_nodes


            if node is None:
                return


            visit(
                node.get_left()
            )


            examined_nodes += 1


            event = (
                node.get_event()
            )


            if (
                event.depth
                <=
                max_depth

                and

                start_date
                <=
                event.date_time
                <=
                end_date
            ):

                results.append(
                    self._event_data(
                        event
                    )
                )


            visit(
                node.get_right()
            )


        visit(
            avl_tree.get_root()
        )


        response = DataAndMsgReturn()


        response.data = {

            "events":
                results,

            "max_depth":
                max_depth,

            "start_date":
                start_date.isoformat(),

            "end_date":
                end_date.isoformat(),

            "examined_nodes":
                examined_nodes,

            "cost_analysis": {

                "worst_case":
                    "O(n)",

                "safe_pruning":
                    (
                        "Hypocenter depth and "
                        "occurrence time are not part "
                        "of K, so no AVL branch can "
                        "be safely discarded using "
                        "these fields."
                    )
            }
        }


        response.msg = (
            f"Found {len(results)} "
            f"active events for the "
            f"depth/date query"
        )


        return response


    # =========================================================
    # CONSULTA 3
    # ASOCIACIONES
    # =========================================================

    def get_event_associations(
        self,
        identifier
    ):

        try:

            identifier = int(
                identifier
            )


        except (
            TypeError,
            ValueError
        ):

            return self._error(
                "Invalid identifier"
            )


        scenario = (
            self.sismolab
            .get_scenario()
        )


        event = (
            scenario
            .get_event_by_id(
                identifier
            )
        )


        if event is None:

            return self._error(
                "Event not found"
            )


        if (
            event.catalog_status
            ==
            CatalogStatus.DELETED
        ):

            return self._error(
                "Deleted events do not "
                "participate in associations"
            )


        # IMPORTANTE:
        #
        # Reutilizamos AssociationService.
        #
        # NO volvemos a programar aquí
        # las reglas de W, R, magnitud y tiempo.
        candidates = (
            self.association_service
            .get_candidates(
                event
            )
        )


        candidate_details = []


        for candidate in candidates:

            candidate_details.append({

                "event":
                    self._event_data(
                        candidate
                    ),

                "status":
                    candidate
                    .catalog_status
                    .value,

                "distance_km":
                    self.association_service
                    .calculate_distance(
                        candidate,
                        event
                    ),

                "time_difference_hours":
                    self.association_service
                    .calculate_time_difference_hours(
                        candidate,
                        event
                    )
            })


        # Mismo criterio determinista
        # que elegimos en punto 7:
        #
        # menor distancia,
        # luego menor identifier.
        candidate_details.sort(
            key=lambda item: (

                item[
                    "distance_km"
                ],

                item[
                    "event"
                ][
                    "identifier"
                ]
            )
        )


        # Referencia actualmente elegida
        # para este Event.
        chosen_association = (
            self.association_service
            .get_association_for_event(
                event
            )
        )


        chosen_reference = None


        if (
            chosen_association
            is not None
        ):

            reference_event = (
                chosen_association
                .get_reference_event()
            )


            chosen_reference = {

                "event":
                    self._event_data(
                        reference_event
                    ),

                "status":
                    reference_event
                    .catalog_status
                    .value,

                "distance_km":
                    self.association_service
                    .calculate_distance(
                        reference_event,
                        event
                    ),

                "time_difference_hours":
                    self.association_service
                    .calculate_time_difference_hours(
                        reference_event,
                        event
                    )
            }


        # Eventos que utilizan al Event
        # consultado como referencia.
        associations = (
            self.sismolab
            .get_associations()
        )


        referencing_events = []


        for association in associations:

            reference_event = (
                association
                .get_reference_event()
            )


            if (
                reference_event.identifier
                !=
                event.identifier
            ):

                continue


            aftershock_event = (
                association
                .get_aftershock_event()
            )


            referencing_events.append({

                "event":
                    self._event_data(
                        aftershock_event
                    ),

                "status":
                    aftershock_event
                    .catalog_status
                    .value
            })


        registry = (
            scenario
            .get_events_by_id()
        )


        response = DataAndMsgReturn()


        response.data = {

            "target_event":
                self._event_data(
                    event
                ),

            "target_status":
                event
                .catalog_status
                .value,

            "candidates":
                candidate_details,

            "chosen_reference":
                chosen_reference,

            "referencing_events":
                referencing_events,

            # Esta consulta NO necesita
            # recorrer el AVL.
            #
            # Usa el índice por ID y
            # las asociaciones porque debe
            # incluir también archivados.
            "examined_nodes":
                0,

            "auxiliary_events_examined":
                len(registry),

            "associations_examined":
                len(associations),

            "cost_analysis": {

                "worst_case":
                    "O(n + a)",

                "safe_pruning":
                    (
                        "This query does not "
                        "traverse the AVL. "
                        "It uses the ID registry "
                        "and association collection "
                        "because archived events must "
                        "also be considered. "
                        "Therefore AVL examined_nodes "
                        "is 0."
                    )
            }
        }


        response.msg = (
            f"Association information "
            f"calculated for event "
            f"{identifier}"
        )


        return response


    # =========================================================
    # CONSULTA 4
    # PRIORIDAD ALTA + ACCESO COSTOSO
    # =========================================================

    def get_high_priority_costly_access(
        self
    ):

        scenario = (
            self.sismolab
            .get_scenario()
        )


        access_limit = (
            scenario
            .get_access_limit()
        )


        avl_tree = (
            self.sismolab
            .get_avl_tree()
        )


        results = []

        examined_nodes = 0


        def visit(
            node,
            depth
        ):

            nonlocal examined_nodes


            if node is None:
                return


            examined_nodes += 1


            event = (
                node.get_event()
            )


            # K = (P, M, I)
            #
            # Si P < 3, todo el subárbol
            # izquierdo también tendrá
            # prioridad menor o igual.
            #
            # Entonces podemos descartarlo.
            if event.priority < 3:

                node.set_costly_access(
                    False
                )


                visit(
                    node.get_right(),
                    depth + 1
                )


                return


            # Prioridad alta = 3.
            #
            # Acceso costoso SOLO depende de:
            #
            # depth > L
            costly_access = (
                depth
                >
                access_limit
            )


            node.set_costly_access(
                costly_access
            )


            if costly_access:

                results.append({

                    "event":
                        self._event_data(
                            event
                        ),

                    "node_depth":
                        depth,

                    "access_limit":
                        access_limit,

                    # Para un Event existente:
                    #
                    # visitados = depth + 1
                    "search_visited_nodes":
                        depth + 1,

                    "costly_access":
                        True
                })


            visit(
                node.get_left(),
                depth + 1
            )


            visit(
                node.get_right(),
                depth + 1
            )


        visit(
            avl_tree.get_root(),
            0
        )


        response = DataAndMsgReturn()


        response.data = {

            "events":
                results,

            "access_limit":
                access_limit,

            "total_found":
                len(results),

            "examined_nodes":
                examined_nodes,

            "cost_analysis": {

                "worst_case":
                    "O(n)",

                "safe_pruning":
                    (
                        "Priority is the first "
                        "component of K. "
                        "If a visited node has P<3, "
                        "its entire left subtree can "
                        "be discarded because no key "
                        "there can have priority 3."
                    )
            }
        }


        response.msg = (
            f"Found {len(results)} "
            f"high-priority events "
            f"with costly access"
        )


        return response


    # =========================================================
    # COMPARACIÓN DEL AVL Y BST ACTUALES
    # =========================================================

    def compare_current_avl_bst(
        self,
        identifiers=None
    ):

        scenario = (
            self.sismolab
            .get_scenario()
        )


        avl_tree = (
            self.sismolab
            .get_avl_tree()
        )


        bst_tree = (
            self.sismolab
            .get_bst_tree()
        )


        # Si no se especifican IDs,
        # comparamos todos los activos.
        if identifiers is None:

            events = [

                node.get_event()

                for node
                in avl_tree.inorder()
            ]


        else:

            if not isinstance(
                identifiers,
                (
                    list,
                    tuple,
                    set
                )
            ):

                return self._error(
                    "identifiers must be "
                    "a collection or None"
                )


            events = []

            seen = set()


            for identifier in identifiers:

                try:

                    identifier = int(
                        identifier
                    )


                except (
                    TypeError,
                    ValueError
                ):

                    return self._error(
                        "All identifiers must "
                        "be valid integers"
                    )


                if identifier in seen:
                    continue


                seen.add(
                    identifier
                )


                event = (
                    scenario
                    .get_event_by_id(
                        identifier
                    )
                )


                if (
                    event is None
                    or
                    event.catalog_status
                    !=
                    CatalogStatus.ACTIVE
                ):

                    return self._error(
                        f"Identifier "
                        f"{identifier} "
                        f"is not an active event"
                    )


                events.append(
                    event
                )


        per_key = []

        avl_total = 0

        bst_total = 0


        for event in events:

            key = event.get_key()


            (
                avl_node,
                avl_comparisons
            ) = (
                avl_tree
                .search_with_comparisons(
                    key
                )
            )


            (
                bst_node,
                bst_comparisons
            ) = (
                bst_tree
                .search_with_comparisons(
                    key
                )
            )


            avl_total += (
                avl_comparisons
            )

            bst_total += (
                bst_comparisons
            )


            per_key.append({

                "identifier":
                    event.identifier,

                "key":
                    key,

                "avl_found":
                    avl_node
                    is not None,

                "bst_found":
                    bst_node
                    is not None,

                "avl_comparisons":
                    avl_comparisons,

                "bst_comparisons":
                    bst_comparisons
            })


        response = DataAndMsgReturn()


        response.data = {

            "event_count":
                len(events),

            "avl": {

                "height":
                    avl_tree.height(),

                "leaf_count":
                    avl_tree.leaf_count(),

                "search_comparisons":
                    avl_total
            },

            "bst": {

                "height":
                    bst_tree.height(),

                "leaf_count":
                    bst_tree.leaf_count(),

                "search_comparisons":
                    bst_total
            },

            "searches":
                per_key,

            # La consulta de comparación
            # examinó esta cantidad total
            # de nodos AVL durante las búsquedas.
            "examined_nodes":
                avl_total,

            "cost_analysis": {

                "avl_search":
                    (
                        "O(log n) when balanced; "
                        "while stress mode is active "
                        "the AVL may temporarily "
                        "degrade toward O(n)."
                    ),

                "bst_search":
                    (
                        "O(h), with worst case O(n)."
                    )
            }
        }


        response.msg = (
            "Current AVL and BST structures "
            "compared using the same keys"
        )


        return response


    # =========================================================
    # COMPARACIÓN CON DISTINTOS ÓRDENES DE INSERCIÓN
    # =========================================================

    def compare_insertion_orders(
        self
    ):

        scenario = (
            self.sismolab
            .get_scenario()
        )


        # El diccionario conserva el orden
        # en que se registraron los IDs.
        registration_order = [

            event

            for event
            in (
                scenario
                .get_events_by_id()
                .values()
            )

            if (
                event.catalog_status
                ==
                CatalogStatus.ACTIVE
            )
        ]


        ascending_order = sorted(
            registration_order,
            key=lambda event:
                event.get_key()
        )


        descending_order = list(
            reversed(
                ascending_order
            )
        )


        orders = {

            "registration_order":
                registration_order,

            "ascending_key":
                ascending_order,

            "descending_key":
                descending_order
        }


        results = {}

        total_avl_examined = 0


        # Construimos árboles TEMPORALES.
        #
        # No modificamos el escenario real.
        for (
            order_name,
            events
        ) in orders.items():


            temp_avl = AVLTree()

            temp_bst = BSTTree()


            for event in events:

                temp_avl.insert(
                    event,
                    rebalance=True
                )

                temp_bst.insert(
                    event
                )


            searches = []

            avl_total = 0

            bst_total = 0


            # Buscamos las MISMAS claves
            # en ambos árboles.
            for event in ascending_order:

                key = (
                    event.get_key()
                )


                (
                    avl_node,
                    avl_comparisons
                ) = (
                    temp_avl
                    .search_with_comparisons(
                        key
                    )
                )


                (
                    bst_node,
                    bst_comparisons
                ) = (
                    temp_bst
                    .search_with_comparisons(
                        key
                    )
                )


                avl_total += (
                    avl_comparisons
                )

                bst_total += (
                    bst_comparisons
                )


                searches.append({

                    "identifier":
                        event.identifier,

                    "key":
                        key,

                    "avl_found":
                        avl_node
                        is not None,

                    "bst_found":
                        bst_node
                        is not None,

                    "avl_comparisons":
                        avl_comparisons,

                    "bst_comparisons":
                        bst_comparisons
                })


            total_avl_examined += (
                avl_total
            )


            results[
                order_name
            ] = {

                "insertion_ids": [

                    event.identifier

                    for event
                    in events
                ],

                "avl": {

                    "height":
                        temp_avl.height(),

                    "leaf_count":
                        temp_avl.leaf_count(),

                    "search_comparisons":
                        avl_total
                },

                "bst": {

                    "height":
                        temp_bst.height(),

                    "leaf_count":
                        temp_bst.leaf_count(),

                    "search_comparisons":
                        bst_total
                },

                "searches":
                    searches,

                "examined_nodes":
                    avl_total
            }


        response = DataAndMsgReturn()


        response.data = {

            "event_count":
                len(
                    registration_order
                ),

            "orders":
                results,

            "examined_nodes":
                total_avl_examined,

            "cost_analysis": {

                "temporary_avl_build":
                    "O(n log n)",

                "temporary_bst_build":
                    (
                        "O(n^2) in the worst case. "
                        "Ascending K demonstrates "
                        "the classic BST degradation."
                    ),

                "purpose":
                    (
                        "Temporary trees are used "
                        "only for structural comparison. "
                        "The active AVL and BST are "
                        "not modified."
                    )
            }
        }


        response.msg = (
            "Insertion-order comparison "
            "completed successfully"
        )


        return response
