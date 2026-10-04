from typing import List, Dict, Any, Tuple, Optional
from src.models.Returnings import DataAndMsgReturn


class AuditService:
    """
    Servicio de auditoría estructural para el árbol AVL (Sección 14).
    Comprueba orden global por K = (P, M, I), unicidad de IDs,
    alturas recalculadas (-1 vacío, 0 hoja) y factores de balance (FB = h_izq - h_der).
    """

    @staticmethod
    def calculate_node_height(node: Any) -> int:
        """
        Calcula la altura real de un nodo recursivamente.
        Convención del proyecto: Árbol vacío = -1, Hoja = 0.
        """
        if node is None:
            return -1
        left_node = node.left if hasattr(node, "left") else getattr(node, "get_left", lambda: None)()
        right_node = node.right if hasattr(node, "right") else getattr(node, "get_right", lambda: None)()
        return 1 + max(
            AuditService.calculate_node_height(left_node),
            AuditService.calculate_node_height(right_node)
        )

    @staticmethod
    def verify_structure(sismolab: Any) -> DataAndMsgReturn:
        """
        Ejecuta la auditoría global sobre el árbol AVL activo de SismoLab.
        Retorna un informe estructurado con el estado de validez y las observaciones.
        """
        response = DataAndMsgReturn()
        report_errors: List[Dict[str, Any]] = []
        visited_ids = set()

        avl_tree = sismolab.get_avl_tree() if hasattr(sismolab, "get_avl_tree") else getattr(sismolab, "avl_tree", None)
        root = avl_tree.root if avl_tree else None

        scenario = sismolab.get_scenario() if hasattr(sismolab, "get_scenario") else getattr(sismolab, "scenario", None)
        is_stress = scenario.is_stress_mode() if (scenario and hasattr(scenario, "is_stress_mode")) else getattr(scenario, "stress_mode", False) if scenario else getattr(sismolab, "is_stress_mode", False)

        if root is not None:
            AuditService._audit_node(
                node=root,
                min_key=None,
                max_key=None,
                visited_ids=visited_ids,
                is_stress_mode=is_stress,
                report_errors=report_errors
            )

        critical_errors = [e for e in report_errors if e["type"] in ("ORDER_ERROR", "METADATA_ERROR")]

        response.data = {
            "is_valid": len(critical_errors) == 0,
            "is_stress_mode": is_stress,
            "total_inconsistencies": len(report_errors),
            "errors": report_errors
        }
        response.msg = f"Auditoría finalizada. Se encontraron {len(report_errors)} observación(es)."
        return response

    @staticmethod
    def _audit_node(
        node: Any,
        min_key: Optional[Tuple],
        max_key: Optional[Tuple],
        visited_ids: set,
        is_stress_mode: bool,
        report_errors: List[Dict[str, Any]]
    ) -> int:
        if node is None:
            return -1

        event = node.event if hasattr(node, "event") else node.get_event()
        event_id = event.identifier
        key = event.get_key()

        # 1. Comprobar Unicidad / Ausencia de Ciclos
        if event_id in visited_ids:
            report_errors.append({
                "event_id": event_id,
                "type": "METADATA_ERROR",
                "description": f"ID de evento duplicado o ciclo detectado en el árbol: ID {event_id}"
            })
            return -1
        visited_ids.add(event_id)

        # 2. Comprobar Orden Global BST por K = (P, M, I)
        if min_key and key <= min_key:
            report_errors.append({
                "event_id": event_id,
                "type": "ORDER_ERROR",
                "description": f"Violación de orden BST: Clave {key} <= límite inferior {min_key}"
            })
        if max_key and key >= max_key:
            report_errors.append({
                "event_id": event_id,
                "type": "ORDER_ERROR",
                "description": f"Violación de orden BST: Clave {key} >= límite superior {max_key}"
            })

        left_node = node.left if hasattr(node, "left") else getattr(node, "get_left", lambda: None)()
        right_node = node.right if hasattr(node, "right") else getattr(node, "get_right", lambda: None)()

        h_left = AuditService._audit_node(left_node, min_key, key, visited_ids, is_stress_mode, report_errors)
        h_right = AuditService._audit_node(right_node, key, max_key, visited_ids, is_stress_mode, report_errors)

        # 3. Recalcular Altura Real y Factor de Balance (FB = h_izq - h_der)
        real_height = 1 + max(h_left, h_right)
        balance_factor = h_left - h_right

        stored_height = getattr(node, "height", None)
        if stored_height is not None and stored_height != real_height:
            report_errors.append({
                "event_id": event_id,
                "type": "METADATA_ERROR",
                "description": f"Altura guardada ({stored_height}) != altura calculada ({real_height})"
            })

        # 4. Validar Factor de Balance según el modo de ejecución
        if balance_factor not in (-1, 0, 1):
            if is_stress_mode:
                report_errors.append({
                    "event_id": event_id,
                    "type": "EXPECTED_UNBALANCE",
                    "description": f"Nodo desbalanceado (FB={balance_factor}) esperado en Modo Estrés."
                })
            else:
                report_errors.append({
                    "event_id": event_id,
                    "type": "METADATA_ERROR",
                    "description": f"Violación de balanceo AVL en Modo Normal: Factor de Balance = {balance_factor}"
                })

        return real_height