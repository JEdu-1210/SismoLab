from src.business.AssociationService import AssociationService
from src.business.PriorityService import PriorityService

from src.models.Returnings import DataAndMsgReturn
from src.models.Status import (
    AttentionStatus,
    CatalogStatus
)


class AuditService:

    # =========================================================
    # AUDITORÃA COMPLETA
    # =========================================================

    @staticmethod
    def verify_structure(
        sismolab
    ):

        response = DataAndMsgReturn()

        scenario = (
            sismolab.get_scenario()
        )

        avl_tree = (
            sismolab.get_avl_tree()
        )

        bst_tree = (
            sismolab.get_bst_tree()
        )

        registry = (
            scenario.get_events_by_id()
        )

        stress_mode = (
            scenario.is_stress_mode()
        )


        issues = []

        # IDs presentes en el AVL activo.
        active_ids = set()

        # Nodos físicos visitados.
        # Permite detectar ciclos o referencias repetidas.
        active_node_objects = set()

        # IDs de activo + histórico.
        # Sirve para detectar que una identidad
        # aparezca en más de un catálogo.
        global_catalog_ids = set()


        # =====================================================
        # 1. AUDITAR AVL ACTIVO
        # =====================================================

        calculated_height = (
            AuditService
            ._audit_avl_node(
                node=avl_tree.get_root(),
                expected_parent=None,

                min_key=None,
                max_key=None,

                expected_status=(
                    CatalogStatus.ACTIVE
                ),

                scenario=scenario,
                registry=registry,

                event_ids=active_ids,
                node_objects=(
                    active_node_objects
                ),

                global_catalog_ids=(
                    global_catalog_ids
                ),

                issues=issues,

                depth=0,

                stress_mode=stress_mode,

                validate_active_balance=True,
                validate_access=True
            )
        )


        # También verificamos que la altura
        # anunciada por el árbol corresponda
        # con la calculada desde cero.
        if (
            calculated_height
            !=
            avl_tree.height()
        ):

            AuditService._issue(
                issues,
                None,
                "METADATA_ERROR",
                (
                    "AVL tree height reports "
                    f"{avl_tree.height()} "
                    "but calculated height is "
                    f"{calculated_height}"
                )
            )


        # =====================================================
        # 2. AUDITAR BST COMPARATIVO
        # =====================================================

        bst_ids = set()


        AuditService._audit_bst_node(
            node=bst_tree.get_root(),
            expected_parent=None,

            min_key=None,
            max_key=None,

            registry=registry,

            event_ids=bst_ids,
            node_objects=set(),

            issues=issues
        )


        # Ambos árboles deben contener
        # exactamente los mismos Events activos.
        missing_in_bst = (
            active_ids
            -
            bst_ids
        )

        extra_in_bst = (
            bst_ids
            -
            active_ids
        )


        for identifier in sorted(
            missing_in_bst
        ):

            AuditService._issue(
                issues,
                identifier,
                "REFERENCE_ERROR",
                (
                    "Active event exists in AVL "
                    "but is missing from BST"
                )
            )


        for identifier in sorted(
            extra_in_bst
        ):

            AuditService._issue(
                issues,
                identifier,
                "REFERENCE_ERROR",
                (
                    "BST contains an event "
                    "that is not present "
                    "in the active AVL"
                )
            )


        # =====================================================
        # 3. AUDITAR HISTÓRICO
        # =====================================================

        archived_ids = set()

        archived_node_objects = set()


        for root in (
            sismolab
            .get_history()
            .get_archived_roots()
        ):

            AuditService._audit_avl_node(
                node=root,
                expected_parent=None,

                min_key=None,
                max_key=None,

                expected_status=(
                    CatalogStatus.ARCHIVED
                ),

                scenario=scenario,
                registry=registry,

                event_ids=archived_ids,

                node_objects=(
                    archived_node_objects
                ),

                global_catalog_ids=(
                    global_catalog_ids
                ),

                issues=issues,

                depth=0,

                stress_mode=stress_mode,

                # Histórico debe conservar
                # orden y metadatos,
                # pero no tiene que obedecer
                # el balance del AVL activo.
                validate_active_balance=False,

                validate_access=False
            )


        # =====================================================
        # 4. ELIMINADOS / REGISTRO GLOBAL
        # =====================================================

        deleted_ids = set()


        for (
            identifier,
            event
        ) in registry.items():


            if (
                event.catalog_status
                ==
                CatalogStatus.DELETED
            ):

                deleted_ids.add(
                    identifier
                )


                if (
                    identifier
                    in
                    global_catalog_ids
                ):

                    AuditService._issue(
                        issues,
                        identifier,
                        "DUPLICATE_ID",
                        (
                            "Deleted identifier "
                            "also appears in "
                            "active/history topology"
                        )
                    )


                global_catalog_ids.add(
                    identifier
                )


            elif (
                event.catalog_status
                ==
                CatalogStatus.ACTIVE

                and

                identifier
                not in
                active_ids
            ):

                AuditService._issue(
                    issues,
                    identifier,
                    "REFERENCE_ERROR",
                    (
                        "Registry marks event ACTIVE "
                        "but it is not present "
                        "in the active AVL"
                    )
                )


            elif (
                event.catalog_status
                ==
                CatalogStatus.ARCHIVED

                and

                identifier
                not in
                archived_ids
            ):

                AuditService._issue(
                    issues,
                    identifier,
                    "REFERENCE_ERROR",
                    (
                        "Registry marks event ARCHIVED "
                        "but it is not present "
                        "in History"
                    )
                )


        # =====================================================
        # 5. IDS RETIRADOS
        # =====================================================

        retired_ids = (
            sismolab.get_retired_ids()
        )


        for identifier in sorted(
            deleted_ids
            -
            retired_ids
        ):

            AuditService._issue(
                issues,
                identifier,
                "REFERENCE_ERROR",
                (
                    "Deleted event identifier "
                    "is missing from retired IDs"
                )
            )


        for identifier in sorted(
            retired_ids
            -
            deleted_ids
        ):

            AuditService._issue(
                issues,
                identifier,
                "REFERENCE_ERROR",
                (
                    "Retired identifier does not "
                    "correspond to a DELETED event"
                )
            )


        # =====================================================
        # 6. ASOCIACIONES
        # =====================================================

        AuditService._audit_associations(
            sismolab,
            issues
        )


        # =====================================================
        # RESULTADO
        # =====================================================

        critical = [

            item

            for item in issues

            if (
                item["severity"]
                ==
                "ERROR"
            )
        ]


        expected_unbalances = [

            item

            for item in issues

            if (
                item["type"]
                ==
                "EXPECTED_UNBALANCE"
            )
        ]


        event_reports = (
            AuditService
            ._group_event_reports(
                issues
            )
        )


        global_issues = [

            item

            for item in issues

            if (
                item["event_id"]
                is None
            )
        ]


        response.data = {

            "is_valid":
                len(critical) == 0,

            "is_stress_mode":
                stress_mode,

            "active_events_examined":
                len(active_ids),

            "archived_events_examined":
                len(archived_ids),

            "bst_events_examined":
                len(bst_ids),

            "total_observations":
                len(issues),

            "critical_inconsistencies":
                len(critical),

            "expected_unbalances":
                len(expected_unbalances),

            # Reporte por Event inconsistente.
            "event_reports":
                event_reports,

            # Problemas generales sin un
            # identificador concreto.
            "global_issues":
                global_issues,

            # Lista plana útil para GUI.
            "issues":
                issues
        }


        if len(critical) == 0:

            response.msg = (
                "Structure audit "
                "completed successfully"
            )

        else:

            response.msg = (
                "Structure audit found "
                f"{len(critical)} "
                "critical inconsistency(ies)"
            )


        return response


    # =========================================================
    # INDICADORES DEL SISTEMA
    # =========================================================

    @staticmethod
    def get_indicators(
        sismolab
    ):

        response = DataAndMsgReturn()

        avl_tree = (
            sismolab.get_avl_tree()
        )

        bst_tree = (
            sismolab.get_bst_tree()
        )

        history = (
            sismolab.get_history()
        )

        metrics = (
            sismolab
            .get_metrics()
            .get_summary()
        )


        active_nodes = (
            avl_tree.inorder()
        )


        priority_counts = {
            "1": 0,
            "2": 0,
            "3": 0
        }


        pending = 0

        costly = 0


        for node in active_nodes:

            event = (
                node.get_event()
            )


            priority_key = str(
                event.priority
            )


            priority_counts[
                priority_key
            ] = (
                priority_counts.get(
                    priority_key,
                    0
                )
                +
                1
            )


            if (
                event.attention_status
                ==
                AttentionStatus.PENDING
            ):

                pending += 1


            if (
                node.is_costly_access()
            ):

                costly += 1


        response.data = {

            # ---------------------------------------------
            # CATÃLOGO
            # ---------------------------------------------

            "catalog": {

                "active_events":
                    len(active_nodes),

                "historical_events":
                    history.count_events(),

                "retired_identifiers":
                    len(
                        sismolab
                        .get_retired_ids()
                    )
            },


            # ---------------------------------------------
            # AVL
            # ---------------------------------------------

            "avl": {

                "height":
                    avl_tree.height(),

                "leaf_count":
                    avl_tree.leaf_count(),

                "inorder":
                    AuditService
                    ._traversal_data(
                        avl_tree.inorder()
                    ),

                "preorder":
                    AuditService
                    ._traversal_data(
                        avl_tree.preorder()
                    ),

                "postorder":
                    AuditService
                    ._traversal_data(
                        avl_tree.postorder()
                    ),

                "breadth_first":
                    AuditService
                    ._traversal_data(
                        avl_tree.breadth_first()
                    )
            },


            # ---------------------------------------------
            # BST COMPARATIVO
            # ---------------------------------------------

            "bst": {

                "height":
                    bst_tree.height(),

                "leaf_count":
                    bst_tree.leaf_count()
            },


            # ---------------------------------------------
            # EVENTOS
            # ---------------------------------------------

            "events": {

                "by_priority":
                    priority_counts,

                "pending_attention":
                    pending,

                "costly_access":
                    costly
            },


            # ---------------------------------------------
            # CONTADORES
            # ---------------------------------------------

            "metrics":
                metrics,


            # Dato útil para GUI.
            "queue_size":
                sismolab
                .get_report_queue()
                .size()
        }


        response.msg = (
            "System indicators "
            "calculated successfully"
        )


        return response


    # =========================================================
    # AUDITAR UN NODO AVL
    # =========================================================

    @staticmethod
    def _audit_avl_node(
        node,
        expected_parent,
        min_key,
        max_key,
        expected_status,
        scenario,
        registry,
        event_ids,
        node_objects,
        global_catalog_ids,
        issues,
        depth,
        stress_mode,
        validate_active_balance,
        validate_access
    ):

        # Ãrbol vacÃ­o = -1.
        if node is None:

            return -1


        object_id = id(
            node
        )


        # Evita recursión infinita en
        # caso de ciclo o nodo compartido.
        if (
            object_id
            in
            node_objects
        ):

            event_id = None


            try:

                event_id = (
                    node
                    .get_event()
                    .identifier
                )

            except Exception:
                pass


            AuditService._issue(
                issues,
                event_id,
                "REFERENCE_ERROR",
                (
                    "Cycle or repeated node "
                    "reference detected"
                )
            )


            return -1


        node_objects.add(
            object_id
        )


        event = (
            node.get_event()
        )

        identifier = (
            event.identifier
        )

        key = (
            event.get_key()
        )


        # =====================================================
        # UNICIDAD
        # =====================================================

        if identifier in event_ids:

            AuditService._issue(
                issues,
                identifier,
                "DUPLICATE_ID",
                (
                    "Identifier appears more than "
                    "once in the same topology"
                )
            )

        else:

            event_ids.add(
                identifier
            )


        # Activo e histórico tampoco
        # pueden repetir identidad.
        if (
            identifier
            in
            global_catalog_ids
        ):

            AuditService._issue(
                issues,
                identifier,
                "DUPLICATE_ID",
                (
                    "Identifier appears in more "
                    "than one catalog topology"
                )
            )

        else:

            global_catalog_ids.add(
                identifier
            )


        # =====================================================
        # REFERENCIA AL PADRE
        # =====================================================

        if (
            node.get_parent()
            is not
            expected_parent
        ):

            AuditService._issue(
                issues,
                identifier,
                "REFERENCE_ERROR",
                (
                    "Parent reference "
                    "is inconsistent"
                )
            )


        # =====================================================
        # REGISTRO DEL ESCENARIO
        # =====================================================

        registered_event = (
            registry.get(
                identifier
            )
        )


        if registered_event is None:

            AuditService._issue(
                issues,
                identifier,
                "REFERENCE_ERROR",
                (
                    "Event is missing from "
                    "Scenario registry"
                )
            )


        elif (
            registered_event
            is not
            event
        ):

            AuditService._issue(
                issues,
                identifier,
                "REFERENCE_ERROR",
                (
                    "Tree node and Scenario registry "
                    "do not reference the same "
                    "Event object"
                )
            )


        # =====================================================
        # ESTADO DEL CATÃLOGO
        # =====================================================

        if (
            event.catalog_status
            !=
            expected_status
        ):

            AuditService._issue(
                issues,
                identifier,
                "STATUS_ERROR",
                (
                    "Expected catalog status "
                    f"{expected_status.value}, "
                    "found "
                    f"{event.catalog_status.value}"
                )
            )


        # =====================================================
        # ORDEN GLOBAL POR K
        # =====================================================

        if (
            min_key is not None
            and
            key <= min_key
        ):

            AuditService._issue(
                issues,
                identifier,
                "ORDER_ERROR",
                (
                    "Global K order violation: "
                    f"{key} <= "
                    f"lower bound {min_key}"
                )
            )


        if (
            max_key is not None
            and
            key >= max_key
        ):

            AuditService._issue(
                issues,
                identifier,
                "ORDER_ERROR",
                (
                    "Global K order violation: "
                    f"{key} >= "
                    f"upper bound {max_key}"
                )
            )


        # También comprobamos datos derivados
        # como prioridad y zona poblada.
        AuditService._audit_event_data(
            event,
            scenario,
            issues
        )


        # =====================================================
        # RECURSIÓN
        # =====================================================

        left_height = (
            AuditService
            ._audit_avl_node(
                node.get_left(),
                node,

                min_key,
                key,

                expected_status,

                scenario,
                registry,

                event_ids,
                node_objects,
                global_catalog_ids,

                issues,

                depth + 1,

                stress_mode,

                validate_active_balance,
                validate_access
            )
        )


        right_height = (
            AuditService
            ._audit_avl_node(
                node.get_right(),
                node,

                key,
                max_key,

                expected_status,

                scenario,
                registry,

                event_ids,
                node_objects,
                global_catalog_ids,

                issues,

                depth + 1,

                stress_mode,

                validate_active_balance,
                validate_access
            )
        )


        # =====================================================
        # ALTURA REAL
        # =====================================================

        real_height = (
            1
            +
            max(
                left_height,
                right_height
            )
        )


        balance_factor = (
            left_height
            -
            right_height
        )


        if (
            node.get_height()
            !=
            real_height
        ):

            AuditService._issue(
                issues,
                identifier,
                "METADATA_ERROR",
                (
                    "Stored height "
                    f"{node.get_height()} "
                    "differs from recalculated "
                    f"height {real_height}"
                )
            )


        # =====================================================
        # FACTOR DE BALANCE
        # =====================================================

        if (
            validate_active_balance
            and
            abs(
                balance_factor
            )
            >
            1
        ):

            # En estrés el desbalance es esperado,
            # por sí mismo NO invalida la estructura.
            if stress_mode:

                AuditService._issue(
                    issues,
                    identifier,
                    "EXPECTED_UNBALANCE",
                    (
                        "Balance factor "
                        f"{balance_factor} "
                        "is allowed temporarily "
                        "in stress mode"
                    ),
                    severity="WARNING"
                )


            # En modo normal sí es error.
            else:

                AuditService._issue(
                    issues,
                    identifier,
                    "BALANCE_ERROR",
                    (
                        "Balance factor "
                        f"{balance_factor} "
                        "is invalid in normal mode"
                    )
                )


        # =====================================================
        # MARCA DE ACCESO COSTOSO
        # =====================================================

        if validate_access:

            expected_costly = (

                event.priority == 3

                and

                depth
                >
                scenario.get_access_limit()
            )


            if (
                node.is_costly_access()
                !=
                expected_costly
            ):

                AuditService._issue(
                    issues,
                    identifier,
                    "METADATA_ERROR",
                    (
                        "Costly-access mark is "
                        f"{node.is_costly_access()} "
                        "but expected "
                        f"{expected_costly}"
                    )
                )


        return real_height


    # =========================================================
    # AUDITAR BST
    # =========================================================

    @staticmethod
    def _audit_bst_node(
        node,
        expected_parent,
        min_key,
        max_key,
        registry,
        event_ids,
        node_objects,
        issues
    ):

        if node is None:

            return


        object_id = id(
            node
        )


        if (
            object_id
            in
            node_objects
        ):

            identifier = None


            try:

                identifier = (
                    node
                    .get_event()
                    .identifier
                )

            except Exception:
                pass


            AuditService._issue(
                issues,
                identifier,
                "REFERENCE_ERROR",
                (
                    "Cycle or repeated node "
                    "reference detected in BST"
                )
            )


            return


        node_objects.add(
            object_id
        )


        event = (
            node.get_event()
        )

        identifier = (
            event.identifier
        )

        key = (
            event.get_key()
        )


        if identifier in event_ids:

            AuditService._issue(
                issues,
                identifier,
                "DUPLICATE_ID",
                (
                    "Identifier appears more "
                    "than once in BST"
                )
            )

        else:

            event_ids.add(
                identifier
            )


        if (
            node.get_parent()
            is not
            expected_parent
        ):

            AuditService._issue(
                issues,
                identifier,
                "REFERENCE_ERROR",
                (
                    "BST parent reference "
                    "is inconsistent"
                )
            )


        registered_event = (
            registry.get(
                identifier
            )
        )


        if (
            registered_event is None
            or
            registered_event
            is not
            event
        ):

            AuditService._issue(
                issues,
                identifier,
                "REFERENCE_ERROR",
                (
                    "BST event reference does "
                    "not match Scenario registry"
                )
            )


        if (
            event.catalog_status
            !=
            CatalogStatus.ACTIVE
        ):

            AuditService._issue(
                issues,
                identifier,
                "STATUS_ERROR",
                (
                    "BST contains a "
                    "non-active event"
                )
            )


        # Orden GLOBAL.
        if (
            min_key is not None
            and
            key <= min_key
        ):

            AuditService._issue(
                issues,
                identifier,
                "ORDER_ERROR",
                (
                    "BST global K violation: "
                    f"{key} <= "
                    f"lower bound {min_key}"
                )
            )


        if (
            max_key is not None
            and
            key >= max_key
        ):

            AuditService._issue(
                issues,
                identifier,
                "ORDER_ERROR",
                (
                    "BST global K violation: "
                    f"{key} >= "
                    f"upper bound {max_key}"
                )
            )


        AuditService._audit_bst_node(
            node.get_left(),
            node,
            min_key,
            key,
            registry,
            event_ids,
            node_objects,
            issues
        )


        AuditService._audit_bst_node(
            node.get_right(),
            node,
            key,
            max_key,
            registry,
            event_ids,
            node_objects,
            issues
        )


    # =========================================================
    # DATOS DERIVADOS DEL EVENT
    # =========================================================

    @staticmethod
    def _audit_event_data(
        event,
        scenario,
        issues
    ):

        identifier = (
            event.identifier
        )


        calculated_populated = (
            scenario
            .is_point_in_populated_zone(
                event.x,
                event.y
            )
        )


        if (
            event.is_populated_zone
            !=
            calculated_populated
        ):

            AuditService._issue(
                issues,
                identifier,
                "METADATA_ERROR",
                (
                    "Stored populated-zone value "
                    f"{event.is_populated_zone} "
                    "differs from calculated "
                    f"value {calculated_populated}"
                )
            )


        calculated_priority = (
            PriorityService
            .calculate_priority(
                event.magnitude,
                event.depth,
                calculated_populated
            )
        )


        if (
            event.priority
            !=
            calculated_priority
        ):

            AuditService._issue(
                issues,
                identifier,
                "METADATA_ERROR",
                (
                    "Stored priority "
                    f"{event.priority} "
                    "differs from calculated "
                    f"priority "
                    f"{calculated_priority}"
                )
            )


        # Todas las estaciones aceptadas
        # deben seguir existiendo.
        for station_name in (
            event.accepted_stations
        ):

            if (
                scenario
                .get_station_by_name(
                    station_name
                )
                is None
            ):

                AuditService._issue(
                    issues,
                    identifier,
                    "REFERENCE_ERROR",
                    (
                        "Accepted station "
                        f"'{station_name}' "
                        "does not exist "
                        "in Scenario"
                    )
                )


    # =========================================================
    # AUDITAR ASOCIACIONES
    # =========================================================

    @staticmethod
    def _audit_associations(
        sismolab,
        issues
    ):

        scenario = (
            sismolab.get_scenario()
        )

        registry = (
            scenario.get_events_by_id()
        )


        association_service = (
            AssociationService(
                sismolab
            )
        )


        # B -> ID de su referencia.
        actual_by_aftershock = {}


        for association in (
            sismolab.get_associations()
        ):

            reference = (
                association
                .get_reference_event()
            )

            aftershock = (
                association
                .get_aftershock_event()
            )


            aftershock_id = (
                aftershock.identifier
            )


            # Un B solamente puede tener
            # una referencia elegida.
            if (
                aftershock_id
                in
                actual_by_aftershock
            ):

                AuditService._issue(
                    issues,
                    aftershock_id,
                    "ASSOCIATION_ERROR",
                    (
                        "Event has more than "
                        "one chosen reference"
                    )
                )


            actual_by_aftershock[
                aftershock_id
            ] = (
                reference.identifier
            )


            # Las asociaciones deben usar
            # las identidades registradas.
            if (
                registry.get(
                    reference.identifier
                )
                is not
                reference
            ):

                AuditService._issue(
                    issues,
                    reference.identifier,
                    "REFERENCE_ERROR",
                    (
                        "Association reference "
                        "Event is not the "
                        "registered Event object"
                    )
                )


            if (
                registry.get(
                    aftershock.identifier
                )
                is not
                aftershock
            ):

                AuditService._issue(
                    issues,
                    aftershock.identifier,
                    "REFERENCE_ERROR",
                    (
                        "Association aftershock "
                        "Event is not the "
                        "registered Event object"
                    )
                )


            if (
                reference.catalog_status
                ==
                CatalogStatus.DELETED

                or

                aftershock.catalog_status
                ==
                CatalogStatus.DELETED
            ):

                AuditService._issue(
                    issues,
                    aftershock.identifier,
                    "ASSOCIATION_ERROR",
                    (
                        "Deleted events cannot "
                        "participate in associations"
                    )
                )


            elif not (
                association_service
                .is_candidate(
                    reference,
                    aftershock
                )
            ):

                AuditService._issue(
                    issues,
                    aftershock.identifier,
                    "ASSOCIATION_ERROR",
                    (
                        "Stored reference does "
                        "not satisfy candidate rules"
                    )
                )


        # -----------------------------------------------------
        # Verificar también asociaciones AUSENTES.
        #
        # No basta comprobar solamente
        # las asociaciones que sí existen.
        # -----------------------------------------------------

        for event in (
            registry.values()
        ):

            if (
                event.catalog_status
                not in
                (
                    CatalogStatus.ACTIVE,
                    CatalogStatus.ARCHIVED
                )
            ):

                continue


            expected_reference = (
                association_service
                .choose_reference(
                    event
                )
            )


            actual_reference_id = (
                actual_by_aftershock.get(
                    event.identifier
                )
            )


            expected_reference_id = (

                expected_reference.identifier

                if (
                    expected_reference
                    is not None
                )

                else None
            )


            if (
                actual_reference_id
                !=
                expected_reference_id
            ):

                AuditService._issue(
                    issues,
                    event.identifier,
                    "ASSOCIATION_ERROR",
                    (
                        "Chosen reference is "
                        f"{actual_reference_id}, "
                        "expected deterministic "
                        "reference is "
                        f"{expected_reference_id}"
                    )
                )


    # =========================================================
    # CREAR OBSERVACIÓN
    # =========================================================

    @staticmethod
    def _issue(
        issues,
        event_id,
        issue_type,
        description,
        severity="ERROR"
    ):

        issues.append({

            "event_id":
                event_id,

            "type":
                issue_type,

            "severity":
                severity,

            "description":
                description
        })


    # =========================================================
    # AGRUPAR REPORTE POR EVENT
    # =========================================================

    @staticmethod
    def _group_event_reports(
        issues
    ):

        grouped = {}


        for issue in issues:

            identifier = (
                issue.get(
                    "event_id"
                )
            )


            if identifier is None:
                continue


            if identifier not in grouped:

                grouped[
                    identifier
                ] = []


            grouped[
                identifier
            ].append({

                "type":
                    issue["type"],

                "severity":
                    issue["severity"],

                "description":
                    issue["description"]
            })


        return [

            {
                "event_id":
                    identifier,

                "issues":
                    grouped[
                        identifier
                    ]
            }

            for identifier
            in sorted(
                grouped
            )
        ]


    # =========================================================
    # CONVERTIR RECORRIDO PARA GUI
    # =========================================================

    @staticmethod
    def _traversal_data(
        nodes
    ):

        return [

            {
                "identifier":
                    node
                    .get_event()
                    .identifier,

                "key":
                    node.get_key()
            }

            for node
            in nodes
        ]
