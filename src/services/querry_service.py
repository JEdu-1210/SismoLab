from typing import Any, List, Dict, Optional, Tuple
from datetime import datetime
from src.models.Returnings import DataAndMsgReturn
from src.models.Status import AttentionStatus


class QueryService:
    """
    Servicio para ejecutar las consultas analíticas sobre los eventos de SismoLab (Punto 11).
    Reporta de forma explícita la cantidad de nodos del AVL examinados en cada búsqueda.
    """

    # -------------------------------------------------------------------------
    # CONSULTA 1: Primeros K eventos pendientes en orden descendente de K
    # -------------------------------------------------------------------------
    @staticmethod
    def get_top_k_pending(sismolab: Any, k: int) -> DataAndMsgReturn:
        response = DataAndMsgReturn()
        if k <= 0:
            response.error = "El parámetro 'k' debe ser un entero positivo."
            return response

        results: List[Any] = []
        examined_nodes = [0]
        avl_tree = sismolab.get_avl_tree()
        root = avl_tree.get_root() if (avl_tree and hasattr(avl_tree, "get_root")) else getattr(avl_tree, "root", None)

        def _reverse_in_order(node):
            if node is None or len(results) >= k:
                return

            # Visitar subárbol derecho (claves K mayores)
            right_child = node.get_right() if hasattr(node, "get_right") else getattr(node, "right", None)
            _reverse_in_order(right_child)

            if len(results) >= k:
                return

            # Examinar nodo actual
            examined_nodes[0] += 1
            event = node.get_event() if hasattr(node, "get_event") else getattr(node, "event", None)

            status = getattr(event, "attention_status", None)
            is_pending = (status == AttentionStatus.PENDING) or (str(status) == "PENDING") or (getattr(status, "value", "") == "PENDING")

            if is_pending:
                results.append(event.to_dict() if hasattr(event, "to_dict") else event)

            if len(results) >= k:
                return

            # Visitar subárbol izquierdo (claves K menores)
            left_child = node.get_left() if hasattr(node, "get_left") else getattr(node, "left", None)
            _reverse_in_order(left_child)

        _reverse_in_order(root)

        response.data = {
            "events": results,
            "count_retrieved": len(results),
            "k_requested": k,
            "examined_nodes": examined_nodes[0]
        }
        response.msg = f"Se obtuvieron {len(results)} eventos pendientes examinando {examined_nodes[0]} nodos."
        return response

    # -------------------------------------------------------------------------
    # CONSULTA 2A: Eventos por rango inclusivo de Magnitud
    # -------------------------------------------------------------------------
    @staticmethod
    def get_events_by_magnitude_range(sismolab: Any, min_mag: float, max_mag: float) -> DataAndMsgReturn:
        response = DataAndMsgReturn()
        min_mag = float(min_mag)
        max_mag = float(max_mag)

        results: List[Any] = []
        examined_nodes = [0]
        avl_tree = sismolab.get_avl_tree()
        root = avl_tree.get_root() if (avl_tree and hasattr(avl_tree, "get_root")) else getattr(avl_tree, "root", None)

        def _traverse(node):
            if node is None:
                return

            examined_nodes[0] += 1
            event = node.get_event() if hasattr(node, "get_event") else getattr(node, "event", None)

            if min_mag <= event.magnitude <= max_mag:
                results.append(event.to_dict() if hasattr(event, "to_dict") else event)

            left_child = node.get_left() if hasattr(node, "get_left") else getattr(node, "left", None)
            right_child = node.get_right() if hasattr(node, "get_right") else getattr(node, "right", None)

            _traverse(left_child)
            _traverse(right_child)

        _traverse(root)

        response.data = {
            "events": results,
            "min_magnitude": min_mag,
            "max_magnitude": max_mag,
            "examined_nodes": examined_nodes[0]
        }
        response.msg = f"Se encontraron {len(results)} eventos en el rango de magnitud [{min_mag}, {max_mag}]."
        return response

    # -------------------------------------------------------------------------
    # CONSULTA 2B: Eventos por profundidad e intervalo inclusivo de fechas
    # -------------------------------------------------------------------------
    @staticmethod
    def get_events_by_depth_and_date_range(sismolab: Any, limit_depth: float, min_date: Any, max_date: Any) -> DataAndMsgReturn:
        response = DataAndMsgReturn()
        limit_depth = float(limit_depth)

        # Normalización segura de fechas a objetos datetime
        def _parse_date(dt_input):
            if isinstance(dt_input, datetime):
                return dt_input
            return datetime.fromisoformat(str(dt_input).replace("Z", "+00:00"))

        dt_min = _parse_date(min_date)
        dt_max = _parse_date(max_date)

        results: List[Any] = []
        examined_nodes = [0]
        avl_tree = sismolab.get_avl_tree()
        root = avl_tree.get_root() if (avl_tree and hasattr(avl_tree, "get_root")) else getattr(avl_tree, "root", None)

        def _traverse(node):
            if node is None:
                return

            examined_nodes[0] += 1
            event = node.get_event() if hasattr(node, "get_event") else getattr(node, "event", None)
            event_date = _parse_date(event.date_time)

            if event.depth <= limit_depth and (dt_min <= event_date <= dt_max):
                results.append(event.to_dict() if hasattr(event, "to_dict") else event)

            left_child = node.get_left() if hasattr(node, "get_left") else getattr(node, "left", None)
            right_child = node.get_right() if hasattr(node, "get_right") else getattr(node, "right", None)

            _traverse(left_child)
            _traverse(right_child)

        _traverse(root)

        response.data = {
            "events": results,
            "limit_depth": limit_depth,
            "date_range": [dt_min.isoformat(), dt_max.isoformat()],
            "examined_nodes": examined_nodes[0]
        }
        response.msg = f"Se encontraron {len(results)} eventos en el rango especificado."
        return response

    # -------------------------------------------------------------------------
    # CONSULTA 3: Candidatos, referencia elegida y referencias inversas (Activos e Histórico)
    # -------------------------------------------------------------------------
    @staticmethod
    def get_event_associations(sismolab: Any, target_event_id: int) -> DataAndMsgReturn:
        response = DataAndMsgReturn()
        examined_nodes = [0]
        all_events: List[Tuple[Any, str]] = []

        # Recolectar eventos activos del AVL
        avl_tree = sismolab.get_avl_tree()
        root = avl_tree.get_root() if (avl_tree and hasattr(avl_tree, "get_root")) else getattr(avl_tree, "root", None)

        def _collect_active(node):
            if node is None:
                return
            examined_nodes[0] += 1
            event = node.get_event() if hasattr(node, "get_event") else getattr(node, "event", None)
            all_events.append((event, "ACTIVE"))
            left = node.get_left() if hasattr(node, "get_left") else getattr(node, "left", None)
            right = node.get_right() if hasattr(node, "get_right") else getattr(node, "right", None)
            _collect_active(left)
            _collect_active(right)

        _collect_active(root)

        # Recolectar eventos archivados del Histórico
        history = sismolab.get_history()
        if history:
            archived_list = history.get_all_events() if hasattr(history, "get_all_events") else []
            for ev in archived_list:
                all_events.append((ev, "ARCHIVED"))

        # Localizar el evento objetivo
        target_event = None
        target_status = "UNKNOWN"
        for ev, status in all_events:
            if ev.identifier == target_event_id:
                target_event = ev
                target_status = status
                break

        if not target_event:
            response.error = f"El evento con ID {target_event_id} no existe en el árbol activo ni en el histórico."
            response.data = {"examined_nodes": examined_nodes[0]}
            return response

        scenario = sismolab.get_scenario()
        r_km = getattr(scenario, "r_km", 40.0) if scenario else 40.0

        candidates = []
        referencing_events = []

        for ev, status in all_events:
            if ev.identifier == target_event_id:
                continue

            dist = ((ev.x - target_event.x) ** 2 + (ev.y - target_event.y) ** 2) ** 0.5
            if dist <= r_km:
                candidates.append({
                    "event": ev.to_dict() if hasattr(ev, "to_dict") else ev,
                    "status": status,
                    "distance_km": round(dist, 2)
                })

            if getattr(ev, "reference_event_id", None) == target_event_id:
                referencing_events.append({
                    "event": ev.to_dict() if hasattr(ev, "to_dict") else ev,
                    "status": status
                })

        chosen_reference_id = getattr(target_event, "reference_event_id", None)

        response.data = {
            "target_event_id": target_event_id,
            "target_status": target_status,
            "chosen_reference_id": chosen_reference_id,
            "candidates": candidates,
            "referencing_events": referencing_events,
            "examined_nodes": examined_nodes[0]
        }
        response.msg = f"Asociaciones obtenidas para el evento {target_event_id}."
        return response

    # -------------------------------------------------------------------------
    # CONSULTA 4: Eventos de prioridad alta con acceso costoso
    # -------------------------------------------------------------------------
    @staticmethod
    def get_high_priority_costly_access(sismolab: Any, limit_L: Optional[int] = None) -> DataAndMsgReturn:
        response = DataAndMsgReturn()
        scenario = sismolab.get_scenario()

        if limit_L is None:
            limit_L = getattr(scenario, "access_limit", 3) if scenario else 3

        results: List[Any] = []
        examined_nodes = [0]
        avl_tree = sismolab.get_avl_tree()
        root = avl_tree.get_root() if (avl_tree and hasattr(avl_tree, "get_root")) else getattr(avl_tree, "root", None)

        def _traverse_and_check(node, current_depth: int):
            if node is None:
                return

            examined_nodes[0] += 1
            event = node.get_event() if hasattr(node, "get_event") else getattr(node, "event", None)

            if event.priority == 3:
                search_visited_count = QueryService._count_search_steps(root, event.get_key())

                if current_depth > limit_L or search_visited_count > limit_L:
                    results.append({
                        "event": event.to_dict() if hasattr(event, "to_dict") else event,
                        "node_depth": current_depth,
                        "access_limit_L": limit_L,
                        "search_visited_nodes": search_visited_count
                    })

            left_child = node.get_left() if hasattr(node, "get_left") else getattr(node, "left", None)
            right_child = node.get_right() if hasattr(node, "get_right") else getattr(node, "right", None)

            _traverse_and_check(left_child, current_depth + 1)
            _traverse_and_check(right_child, current_depth + 1)

        _traverse_and_check(root, current_depth=0)

        response.data = {
            "costly_high_priority_events": results,
            "access_limit_L": limit_L,
            "total_found": len(results),
            "examined_nodes": examined_nodes[0]
        }
        response.msg = f"Se encontraron {len(results)} eventos de alta prioridad con acceso costoso (L={limit_L})."
        return response

    @staticmethod
    def _count_search_steps(root: Any, target_key: Tuple[int, float, int]) -> int:
        """Simula la búsqueda por clave K e indica la cantidad de pasos desde la raíz."""
        current = root
        visited = 0

        while current is not None:
            visited += 1
            event = current.get_event() if hasattr(current, "get_event") else getattr(current, "event", None)
            current_key = event.get_key()

            if target_key == current_key:
                break
            elif target_key < current_key:
                current = current.get_left() if hasattr(current, "get_left") else getattr(current, "left", None)
            else:
                current = current.get_right() if hasattr(current, "get_right") else getattr(current, "right", None)

        return visited