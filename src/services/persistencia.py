from datetime import datetime
from math import isfinite

from src.models.Event import Event
from src.models.Metrics import Metrics
from src.models.Report import Report
from src.models.Scenario import Scenario
from src.models.SismoLab import SismoLab
from src.models.Station import Station
from src.models.Status import (
    AttentionStatus,
    CatalogStatus
)
from src.models.Zone import Zone
from src.models.Returnings import DataAndMsgReturn

from src.business.AccessService import AccessService
from src.business.AssociationService import AssociationService
from src.business.PriorityService import PriorityService

from src.structures.AVLNode import AVLNode
from src.structures.BSTNode import BSTNode

from src.utils.Files import FilesUtils


class PersistenceService:

    SCHEMA_NAME = "SismoLabAVL"
    SCHEMA_VERSION = 1


    # =========================================================
    # GUARDADO ESTRUCTURAL
    # =========================================================

    @staticmethod
    def save_structural(
        filepath,
        sismolab
    ):

        response = DataAndMsgReturn()


        if (
            not isinstance(filepath, str)
            or filepath.strip() == ""
        ):

            response.ok = False
            response.error = (
                "A valid output path is required"
            )

            return response


        try:

            payload = {

                "schema":
                    PersistenceService.SCHEMA_NAME,

                "schema_version":
                    PersistenceService.SCHEMA_VERSION,

                "state":
                    PersistenceService.export_state(
                        sismolab
                    )
            }


            write_result = (
                FilesUtils.write_json(
                    filepath,
                    payload
                )
            )


            if not write_result.ok:

                response.ok = False
                response.error = (
                    write_result.error
                )

                return response


            response.data = {

                "filepath":
                    filepath,

                "schema_version":
                    PersistenceService.SCHEMA_VERSION
            }


            response.msg = (
                "Structural state saved successfully"
            )


            return response


        except Exception as exc:

            response.ok = False

            response.error = (
                "Could not save structural state: "
                f"{exc}"
            )

            return response


    # =========================================================
    # EXPORTAR ESTADO A MEMORIA
    #
    # Este mÃ©todo tambiÃ©n serÃ¡ utilizado
    # despuÃ©s por Undo y VersionService.
    # =========================================================

    @staticmethod
    def export_state(
        sismolab
    ):

        scenario = (
            sismolab.get_scenario()
        )

        avl_tree = (
            sismolab.get_avl_tree()
        )

        bst_tree = (
            sismolab.get_bst_tree()
        )

        history = (
            sismolab.get_history()
        )


        all_events = (
            scenario.get_events_by_id()
        )


        # Los eventos eliminados ya no se
        # encuentran dentro de AVL/BST/History,
        # por eso debemos guardarlos aparte.
        deleted_events = [

            event.to_dict()

            for event
            in all_events.values()

            if (
                event.catalog_status
                ==
                CatalogStatus.DELETED
            )
        ]


        state = {

            # -------------------------------------------------
            # ESCENARIO
            # -------------------------------------------------

            "scenario": {

                "simulation_clock":
                    PersistenceService
                    ._datetime_to_text(
                        scenario
                        .get_simulation_clock()
                    ),

                "w_hours":
                    scenario.get_w_hours(),

                "r_km":
                    scenario.get_r_km(),

                "access_limit":
                    scenario.get_access_limit(),

                "archive_age_hours":
                    scenario
                    .get_archive_age_hours(),

                "stress_mode":
                    scenario.is_stress_mode(),

                "zones": [

                    zone.to_dict()

                    for zone
                    in scenario.get_zones()
                ],

                "stations": [

                    station.to_dict()

                    for station
                    in scenario.get_stations()
                ]
            },


            # -------------------------------------------------
            # TOPOLOGÃA REAL DEL AVL ACTIVO
            # -------------------------------------------------

            "active_avl_topology":
                PersistenceService
                ._serialize_avl_node(
                    avl_tree.get_root(),
                    include_costly_access=True
                ),


            # -------------------------------------------------
            # TOPOLOGÃA DEL BST COMPARATIVO
            # -------------------------------------------------

            "comparison_bst_topology":
                PersistenceService
                ._serialize_bst_node(
                    bst_tree.get_root()
                ),


            # -------------------------------------------------
            # HISTÃ“RICO
            # -------------------------------------------------

            "history_topologies": [

                PersistenceService
                ._serialize_avl_node(
                    root,
                    include_costly_access=False
                )

                for root
                in history.get_archived_roots()
            ],


            # -------------------------------------------------
            # ELIMINADOS
            # -------------------------------------------------

            "deleted_events":
                deleted_events,


            "retired_ids":
                sorted(
                    sismolab.get_retired_ids()
                ),


            # -------------------------------------------------
            # ASOCIACIONES
            # -------------------------------------------------

            "associations": [

                {
                    "reference_event_id":
                        association
                        .get_reference_event()
                        .identifier,

                    "aftershock_event_id":
                        association
                        .get_aftershock_event()
                        .identifier
                }

                for association
                in sismolab.get_associations()
            ],


            # -------------------------------------------------
            # COLA FIFO
            # -------------------------------------------------

            "report_queue": [

                PersistenceService
                ._serialize_report(
                    report
                )

                for report
                in (
                    sismolab
                    .get_report_queue()
                    .get_reports()
                )
            ],


            # -------------------------------------------------
            # MÃ‰TRICAS
            # -------------------------------------------------

            "metrics":
                sismolab
                .get_metrics()
                .get_summary()
        }


        return state


    # =========================================================
    # CARGA POR INSERCIONES
    # =========================================================

    @staticmethod
    def load_by_insertions(
        filepath,
        sismolab,
        bst_class=None
    ):

        response = DataAndMsgReturn()


        read_result = (
            FilesUtils.read_json(
                filepath
            )
        )


        if (
            not read_result.ok
            or read_result.data is None
        ):

            response.ok = False

            response.error = (
                read_result.error
                or
                read_result.msg
                or
                "Could not read insertion file"
            )

            return response


        data = read_result.data


        # Permitimos:

        # [
        #   {...},
        #   {...}
        # ]

        # o:

        # {
        #   "events": [...]
        # }

        if isinstance(
            data,
            list
        ):

            event_list = data


        elif isinstance(
            data,
            dict
        ):

            event_list = (
                data.get(
                    "events"
                )
            )


            # Compatibilidad con formato anterior.
            if event_list is None:

                event_list = (
                    data.get(
                        "active_tree_events"
                    )
                )


        else:

            event_list = None


        if not isinstance(
            event_list,
            list
        ):

            response.ok = False

            response.error = (
                "Insertion file must contain "
                "an event list under 'events'"
            )

            return response


        try:

            # -------------------------------------------------
            # IMPORTANTE:
            #
            # Construimos todo en un SismoLab TEMPORAL.
            #
            # TodavÃ­a no tocamos el sistema real.
            # -------------------------------------------------

            temp_scenario = (
                PersistenceService
                ._clone_scenario_configuration(
                    sismolab.get_scenario()
                )
            )


            temp_lab = SismoLab(
                temp_scenario
            )

            temp_lab.get_avl_tree().clear_rotation_log()

            seen_ids = set()


            for index, event_data in enumerate(
                event_list
            ):

                if not isinstance(
                    event_data,
                    dict
                ):

                    raise ValueError(
                        f"Event at position "
                        f"{index} is not an object"
                    )


                identifier = (
                    PersistenceService
                    ._strict_identifier(
                        event_data.get(
                            "identifier"
                        )
                    )
                )


                # IDs repetidos invalidan
                # completamente el archivo.
                if identifier in seen_ids:

                    raise ValueError(
                        "Duplicate identifier "
                        "in insertion sequence: "
                        f"{identifier}"
                    )


                seen_ids.add(
                    identifier
                )


                event = (
                    PersistenceService
                    ._event_from_dict(
                        event_data,
                        temp_scenario,
                        expected_status=(
                            CatalogStatus.ACTIVE
                        ),
                        default_status=(
                            CatalogStatus.ACTIVE
                        )
                    )
                )


                if not (
                    temp_scenario
                    .register_event(
                        event
                    )
                ):

                    raise ValueError(
                        f"Identifier "
                        f"{identifier} "
                        f"could not be registered"
                    )


                # AVL con balanceo ACTIVO.
                inserted_avl = (
                    temp_lab
                    .get_avl_tree()
                    .insert(
                        event,
                        rebalance=True
                    )
                )


                if inserted_avl is None:

                    raise ValueError(
                        f"Could not insert "
                        f"identifier "
                        f"{identifier} "
                        f"in AVL"
                    )


                # BST sin balanceo.
                inserted_bst = (
                    temp_lab
                    .get_bst_tree()
                    .insert(
                        event
                    )
                )


                if inserted_bst is None:

                    raise ValueError(
                        f"Could not insert "
                        f"identifier "
                        f"{identifier} "
                        f"in BST"
                    )

            temp_lab.get_metrics().register_rotation_log(
                temp_lab
                .get_avl_tree()
                .get_rotation_log()
            )
            
            # La nueva colecciÃ³n puede generar
            # asociaciones.
            AssociationService(
                temp_lab
            ).recalculate_all()


            # Actualizar marcas de acceso.
            AccessService(
                temp_lab
            ).update_access_marks()


            # -------------------------------------------------
            # SOLO AHORA sustituimos el estado real.
            # -------------------------------------------------

            PersistenceService \
                ._commit_operational_state(
                    sismolab,
                    temp_lab
                )


            avl_tree = (
                sismolab.get_avl_tree()
            )

            bst_tree = (
                sismolab.get_bst_tree()
            )


            avl_root = (
                avl_tree.get_root()
            )

            bst_root = (
                bst_tree.get_root()
            )


            response.data = {

                "loaded_events":
                    len(event_list),

                "avl": {

                    "root_id":
                        (
                            avl_root
                            .get_event()
                            .identifier
                            if avl_root
                            else None
                        ),

                    "root_key":
                        (
                            avl_root
                            .get_key()
                            if avl_root
                            else None
                        ),

                    "height":
                        avl_tree.height(),

                    "max_depth":
                        avl_tree.height(),

                    "leaf_count":
                        avl_tree.leaf_count()
                },


                "bst": {

                    "root_id":
                        (
                            bst_root
                            .get_event()
                            .identifier
                            if bst_root
                            else None
                        ),

                    "root_key":
                        (
                            bst_root
                            .get_key()
                            if bst_root
                            else None
                        ),

                    "height":
                        bst_tree.height(),

                    "max_depth":
                        bst_tree.height(),

                    "leaf_count":
                        bst_tree.leaf_count()
                }
            }


            response.msg = (
                "Insertion load "
                "completed successfully"
            )


            return response


        except Exception as exc:

            response.ok = False

            response.error = (
                "Insertion load rejected. "
                "Current scenario was not modified. "
                f"Reason: {exc}"
            )


            return response


    # =========================================================
    # CARGA POR TOPOLOGÃA
    # =========================================================

    @staticmethod
    def load_by_topology(
        filepath,
        sismolab
    ):

        response = DataAndMsgReturn()


        read_result = (
            FilesUtils.read_json(
                filepath
            )
        )


        if (
            not read_result.ok
            or read_result.data is None
        ):

            response.ok = False

            response.error = (
                read_result.error
                or
                read_result.msg
                or
                "Could not read topology file"
            )

            return response


        payload = (
            read_result.data
        )


        if not isinstance(
            payload,
            dict
        ):

            response.ok = False

            response.error = (
                "Topology file must "
                "contain a JSON object"
            )

            return response


        # Archivo generado por save_structural().
        if "state" in payload:

            schema = payload.get(
                "schema"
            )


            if (
                schema is not None
                and
                schema
                !=
                PersistenceService.SCHEMA_NAME
            ):

                response.ok = False
                response.error = (
                    "Unknown persistence schema"
                )

                return response


            version = payload.get(
                "schema_version",
                PersistenceService.SCHEMA_VERSION
            )


            if (
                version
                !=
                PersistenceService.SCHEMA_VERSION
            ):

                response.ok = False

                response.error = (
                    "Unsupported schema version: "
                    f"{version}"
                )

                return response


            state = payload.get(
                "state"
            )


        # TambiÃ©n permitimos recibir
        # directamente el objeto state.
        else:

            state = payload


        return (
            PersistenceService
            .apply_state(
                sismolab,
                state,
                success_message=(
                    "Topology validated "
                    "and loaded successfully"
                )
            )
        )


    # Nombre antiguo.
    #
    # Lo dejamos para no romper
    # cÃ³digo previo del compaÃ±ero.
    @staticmethod
    def validate_and_load_topology(
        filepath,
        sismolab
    ):

        return (
            PersistenceService
            .load_by_topology(
                filepath,
                sismolab
            )
        )


    # =========================================================
    # APLICAR UN ESTADO EN MEMORIA
    #
    # Muy importante para:
    # - carga topolÃ³gica
    # - Undo
    # - versiones
    # =========================================================

    @staticmethod
    def apply_state(
        sismolab,
        state,
        success_message=(
            "State restored successfully"
        )
    ):

        response = DataAndMsgReturn()


        try:

            # Primero construir y validar TODO.
            temp_lab = (
                PersistenceService
                ._build_lab_from_state(
                    state
                )
            )


            # Solo cuando TODO funcionÃ³:
            PersistenceService \
                ._commit_operational_state(
                    sismolab,
                    temp_lab
                )


            response.data = {

                "active_events":
                    (
                        sismolab
                        .get_avl_tree()
                        .count_nodes()
                    ),

                "archived_events":
                    (
                        sismolab
                        .get_history()
                        .count_events()
                    ),

                "deleted_events":
                    len(
                        sismolab
                        .get_retired_ids()
                    ),

                "stress_mode":
                    (
                        sismolab
                        .get_scenario()
                        .is_stress_mode()
                    )
            }


            response.msg = (
                success_message
            )


            return response


        except Exception as exc:

            response.ok = False

            response.error = (
                "State rejected. "
                "Current scenario was not modified. "
                f"Reason: {exc}"
            )


            return response


    # =========================================================
    # CONSTRUIR SISTEMA TEMPORAL COMPLETO
    # =========================================================

    @staticmethod
    def _build_lab_from_state(
        state
    ):

        if not isinstance(
            state,
            dict
        ):

            raise ValueError(
                "State must be a JSON object"
            )


        scenario_data = (
            state.get(
                "scenario"
            )
        )


        if not isinstance(
            scenario_data,
            dict
        ):

            raise ValueError(
                "Missing 'scenario' section"
            )


        simulation_clock = (
            PersistenceService
            ._parse_datetime(
                scenario_data.get(
                    "simulation_clock"
                )
            )
        )


        # -----------------------------------------------------
        # VALIDAR PARÃMETROS
        # -----------------------------------------------------

        access_limit = (
            scenario_data.get(
                "access_limit",
                3
            )
        )


        if (
            isinstance(
                access_limit,
                bool
            )
            or
            not isinstance(
                access_limit,
                int
            )
            or
            access_limit < 0
        ):

            raise ValueError(
                "L must be a "
                "non-negative integer"
            )


        w_hours = (
            PersistenceService
            ._positive_float(
                scenario_data.get(
                    "w_hours",
                    48
                ),
                "W"
            )
        )


        r_km = (
            PersistenceService
            ._positive_float(
                scenario_data.get(
                    "r_km",
                    40
                ),
                "R"
            )
        )


        archive_age_hours = (
            PersistenceService
            ._positive_float(
                scenario_data.get(
                    "archive_age_hours",
                    72
                ),
                "T"
            )
        )


        stress_mode = (
            scenario_data.get(
                "stress_mode",
                False
            )
        )


        if not isinstance(
            stress_mode,
            bool
        ):

            raise ValueError(
                "stress_mode must be boolean"
            )


        scenario = Scenario(
            simulation_clock=simulation_clock,
            w_hours=w_hours,
            r_km=r_km,
            access_limit=access_limit,
            archive_age_hours=archive_age_hours,
            stress_mode=stress_mode
        )


        # -----------------------------------------------------
        # ZONAS
        # -----------------------------------------------------

        zones = (
            scenario_data.get(
                "zones",
                []
            )
        )


        if not isinstance(
            zones,
            list
        ):

            raise ValueError(
                "scenario.zones must be a list"
            )


        for zone_data in zones:

            if not isinstance(
                zone_data,
                dict
            ):

                raise ValueError(
                    "Every zone must "
                    "be an object"
                )


            zone = Zone(
                zone_data.get(
                    "name"
                ),
                zone_data.get(
                    "x_min"
                ),
                zone_data.get(
                    "x_max"
                ),
                zone_data.get(
                    "y_min"
                ),
                zone_data.get(
                    "y_max"
                ),
                zone_data.get(
                    "is_populated"
                )
            )


            if not scenario.add_zone(
                zone
            ):

                raise ValueError(
                    "Invalid or duplicated zone: "
                    f"{zone_data.get('name')}"
                )


        # -----------------------------------------------------
        # ESTACIONES
        # -----------------------------------------------------

        stations = (
            scenario_data.get(
                "stations",
                []
            )
        )


        if not isinstance(
            stations,
            list
        ):

            raise ValueError(
                "scenario.stations "
                "must be a list"
            )


        for station_data in stations:

            if not isinstance(
                station_data,
                dict
            ):

                raise ValueError(
                    "Every station must "
                    "be an object"
                )


            station = Station(
                station_data.get(
                    "name"
                ),
                station_data.get(
                    "x"
                ),
                station_data.get(
                    "y"
                )
            )


            if not scenario.add_station(
                station
            ):

                raise ValueError(
                    "Invalid or duplicated station: "
                    f"{station_data.get('name')}"
                )


        lab = SismoLab(
            scenario
        )


        global_ids = set()


        # Necesitamos este diccionario
        # para reconstruir BST posteriormente.
        active_events = {}


        # =====================================================
        # AVL ACTIVO
        # =====================================================

        (
            active_root,
            _
        ) = (
            PersistenceService
            ._build_avl_node(
                state.get(
                    "active_avl_topology"
                ),
                scenario,
                expected_status=(
                    CatalogStatus.ACTIVE
                ),
                global_ids=global_ids,
                min_key=None,
                max_key=None,
                depth=0,
                require_balanced=(
                    not stress_mode
                ),
                verify_costly_access=True
            )
        )


        lab.get_avl_tree().set_root(
            active_root
        )


        # Registrar todos los Events activos
        # dentro del diccionario auxiliar.
        PersistenceService \
            ._register_tree_events(
                active_root,
                scenario,
                active_events
            )


        # =====================================================
        # HISTÃ“RICO
        # =====================================================

        history_topologies = (
            state.get(
                "history_topologies",
                []
            )
        )


        if not isinstance(
            history_topologies,
            list
        ):

            raise ValueError(
                "history_topologies "
                "must be a list"
            )


        for root_data in history_topologies:

            (
                archived_root,
                _
            ) = (
                PersistenceService
                ._build_avl_node(
                    root_data,
                    scenario,
                    expected_status=(
                        CatalogStatus.ARCHIVED
                    ),
                    global_ids=global_ids,
                    min_key=None,
                    max_key=None,
                    depth=0,
                    require_balanced=False,
                    verify_costly_access=False
                )
            )


            if archived_root is None:

                raise ValueError(
                    "Archived root cannot be null"
                )


            lab.get_history() \
                .add_archived_root(
                    archived_root
                )


            PersistenceService \
                ._register_tree_events(
                    archived_root,
                    scenario
                )


        # =====================================================
        # ELIMINADOS
        # =====================================================

        deleted_events = (
            state.get(
                "deleted_events",
                []
            )
        )


        if not isinstance(
            deleted_events,
            list
        ):

            raise ValueError(
                "deleted_events "
                "must be a list"
            )


        deleted_ids = set()


        for event_data in deleted_events:

            event = (
                PersistenceService
                ._event_from_dict(
                    event_data,
                    scenario,
                    expected_status=(
                        CatalogStatus.DELETED
                    ),
                    default_status=(
                        CatalogStatus.DELETED
                    )
                )
            )


            if (
                event.identifier
                in global_ids
            ):

                raise ValueError(
                    f"Identifier "
                    f"{event.identifier} "
                    f"appears in more than "
                    f"one catalog"
                )


            global_ids.add(
                event.identifier
            )


            deleted_ids.add(
                event.identifier
            )


            scenario._events_by_id[
                event.identifier
            ] = event


        # =====================================================
        # IDS RETIRADOS
        # =====================================================

        retired_ids_raw = (
            state.get(
                "retired_ids",
                []
            )
        )


        if not isinstance(
            retired_ids_raw,
            list
        ):

            raise ValueError(
                "retired_ids must be a list"
            )


        retired_ids = {

            PersistenceService
            ._strict_identifier(
                identifier
            )

            for identifier
            in retired_ids_raw
        }


        # Todo eliminado debe ser retirado
        # y viceversa.
        if (
            retired_ids
            !=
            deleted_ids
        ):

            raise ValueError(
                "retired_ids must match exactly "
                "the identifiers of deleted events"
            )


        lab._retired_ids = set(
            retired_ids
        )


        # =====================================================
        # BST COMPARATIVO
        #
        # Se reconstruye DIRECTAMENTE por topologÃ­a,
        # no mediante insert().
        # =====================================================

        bst_seen = set()


        bst_root = (
            PersistenceService
            ._build_bst_node(
                state.get(
                    "comparison_bst_topology"
                ),
                active_events,
                bst_seen,
                min_key=None,
                max_key=None
            )
        )


        if (
            bst_seen
            !=
            set(
                active_events.keys()
            )
        ):

            raise ValueError(
                "BST topology does not contain "
                "exactly the same active event IDs "
                "as AVL"
            )


        lab.get_bst_tree().set_root(
            bst_root
        )


        # =====================================================
        # COLA FIFO
        # =====================================================

        queue_data = (
            state.get(
                "report_queue",
                []
            )
        )


        if not isinstance(
            queue_data,
            list
        ):

            raise ValueError(
                "report_queue must be a list"
            )


        for report_data in queue_data:

            report = (
                PersistenceService
                ._report_from_dict(
                    report_data,
                    scenario
                )
            )


            lab.get_report_queue() \
                .enqueue(
                    report
                )


        # =====================================================
        # MÃ‰TRICAS
        # =====================================================

        metrics_data = (
            state.get(
                "metrics",
                {}
            )
        )


        lab._metrics = (
            PersistenceService
            ._metrics_from_dict(
                metrics_data
            )
        )


        # =====================================================
        # ASOCIACIONES
        # =====================================================

        # Como nuestra polÃ­tica es determinista,
        # las reconstruimos.
        AssociationService(
            lab
        ).recalculate_all()


        # Si el JSON guardÃ³ asociaciones,
        # verificamos que coincidan EXACTAMENTE
        # con el resultado reconstruido.
        saved_associations = (
            state.get(
                "associations"
            )
        )


        if saved_associations is not None:

            if not isinstance(
                saved_associations,
                list
            ):

                raise ValueError(
                    "associations must be a list"
                )


            saved_pairs = set()


            for item in saved_associations:

                if not isinstance(
                    item,
                    dict
                ):

                    raise ValueError(
                        "Every association "
                        "must be an object"
                    )


                reference_id = (
                    PersistenceService
                    ._strict_identifier(
                        item.get(
                            "reference_event_id"
                        )
                    )
                )


                aftershock_id = (
                    PersistenceService
                    ._strict_identifier(
                        item.get(
                            "aftershock_event_id"
                        )
                    )
                )


                reference_event = (
                    scenario.get_event_by_id(
                        reference_id
                    )
                )

                aftershock_event = (
                    scenario.get_event_by_id(
                        aftershock_id
                    )
                )


                if (
                    reference_event is None
                    or
                    aftershock_event is None
                ):

                    raise ValueError(
                        "Association references "
                        "an unknown event"
                    )


                if (
                    reference_event.catalog_status
                    ==
                    CatalogStatus.DELETED

                    or

                    aftershock_event.catalog_status
                    ==
                    CatalogStatus.DELETED
                ):

                    raise ValueError(
                        "Deleted events cannot "
                        "participate in associations"
                    )


                saved_pairs.add(
                    (
                        reference_id,
                        aftershock_id
                    )
                )


            calculated_pairs = {

                (
                    association
                    .get_reference_event()
                    .identifier,

                    association
                    .get_aftershock_event()
                    .identifier
                )

                for association
                in lab.get_associations()
            }


            if (
                saved_pairs
                !=
                calculated_pairs
            ):

                raise ValueError(
                    "Stored associations do not "
                    "match the deterministic "
                    "association policy"
                )


        return lab


    # =========================================================
    # SERIALIZAR AVL
    # =========================================================

    @staticmethod
    def _serialize_avl_node(
        node,
        include_costly_access=False
    ):

        if node is None:

            return None


        left_height = (
            node.get_left().get_height()
            if node.get_left()
            else -1
        )


        right_height = (
            node.get_right().get_height()
            if node.get_right()
            else -1
        )


        result = {

            "event":
                node
                .get_event()
                .to_dict(),

            "height":
                node.get_height(),

            "balance_factor":
                left_height
                -
                right_height,

            "left":
                PersistenceService
                ._serialize_avl_node(
                    node.get_left(),
                    include_costly_access
                ),

            "right":
                PersistenceService
                ._serialize_avl_node(
                    node.get_right(),
                    include_costly_access
                )
        }


        if include_costly_access:

            result[
                "costly_access"
            ] = (
                node.is_costly_access()
            )


        return result


    # =========================================================
    # RECONSTRUIR AVL DIRECTAMENTE
    # =========================================================

    @staticmethod
    def _build_avl_node(
        node_data,
        scenario,
        expected_status,
        global_ids,
        min_key,
        max_key,
        depth,
        require_balanced,
        verify_costly_access
    ):

        if node_data is None:

            return None, -1


        if not isinstance(
            node_data,
            dict
        ):

            raise ValueError(
                "Every topology node "
                "must be an object or null"
            )


        event_data = (
            node_data.get(
                "event"
            )
        )


        if not isinstance(
            event_data,
            dict
        ):

            raise ValueError(
                "Topology node is "
                "missing its event"
            )


        event = (
            PersistenceService
            ._event_from_dict(
                event_data,
                scenario,
                expected_status=(
                    expected_status
                ),
                default_status=(
                    expected_status
                )
            )
        )


        # Un mismo Event no puede aparecer
        # dos veces en activo/histÃ³rico.
        if (
            event.identifier
            in global_ids
        ):

            raise ValueError(
                f"Identifier "
                f"{event.identifier} "
                f"appears more than once "
                f"in active/history topology"
            )


        global_ids.add(
            event.identifier
        )


        key = (
            event.get_key()
        )


        # -----------------------------------------------------
        # ORDEN BST GLOBAL
        # -----------------------------------------------------

        if (
            min_key is not None
            and
            key <= min_key
        ):

            raise ValueError(
                "Global BST order violation "
                f"at event {event.identifier}: "
                f"{key} <= {min_key}"
            )


        if (
            max_key is not None
            and
            key >= max_key
        ):

            raise ValueError(
                "Global BST order violation "
                f"at event {event.identifier}: "
                f"{key} >= {max_key}"
            )


        (
            left_node,
            left_height
        ) = (
            PersistenceService
            ._build_avl_node(
                node_data.get(
                    "left"
                ),
                scenario,
                expected_status,
                global_ids,
                min_key,
                key,
                depth + 1,
                require_balanced,
                verify_costly_access
            )
        )


        (
            right_node,
            right_height
        ) = (
            PersistenceService
            ._build_avl_node(
                node_data.get(
                    "right"
                ),
                scenario,
                expected_status,
                global_ids,
                key,
                max_key,
                depth + 1,
                require_balanced,
                verify_costly_access
            )
        )


        calculated_height = (
            1
            +
            max(
                left_height,
                right_height
            )
        )


        calculated_balance = (
            left_height
            -
            right_height
        )


        stored_height = (
            node_data.get(
                "height"
            )
        )


        stored_balance = (
            node_data.get(
                "balance_factor"
            )
        )


        # -----------------------------------------------------
        # VALIDAR METADATOS
        # -----------------------------------------------------

        if (
            stored_height
            !=
            calculated_height
        ):

            raise ValueError(
                "Stored height mismatch "
                f"at event {event.identifier}: "
                f"stored={stored_height}, "
                f"calculated="
                f"{calculated_height}"
            )


        if (
            stored_balance
            !=
            calculated_balance
        ):

            raise ValueError(
                "Stored balance factor mismatch "
                f"at event {event.identifier}: "
                f"stored={stored_balance}, "
                f"calculated="
                f"{calculated_balance}"
            )


        # En modo normal debe ser AVL.
        if (
            require_balanced
            and
            abs(
                calculated_balance
            )
            >
            1
        ):

            raise ValueError(
                "Unbalanced AVL node "
                f"{event.identifier} "
                "cannot be loaded "
                "in normal mode"
            )


        # -----------------------------------------------------
        # CONSTRUIR NODO DIRECTAMENTE
        # -----------------------------------------------------

        node = AVLNode(
            event
        )


        node.set_height(
            calculated_height
        )


        node.set_left(
            left_node
        )


        node.set_right(
            right_node
        )


        if left_node is not None:

            left_node.set_parent(
                node
            )


        if right_node is not None:

            right_node.set_parent(
                node
            )


        # -----------------------------------------------------
        # VALIDAR ACCESO COSTOSO
        # -----------------------------------------------------

        if verify_costly_access:

            stored_costly = (
                node_data.get(
                    "costly_access"
                )
            )


            expected_costly = (

                event.priority == 3

                and

                depth
                >
                scenario.get_access_limit()
            )


            if (
                stored_costly
                is not
                expected_costly
            ):

                raise ValueError(
                    "Costly-access flag mismatch "
                    f"at event "
                    f"{event.identifier}"
                )


            node.set_costly_access(
                expected_costly
            )


        return (
            node,
            calculated_height
        )


    # =========================================================
    # SERIALIZAR BST
    # =========================================================

    @staticmethod
    def _serialize_bst_node(
        node
    ):

        if node is None:

            return None


        return {

            "event_id":
                node
                .get_event()
                .identifier,

            "left":
                PersistenceService
                ._serialize_bst_node(
                    node.get_left()
                ),

            "right":
                PersistenceService
                ._serialize_bst_node(
                    node.get_right()
                )
        }


    # =========================================================
    # RECONSTRUIR BST DIRECTAMENTE
    # =========================================================

    @staticmethod
    def _build_bst_node(
        node_data,
        active_events,
        seen_ids,
        min_key,
        max_key
    ):

        if node_data is None:

            return None


        if not isinstance(
            node_data,
            dict
        ):

            raise ValueError(
                "Every BST topology node "
                "must be an object or null"
            )


        identifier = (
            PersistenceService
            ._strict_identifier(
                node_data.get(
                    "event_id"
                )
            )
        )


        if identifier in seen_ids:

            raise ValueError(
                "Duplicate/cyclic identifier "
                "in BST topology: "
                f"{identifier}"
            )


        event = (
            active_events.get(
                identifier
            )
        )


        if event is None:

            raise ValueError(
                "BST references non-active "
                "or unknown identifier "
                f"{identifier}"
            )


        seen_ids.add(
            identifier
        )


        key = (
            event.get_key()
        )


        if (
            min_key is not None
            and
            key <= min_key
        ):

            raise ValueError(
                "Global BST order violation "
                "in comparison tree "
                f"at {identifier}"
            )


        if (
            max_key is not None
            and
            key >= max_key
        ):

            raise ValueError(
                "Global BST order violation "
                "in comparison tree "
                f"at {identifier}"
            )


        left_node = (
            PersistenceService
            ._build_bst_node(
                node_data.get(
                    "left"
                ),
                active_events,
                seen_ids,
                min_key,
                key
            )
        )


        right_node = (
            PersistenceService
            ._build_bst_node(
                node_data.get(
                    "right"
                ),
                active_events,
                seen_ids,
                key,
                max_key
            )
        )


        node = BSTNode(
            event
        )


        node.set_left(
            left_node
        )


        node.set_right(
            right_node
        )


        if left_node is not None:

            left_node.set_parent(
                node
            )


        if right_node is not None:

            right_node.set_parent(
                node
            )


        return node


    # =========================================================
    # EVENT DESDE JSON
    # =========================================================

    @staticmethod
    def _event_from_dict(
        data,
        scenario,
        expected_status=None,
        default_status=CatalogStatus.ACTIVE
    ):

        if not isinstance(
            data,
            dict
        ):

            raise ValueError(
                "Event must be an object"
            )


        identifier = (
            PersistenceService
            ._strict_identifier(
                data.get(
                    "identifier"
                )
            )
        )


        date_time = (
            PersistenceService
            ._parse_datetime(
                data.get(
                    "date_time"
                )
            )
        )


        magnitude = float(
            data.get(
                "magnitude"
            )
        )


        depth = float(
            data.get(
                "depth"
            )
        )


        x = float(
            data.get(
                "x"
            )
        )


        y = float(
            data.get(
                "y"
            )
        )


        revision = int(
            data.get(
                "revision",
                1
            )
        )


        # -----------------------------------------------------
        # RECALCULAR DERIVADOS
        # -----------------------------------------------------

        is_populated = (
            scenario
            .is_point_in_populated_zone(
                x,
                y
            )
        )


        calculated_priority = (
            PriorityService
            .calculate_priority(
                magnitude,
                depth,
                is_populated
            )
        )


        # Si vienen almacenados,
        # DEBEN coincidir.
        if (
            "is_populated_zone"
            in data
        ):

            stored_populated = (
                data.get(
                    "is_populated_zone"
                )
            )


            if (
                not isinstance(
                    stored_populated,
                    bool
                )
                or
                stored_populated
                !=
                is_populated
            ):

                raise ValueError(
                    "Stored populated-zone "
                    "value is inconsistent "
                    f"for event {identifier}"
                )


        if "priority" in data:

            stored_priority = (
                data.get(
                    "priority"
                )
            )


            if (
                stored_priority
                !=
                calculated_priority
            ):

                raise ValueError(
                    "Stored priority is "
                    "inconsistent for event "
                    f"{identifier}: "
                    f"stored="
                    f"{stored_priority}, "
                    f"calculated="
                    f"{calculated_priority}"
                )


        event = Event(
            identifier=identifier,
            magnitude=magnitude,
            depth=depth,
            x=x,
            y=y,
            date_time=date_time,
            revision=revision,
            priority=calculated_priority,
            is_populated_zone=is_populated
        )


        # -----------------------------------------------------
        # ESTADOS
        # -----------------------------------------------------

        attention_text = (
            data.get(
                "attention_status",
                AttentionStatus
                .PENDING
                .value
            )
        )


        catalog_text = (
            data.get(
                "catalog_status",
                default_status.value
            )
        )


        try:

            event.attention_status = (
                AttentionStatus(
                    attention_text
                )
            )


            event.catalog_status = (
                CatalogStatus(
                    catalog_text
                )
            )


        except ValueError as exc:

            raise ValueError(
                "Invalid status for event "
                f"{identifier}: {exc}"
            )


        if (
            expected_status is not None
            and
            event.catalog_status
            !=
            expected_status
        ):

            raise ValueError(
                f"Event {identifier} "
                f"has status "
                f"{event.catalog_status.value}; "
                f"expected "
                f"{expected_status.value}"
            )


        # -----------------------------------------------------
        # ESTACIONES ACEPTADAS
        # -----------------------------------------------------

        accepted_stations = (
            data.get(
                "accepted_stations",
                []
            )
        )


        if not isinstance(
            accepted_stations,
            list
        ):

            raise ValueError(
                "accepted_stations "
                "must be a list "
                f"for event {identifier}"
            )


        for station_name in (
            accepted_stations
        ):

            if (
                not isinstance(
                    station_name,
                    str
                )
                or
                station_name.strip()
                ==
                ""
            ):

                raise ValueError(
                    "Invalid accepted station "
                    f"in event {identifier}"
                )


            if (
                scenario.get_station_by_name(
                    station_name
                )
                is None
            ):

                raise ValueError(
                    f"Event {identifier} "
                    f"references unknown "
                    f"accepted station "
                    f"'{station_name}'"
                )


            event.add_accepted_station(
                station_name
            )


        # -----------------------------------------------------
        # VALIDACIÃ“N FINAL
        # -----------------------------------------------------

        if not event.validateAttributes():

            raise ValueError(
                f"Invalid attributes "
                f"for event {identifier}"
            )


        if (
            event.date_time
            >
            scenario.get_simulation_clock()
        ):

            raise ValueError(
                f"Event {identifier} "
                f"occurs after the "
                f"simulation clock"
            )


        return event


    # =========================================================
    # REPORT SERIALIZATION
    # =========================================================

    @staticmethod
    def _serialize_report(
        report
    ):

        return {

            "identifier":
                report.identifier,

            "revision":
                report.revision,

            "station_name":
                (
                    report.station.name
                    if report.station
                    is not None
                    else None
                ),

            "magnitude":
                report.magnitude,

            "depth":
                report.depth,

            "x":
                report.x,

            "y":
                report.y,

            "date_time":
                PersistenceService
                ._datetime_to_text(
                    report.date_time
                ),

            "event_id":
                (
                    report.event.identifier
                    if report.event
                    is not None
                    else None
                ),

            "decision":
                report.decision
        }


    # =========================================================
    # REPORT DESDE JSON
    # =========================================================

    @staticmethod
    def _report_from_dict(
        data,
        scenario
    ):

        if not isinstance(
            data,
            dict
        ):

            raise ValueError(
                "Queue report "
                "must be an object"
            )


        identifier = (
            PersistenceService
            ._strict_identifier(
                data.get(
                    "identifier"
                )
            )
        )


        revision = (
            data.get(
                "revision"
            )
        )


        if isinstance(
            revision,
            bool
        ):

            raise ValueError(
                "Report revision must "
                "be a positive integer"
            )


        revision = int(
            revision
        )


        if revision <= 0:

            raise ValueError(
                "Report revision must "
                "be a positive integer"
            )


        station_name = (
            data.get(
                "station_name"
            )
        )


        station = (
            scenario
            .get_station_by_name(
                station_name
            )
        )


        if station is None:

            raise ValueError(
                "Queue report references "
                "unknown station "
                f"'{station_name}'"
            )


        date_time = (
            PersistenceService
            ._parse_datetime(
                data.get(
                    "date_time"
                )
            )
        )


        magnitude = float(
            data.get(
                "magnitude"
            )
        )


        depth = float(
            data.get(
                "depth"
            )
        )


        x = float(
            data.get(
                "x"
            )
        )


        y = float(
            data.get(
                "y"
            )
        )


        is_populated = (
            scenario
            .is_point_in_populated_zone(
                x,
                y
            )
        )


        priority = (
            PriorityService
            .calculate_priority(
                magnitude,
                depth,
                is_populated
            )
        )


        # Reutilizamos Event solamente
        # como validador fÃ­sico.
        validator_event = Event(
            identifier,
            magnitude,
            depth,
            x,
            y,
            date_time,
            revision,
            priority,
            is_populated
        )


        if not (
            validator_event
            .validateAttributes()
        ):

            raise ValueError(
                "Invalid physical data "
                "in queued report for "
                f"identifier {identifier}"
            )


        if (
            date_time
            >
            scenario
            .get_simulation_clock()
        ):

            raise ValueError(
                "Queued report event "
                f"{identifier} occurs "
                "after the simulation clock"
            )


        report = Report(
            identifier=identifier,
            revision=revision,
            station=station,
            magnitude=magnitude,
            depth=depth,
            x=x,
            y=y,
            date_time=date_time,
            event=None
        )


        event_id = (
            data.get(
                "event_id"
            )
        )


        if event_id is not None:

            event_id = (
                PersistenceService
                ._strict_identifier(
                    event_id
                )
            )


            event = (
                scenario
                .get_event_by_id(
                    event_id
                )
            )


            if event is None:

                raise ValueError(
                    "Queued report references "
                    "unknown processed event "
                    f"{event_id}"
                )


            report.event = (
                event
            )


        report.decision = (
            data.get(
                "decision"
            )
        )


        return report


    # =========================================================
    # MÃ‰TRICAS
    # =========================================================

    @staticmethod
    def _metrics_from_dict(
        data
    ):

        if not isinstance(
            data,
            dict
        ):

            raise ValueError(
                "metrics must be an object"
            )


        required = [

            "accepted_corrections",
            "discarded_reports",
            "conflicts",
            "mass_archives",
            "archived_events",

            "ll_cases",
            "rr_cases",
            "lr_cases",
            "rl_cases",

            "left_rotations",
            "right_rotations"
        ]


        clean = {}


        for key in required:

            value = (
                data.get(
                    key,
                    0
                )
            )


            if (
                isinstance(
                    value,
                    bool
                )
                or
                not isinstance(
                    value,
                    int
                )
                or
                value < 0
            ):

                raise ValueError(
                    f"Metric '{key}' "
                    f"must be a "
                    f"non-negative integer"
                )


            clean[
                key
            ] = value


        metrics = Metrics()


        metrics.load_summary(
            clean
        )


        return metrics


    # =========================================================
    # AUXILIARES
    # =========================================================

    @staticmethod
    def _register_tree_events(
        root,
        scenario,
        target_dict=None
    ):

        if root is None:
            return


        event = (
            root.get_event()
        )


        scenario._events_by_id[
            event.identifier
        ] = event


        if target_dict is not None:

            target_dict[
                event.identifier
            ] = event


        PersistenceService \
            ._register_tree_events(
                root.get_left(),
                scenario,
                target_dict
            )


        PersistenceService \
            ._register_tree_events(
                root.get_right(),
                scenario,
                target_dict
            )


    # Copia solamente configuraciÃ³n,
    # no Events.
    @staticmethod
    def _clone_scenario_configuration(
        source
    ):

        scenario = Scenario(
            simulation_clock=(
                source
                .get_simulation_clock()
            ),
            w_hours=(
                source.get_w_hours()
            ),
            r_km=(
                source.get_r_km()
            ),
            access_limit=(
                source
                .get_access_limit()
            ),
            archive_age_hours=(
                source
                .get_archive_age_hours()
            ),
            stress_mode=(
                source.is_stress_mode()
            )
        )


        for zone in (
            source.get_zones()
        ):

            scenario.add_zone(
                Zone(
                    zone.name,
                    zone.x_min,
                    zone.x_max,
                    zone.y_min,
                    zone.y_max,
                    zone.is_populated
                )
            )


        for station in (
            source.get_stations()
        ):

            scenario.add_station(
                Station(
                    station.name,
                    station.x,
                    station.y
                )
            )


        return scenario


    # Sustituye solamente el estado operativo.
    #
    # NO toca:
    # - undo stack
    # - versiones
    #
    # Esto serÃ¡ importante en el punto 13.
    @staticmethod
    def _commit_operational_state(
        target,
        source
    ):

        target._scenario = (
            source._scenario
        )

        target._avl_tree = (
            source._avl_tree
        )

        target._bst_tree = (
            source._bst_tree
        )

        target._history = (
            source._history
        )

        target._report_queue = (
            source._report_queue
        )

        target._metrics = (
            source._metrics
        )

        target._associations = (
            source._associations
        )

        target._retired_ids = (
            source._retired_ids
        )


    @staticmethod
    def _datetime_to_text(
        value
    ):

        text = (
            value.isoformat(
                timespec="seconds"
            )
        )


        if text.endswith(
            "+00:00"
        ):

            text = (
                text[:-6]
                +
                "Z"
            )


        return text


    @staticmethod
    def _parse_datetime(
        value
    ):

        if isinstance(
            value,
            datetime
        ):

            result = value


        elif isinstance(
            value,
            str
        ):

            result = (
                datetime.fromisoformat(
                    value.replace(
                        "Z",
                        "+00:00"
                    )
                )
            )


        else:

            raise ValueError(
                "Invalid datetime value"
            )


        if result.microsecond != 0:

            raise ValueError(
                "Datetime must have "
                "second precision"
            )


        if (
            result.tzinfo is None
            or
            result.utcoffset()
            is None
        ):

            raise ValueError(
                "Datetime must include "
                "UTC timezone"
            )


        if (
            result
            .utcoffset()
            .total_seconds()
            != 0
        ):

            raise ValueError(
                "Datetime must use "
                "UTC timezone"
            )


        return result


    @staticmethod
    def _positive_float(
        value,
        name
    ):

        try:

            value = float(
                value
            )


        except (
            TypeError,
            ValueError
        ):

            raise ValueError(
                f"{name} must be numeric"
            )


        if (
            not isfinite(
                value
            )
            or
            value <= 0
        ):

            raise ValueError(
                f"{name} must be "
                "positive and finite"
            )


        return value


    @staticmethod
    def _strict_identifier(
        value
    ):

        if isinstance(
            value,
            bool
        ):

            raise ValueError(
                "Identifier must "
                "be an integer"
            )


        if isinstance(
            value,
            int
        ):

            identifier = value


        elif (
            isinstance(
                value,
                str
            )
            and
            value.strip().isdigit()
        ):

            identifier = int(
                value.strip()
            )


        else:

            raise ValueError(
                "Identifier must "
                "be an integer"
            )


        if (
            identifier < 1
            or
            identifier > 999999
        ):

            raise ValueError(
                "Identifier must be "
                "inside [1, 999999]"
            )


        return identifier
