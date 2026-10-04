from typing import Any, Dict, List, Optional, Tuple
from src.models.Event import Event
from src.models.Report import Report
from src.models.Returnings import DataAndMsgReturn
from src.services.audit_service import AuditService


class QueueProcessingService:
    """
    Servicio encargado de procesar la cola FIFO de reportes en ráfaga (Punto 8)
    y ejecutar la recuperación global in-place en Modo Estrés.
    """

    # -------------------------------------------------------------------------
    # 1. PROCESAR SIGUIENTE REPORTE DE LA COLA (Paso a paso)
    # -------------------------------------------------------------------------
    @staticmethod
    def process_next_report(sismolab: Any) -> DataAndMsgReturn:
        response = DataAndMsgReturn()
        report_queue = sismolab.get_report_queue()

        if report_queue.is_empty():
            response.error = "La cola de reportes está vacía."
            return response

        # Registrar foto en Undo antes de realizar cambios
        QueueProcessingService._record_undo(sismolab, "PROCESS_REPORT", "Procesamiento de reporte desde la cola FIFO")

        report: Report = report_queue.dequeue()
        scenario = sismolab.get_scenario()
        is_stress = scenario.is_stress_mode() if hasattr(scenario, "is_stress_mode") else getattr(scenario, "stress_mode", False)
        metrics = sismolab.get_metrics()
        avl_tree = sismolab.get_avl_tree()

        # Validar si el identificador pertenece a un evento eliminado/retirado
        if sismolab.is_retired_id(report.identifier):
            report.decision = "DESCARTADO_EVENTO_ELIMINADO"
            if hasattr(metrics, "increment_discarded_reports"):
                metrics.increment_discarded_reports()
            response.msg = f"Reporte para ID {report.identifier} descartado: el evento fue ELIMINADO."
            response.data = {"report": report.to_dict(), "decision": report.decision}
            return response

        # Buscar si el evento ya existe en el árbol activo AVL
        existing_node = avl_tree.search_by_id(report.identifier) if hasattr(avl_tree, "search_by_id") else None
        existing_event = (existing_node.get_event() if hasattr(existing_node, "get_event") else existing_node.event) if existing_node else None

        rotations_made = []
        decision = ""

        if existing_event is None:
            # -----------------------------------------------------------------
            # SITUACIÓN: Identificador desconocido -> Crear nuevo evento
            # -----------------------------------------------------------------
            new_event = Event(
                identifier=report.identifier,
                magnitude=report.magnitude,
                depth=report.depth,
                x=report.x,
                y=report.y,
                date_time=report.date_time,
                revision=report.revision,
                priority=1,
                is_populated_zone=False
            )
            
            # Actualizar zona poblada y prioridad P según escenario
            zones = scenario.get_zones() if hasattr(scenario, "get_zones") else getattr(scenario, "zones", [])
            new_event.update_zone_and_priority(zones)
            station_name = report.station.name if hasattr(report.station, "name") else str(report.station)
            new_event.add_accepted_station(station_name)

            if is_stress:
                # En Modo Estrés: Inserción estilo BST simple (sin rotaciones)
                QueueProcessingService._insert_bst_unbalanced(avl_tree, new_event)
                decision = f"NUEVO EVENTO CREADO (Modo Estrés - Rotaciones Aplazadas) [ID {new_event.identifier}]"
            else:
                # En Modo Normal: Inserción AVL con balanceo
                rotations_made = avl_tree.insert(new_event)
                decision = f"NUEVO EVENTO CREADO E INSERTADO EN AVL [ID {new_event.identifier}]"

            report.event = new_event
            report.decision = "ACEPTADO_NUEVO_EVENTO"

        else:
            # -----------------------------------------------------------------
            # SITUACIÓN: Identificador conocido -> Evaluación de revisiones y datos
            # -----------------------------------------------------------------
            current_rev = existing_event.revision
            rep_rev = report.revision

            if rep_rev < current_rev:
                # Revisión menor que la vigente -> Descartar por antiguo
                decision = f"REPORTE DESCARTADO (Antiguo): Rev. {rep_rev} < Rev. vigente {current_rev}"
                report.decision = "DESCARTADO_REVISION_ANTIGUA"
                if hasattr(metrics, "increment_discarded_reports"):
                    metrics.increment_discarded_reports()

            elif rep_rev == current_rev:
                # Comparación de datos del sismo
                same_data = (
                    existing_event.magnitude == report.magnitude and
                    existing_event.depth == report.depth and
                    existing_event.x == report.x and
                    existing_event.y == report.y and
                    str(existing_event.date_time) == str(report.date_time)
                )

                if same_data:
                    # Igual revisión e iguales datos -> Confirmación y añadir estación
                    station_name = report.station.name if hasattr(report.station, "name") else str(report.station)
                    existing_event.add_accepted_station(station_name)
                    decision = f"CONFIRMACIÓN ACEPTADA: Estación '{station_name}' añadida al evento {existing_event.identifier}"
                    report.decision = "CONFIRMACION_ACEPTADA"
                else:
                    # Igual revisión y datos distintos -> Conflicto detectado
                    decision = f"CONFLICTO DETECTADO: Rev. {rep_rev} coincide pero los datos difieren. Reporte rechazado."
                    report.decision = "CONFLICTO_RECHAZADO"
                    if hasattr(metrics, "increment_conflicts"):
                        metrics.increment_conflicts()

            else:
                # Revisión mayor que la vigente -> Sustituir datos
                old_key = existing_event.get_key()

                existing_event.magnitude = report.magnitude
                existing_event.depth = report.depth
                existing_event.x = report.x
                existing_event.y = report.y
                existing_event.date_time = report.date_time
                existing_event.revision = rep_rev
                existing_event.mark_as_pending()

                zones = scenario.get_zones() if hasattr(scenario, "get_zones") else getattr(scenario, "zones", [])
                existing_event.update_zone_and_priority(zones)
                station_name = report.station.name if hasattr(report.station, "name") else str(report.station)
                existing_event.add_accepted_station(station_name)

                new_key = existing_event.get_key()

                # Si cambió la clave K = (P, M, I), se reubica el nodo
                if old_key != new_key:
                    avl_tree.delete_by_key(old_key)
                    if is_stress:
                        QueueProcessingService._insert_bst_unbalanced(avl_tree, existing_event)
                    else:
                        rotations_made = avl_tree.insert(existing_event)
                    decision = f"CORRECCIÓN ACEPTADA: Clave reubicada {old_key} -> {new_key}"
                else:
                    decision = f"CORRECCIÓN ACEPTADA: Datos actualizados sin cambio de clave [ID {existing_event.identifier}]"

                report.event = existing_event
                report.decision = "CORRECCION_ACEPTADA"
                if hasattr(metrics, "increment_accepted_corrections"):
                    metrics.increment_accepted_corrections()

        response.data = {
            "station": report.station.name if hasattr(report.station, "name") else str(report.station),
            "event_id": report.identifier,
            "revision": report.revision,
            "decision": decision,
            "rotations": rotations_made,
            "is_stress_mode": is_stress
        }
        response.msg = f"Paso completado: {decision}"
        return response

    # -------------------------------------------------------------------------
    # 2. RECUPERACIÓN GLOBAL DEL AVL (Re-balanceo In-Place)
    # -------------------------------------------------------------------------
    @staticmethod
    def recover_avl_balance(sismolab: Any) -> DataAndMsgReturn:
        response = DataAndMsgReturn()
        avl_tree = sismolab.get_avl_tree()

        if avl_tree.root is None:
            response.msg = "El árbol está vacío. No requiere re-balanceo."
            return response

        total_rotations = {"LL": 0, "RR": 0, "LR": 0, "RL": 0}
        metrics = sismolab.get_metrics()

        loop_count = 0
        max_loops = 100

        while loop_count < max_loops:
            unbalanced_found, pass_summary = QueueProcessingService._rebalance_pass(avl_tree)
            
            for case_type in pass_summary.get("cases", []):
                if case_type in total_rotations:
                    total_rotations[case_type] += 1
                if hasattr(metrics, "register_rotation"):
                    metrics.register_rotation(case_type)

            if not unbalanced_found:
                break
            loop_count += 1

        # Auditoría previa para confirmar equilibrio total
        audit_res = AuditService.verify_structure(sismolab)
        
        if audit_res.data.get("is_valid", False):
            scenario = sismolab.get_scenario()
            if hasattr(scenario, "set_stress_mode"):
                scenario.set_stress_mode(False)
            elif hasattr(scenario, "stress_mode"):
                scenario.stress_mode = False

            response.data = {
                "recovery_completed": True,
                "passes_required": loop_count + 1,
                "total_rotations": total_rotations
            }
            response.msg = "Recuperación global exitosa. Árbol equilibrado y Modo Normal activado."
        else:
            response.error = "Error en la recuperación: La auditoría detectó desbalance o inconsistencias de orden restantes."
            response.data = audit_res.data

        return response

    # -------------------------------------------------------------------------
    # MÉTODOS AUXILIARES ESTRUCTURALES Y UNDO
    # -------------------------------------------------------------------------
    @staticmethod
    def _insert_bst_unbalanced(tree: Any, event: Event) -> None:
        """Inserta conservando el orden de K pero sin aplicar rotaciones AVL."""
        from src.structures.AVLNode import AVLNode
        new_node = AVLNode(event=event)

        if tree.root is None:
            tree.root = new_node
            return

        curr = tree.root
        target_key = event.get_key()

        while True:
            curr_event = curr.get_event() if hasattr(curr, "get_event") else curr.event
            curr_key = curr_event.get_key()

            if target_key < curr_key:
                left = curr.left if hasattr(curr, "left") else getattr(curr, "get_left")()
                if left is None:
                    if hasattr(curr, "set_left"): curr.set_left(new_node)
                    else: curr.left = new_node
                    break
                curr = left
            else:
                right = curr.right if hasattr(curr, "right") else getattr(curr, "get_right")()
                if right is None:
                    if hasattr(curr, "set_right"): curr.set_right(new_node)
                    else: curr.right = new_node
                    break
                curr = right

        QueueProcessingService._update_heights(tree.root)

    @staticmethod
    def _rebalance_pass(tree: Any) -> Tuple[bool, dict]:
        """Recorre el árbol en Post-Order aplicando rotaciones AVL locales donde |FB| > 1."""
        rotations_summary = {"cases": []}
        unbalanced_node_found = [False]

        def _post_order_rebalance(node):
            if node is None:
                return None

            left = node.left if hasattr(node, "left") else getattr(node, "get_left", lambda: None)()
            right = node.right if hasattr(node, "right") else getattr(node, "get_right", lambda: None)()

            new_left = _post_order_rebalance(left)
            new_right = _post_order_rebalance(right)

            if hasattr(node, "set_left"): node.set_left(new_left)
            else: node.left = new_left

            if hasattr(node, "set_right"): node.set_right(new_right)
            else: node.right = new_right

            h_left = AuditService.calculate_node_height(new_left)
            h_right = AuditService.calculate_node_height(new_right)
            node.height = 1 + max(h_left, h_right)

            fb = h_left - h_right

            if fb > 1:
                unbalanced_node_found[0] = True
                left_sub = new_left.left if hasattr(new_left, "left") else getattr(new_left, "get_left", lambda: None)()
                right_sub = new_left.right if hasattr(new_left, "right") else getattr(new_left, "get_right", lambda: None)()
                left_fb = AuditService.calculate_node_height(left_sub) - AuditService.calculate_node_height(right_sub)

                if left_fb >= 0:
                    rotations_summary["cases"].append("LL")
                    return tree.rotate_right(node) if hasattr(tree, "rotate_right") else node
                else:
                    rotations_summary["cases"].append("LR")
                    return tree.rotate_left_right(node) if hasattr(tree, "rotate_left_right") else node

            elif fb < -1:
                unbalanced_node_found[0] = True
                left_sub = new_right.left if hasattr(new_right, "left") else getattr(new_right, "get_left", lambda: None)()
                right_sub = new_right.right if hasattr(new_right, "right") else getattr(new_right, "get_right", lambda: None)()
                right_fb = AuditService.calculate_node_height(left_sub) - AuditService.calculate_node_height(right_sub)

                if right_fb <= 0:
                    rotations_summary["cases"].append("RR")
                    return tree.rotate_left(node) if hasattr(tree, "rotate_left") else node
                else:
                    rotations_summary["cases"].append("RL")
                    return tree.rotate_right_left(node) if hasattr(tree, "rotate_right_left") else node

            return node

        tree.root = _post_order_rebalance(tree.root)
        return unbalanced_node_found[0], rotations_summary

    @staticmethod
    def _update_heights(node: Any) -> int:
        if node is None:
            return -1
        left = node.left if hasattr(node, "left") else getattr(node, "get_left", lambda: None)()
        right = node.right if hasattr(node, "right") else getattr(node, "get_right", lambda: None)()
        node.height = 1 + max(QueueProcessingService._update_heights(left), QueueProcessingService._update_heights(right))
        return node.height

    @staticmethod
    def _record_undo(sismolab: Any, action_type: str, description: str):
        from src.services.persistencia import PersistenceService
        from src.models.UndoAction import UndoAction

        snapshot = PersistenceService.export_state(sismolab)
        action = UndoAction(action_type=action_type, description=description, previous_state=snapshot)
        sismolab.get_undo_stack().push(action)