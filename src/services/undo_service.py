from typing import Any, Optional
from src.structures.Stack import Stack
from src.models.UndoAction import UndoAction
from src.models.Returnings import DataAndMsgReturn
from src.services.persistencia import PersistenceService
from src.models.Event import Event
from src.models.Report import Report


class UndoService:

    def __init__(self):
        self.undo_stack: Stack = Stack()

    def record_action(self, action_type: str, description: str, sismolab: Any) -> None:
        """
        Captura una foto completa del estado de SismoLab ANTES de aplicar un cambio.
        """
        previous_state = PersistenceService.export_state(sismolab)

        action = UndoAction(
            action_type=action_type,
            description=description,
            previous_state=previous_state
        )

        self.undo_stack.push(action)

    def can_undo(self) -> bool:
        """Comprueba si hay acciones disponibles en la pila."""
        return not self.undo_stack.is_empty()

    def undo(self, sismolab: Any) -> DataAndMsgReturn:
        """Extrae el último estado y lo restaura en SismoLab."""
        response = DataAndMsgReturn()

        if not self.can_undo():
            response.msg = "No hay acciones operativas disponibles para deshacer."
            return response

        try:
            last_action: UndoAction = self.undo_stack.pop()

            self._restore_snapshot(sismolab, last_action.previous_state)

            response.data = last_action
            response.msg = f"Acción deshecha exitosamente: '{last_action.description}'"

        except Exception as e:
            response.error = str(e)

        return response

    def _restore_snapshot(self, sismolab: Any, state_dict: dict) -> None:
        """Restaura los atributos de SismoLab garantizando la reversibilidad completa."""
        if not state_dict:
            return

        scenario = sismolab.get_scenario() if hasattr(sismolab, "get_scenario") else getattr(sismolab, "scenario", None)

        # 1. Restaurar Reloj, Parámetros (W, R, L, T) y Modo Estrés en el Escenario
        if scenario:
            if "clock" in state_dict and hasattr(scenario, "set_simulation_clock"):
                scenario.set_simulation_clock(state_dict["clock"])

            if "stress_mode" in state_dict and hasattr(scenario, "set_stress_mode"):
                scenario.set_stress_mode(state_dict["stress_mode"])

            params = state_dict.get("parameters", {})
            if params:
                if "w_hours" in params: scenario.w_hours = float(params["w_hours"])
                if "r_km" in params: scenario.r_km = float(params["r_km"])
                if "access_limit_L" in params and hasattr(scenario, "set_access_limit"):
                    scenario.set_access_limit(int(params["access_limit_L"]))
                if "archive_age_T" in params: scenario.archive_age_hours = float(params["archive_age_T"])

        # 2. Restaurar IDs retirados/eliminados
        retired_ids = set(state_dict.get("retired_ids", state_dict.get("deleted_ids", [])))
        if hasattr(sismolab, "_retired_ids"):
            sismolab._retired_ids = retired_ids
        elif hasattr(sismolab, "retired_ids"):
            sismolab.retired_ids = retired_ids

        # 3. Restaurar Asociaciones
        if "associations" in state_dict:
            if hasattr(sismolab, "_associations"):
                sismolab._associations = state_dict["associations"]

        # 4. Restaurar Métricas e Indicadores
        if "metrics" in state_dict:
            metrics_obj = sismolab.get_metrics() if hasattr(sismolab, "get_metrics") else getattr(sismolab, "metrics", None)
            if metrics_obj:
                if hasattr(metrics_obj, "load_summary"):
                    metrics_obj.load_summary(state_dict["metrics"])
                elif hasattr(metrics_obj, "from_dict"):
                    sismolab._metrics = metrics_obj.from_dict(state_dict["metrics"])

        # 5. Restaurar Cola FIFO de Reportes
        report_queue = sismolab.get_report_queue() if hasattr(sismolab, "get_report_queue") else getattr(sismolab, "report_queue", None)
        if report_queue and "report_queue" in state_dict:
            if hasattr(report_queue, "clear"):
                report_queue.clear()
            for r_dict in state_dict["report_queue"]:
                report_obj = Report.from_dict(r_dict) if hasattr(Report, "from_dict") else Report(**r_dict)
                report_queue.enqueue(report_obj)

        # 6. Restaurar Histórico
        history_obj = sismolab.get_history() if hasattr(sismolab, "get_history") else getattr(sismolab, "history", None)
        if history_obj and "history" in state_dict:
            if hasattr(history_obj, "load_from_dict"):
                history_obj.load_from_dict(state_dict["history"])
            elif hasattr(history_obj, "clear"):
                history_obj.clear()
                for e_dict in state_dict["history"]:
                    history_obj.add_event(Event.from_dict(e_dict) if hasattr(Event, "from_dict") else Event(**e_dict))

        # 7. Reconstruir Topología del Árbol AVL Activo
        avl_tree = sismolab.get_avl_tree() if hasattr(sismolab, "get_avl_tree") else getattr(sismolab, "avl_tree", None)
        if avl_tree and ("active_tree_topology" in state_dict or "active_topology" in state_dict):
            topology_data = state_dict.get("active_tree_topology") or state_dict.get("active_topology")
            from src.structures.AVLNode import AVLNode
            reconstructed_root = PersistenceService.rebuild_tree_from_topology(topology_data, AVLNode)
            
            if hasattr(avl_tree, "set_root"):
                avl_tree.set_root(reconstructed_root)
            else:
                avl_tree.root = reconstructed_root