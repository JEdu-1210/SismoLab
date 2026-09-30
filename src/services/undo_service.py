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
        Captures a complete snapshot of SismoLab's current state BEFORE executing a change,
        encapsulates it in an UndoAction, and pushes it onto the Stack.
        """
        previous_state = PersistenceService.export_state(sismolab)

        action = UndoAction(
            action_type=action_type,
            description=description,
            previous_state=previous_state
        )

        self.undo_stack.push(action)

    def can_undo(self) -> bool:
        """
        Checks if there are actions available to roll back in the stack.
        """
        return not self.undo_stack.is_empty()

    def undo(self, sismolab: Any) -> DataAndMsgReturn:
        """
        Pops the last UndoAction from the stack and restores SismoLab to its previous state.
        """
        response = DataAndMsgReturn()

        if not self.can_undo():
            response.msg = "No operational actions available to undo."
            return response

        try:
            last_action: UndoAction = self.undo_stack.pop()

            self._restore_snapshot(sismolab, last_action.previous_state)

            response.data = last_action
            response.msg = f"Successfully undid action: '{last_action.description}'"

        except Exception as e:
            response.error = str(e)

        return response

    def _restore_snapshot(self, sismolab: Any, state_dict: dict) -> None:
        """
        Reconstructs the live SismoLab attributes using the saved state snapshot.
        """
        if not state_dict:
            return

        sismolab.clock = state_dict.get("clock", getattr(sismolab, "clock", 0))
        sismolab.deleted_ids = set(state_dict.get("deleted_ids", []))
        sismolab.associations = state_dict.get("associations", [])

        if hasattr(sismolab, "report_queue") and "report_queue" in state_dict:
            sismolab.report_queue.clear() if hasattr(sismolab.report_queue, "clear") else None
            for r_dict in state_dict["report_queue"]:
                report_obj = Report.from_dict(r_dict)
                sismolab.report_queue.enqueue(report_obj)

        if "history" in state_dict:
            sismolab.history = [Event.from_dict(e_dict) for e_dict in state_dict["history"]]

        if hasattr(sismolab, "avl_tree") and "active_tree_topology" in state_dict:
            from src.structures.AVLNode import AVLNode
            sismolab.avl_tree.root = PersistenceService.rebuild_tree_from_topology(
                state_dict["active_tree_topology"], 
                AVLNode
            )