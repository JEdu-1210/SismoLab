import os
from pathlib import Path
from datetime import datetime
from typing import Any, List, Dict, Optional

from src.utils.Files import Files
from src.models.Returnings import BaseReturn, DataAndMsgReturn
from src.models.Version import Version
from src.services.persistencia import PersistenceService
from src.models.Event import Event
from src.models.report import Report


class VersionService:
  

    def __init__(self, storage_dir: str = "data/versions"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_filepath(self, version_name: str) -> str:
        """Helper to generate a safe filename path for a version."""
        safe_filename = "".join(c for c in version_name if c.isalnum() or c in ("_", "-")).rstrip()
        return str(self.storage_dir / f"{safe_filename}.json")

    def create_version(self, name: str, description: str, sismolab: Any) -> BaseReturn:
        """
        Captures the current operational state of SismoLab (excluding undo stack)
        and persists it to disk as a named version.
        """
        response = BaseReturn()

        if not name or not name.strip():
            response.ok = False
            response.error = "Version name cannot be empty."
            return response

        filepath = self._get_filepath(name)

        current_state = PersistenceService.export_state(sismolab)

        version_data = {
            "name": name.strip(),
            "description": description.strip(),
            "created_at": datetime.now().isoformat(),
            "state": current_state
        }

        save_result = Files.write_json(filepath, version_data)
        if not save_result.ok:
            response.ok = False
            response.error = f"Failed to save version file: {save_result.error}"
            return response

        response.ok = True
        return response

    def list_versions(self) -> DataAndMsgReturn:
        """
        Scans the versions directory and returns a list of all saved versions metadata.
        """
        response = DataAndMsgReturn()
        versions_list: List[Dict[str, Any]] = []

        try:
            for file_path in self.storage_dir.glob("*.json"):
                read_res = Files.read_json(str(file_path))
                if read_res.data:
                    data = read_res.data
                    versions_list.append({
                        "name": data.get("name", file_path.stem),
                        "description": data.get("description", ""),
                        "created_at": data.get("created_at", ""),
                        "filename": file_path.name
                    })

            response.data = versions_list
            response.msg = f"Found {len(versions_list)} saved version(s)."
        except Exception as e:
            response.error = str(e)

        return response

    def restore_version(self, name: str, sismolab: Any) -> DataAndMsgReturn:
        """
        Loads a saved version JSON from disk and restores SismoLab's operational state.
        """
        response = DataAndMsgReturn()
        filepath = self._get_filepath(name)

        if not Files.file_exists(filepath):
            response.msg = f"Version '{name}' does not exist on disk."
            return response

        read_res = Files.read_json(filepath)
        if not read_res.data:
            response.error = read_res.error or f"Failed to read version file '{name}'."
            return response

        version_data = read_res.data
        state_dict = version_data.get("state", {})

        try:
            self._apply_state(sismolab, state_dict)
            response.data = version_data
            response.msg = f"Successfully restored version '{name}'."
        except Exception as e:
            response.error = f"Error during state restoration: {str(e)}"

        return response

    def delete_version(self, name: str) -> BaseReturn:
        """
        Deletes a saved version file from disk.
        """
        response = BaseReturn()
        filepath = Path(self._get_filepath(name))

        if not filepath.is_file():
            response.ok = False
            response.error = f"Version file '{name}' not found."
            return response

        try:
            filepath.unlink()
            response.ok = True
        except Exception as e:
            response.ok = False
            response.error = str(e)

        return response

    def _apply_state(self, sismolab: Any, state_dict: dict) -> None:
        """
        Rebuilds live objects and references within SismoLab from a state dictionary.
        """
        if not state_dict:
            return

        sismolab.clock = state_dict.get("clock", getattr(sismolab, "clock", 0))
        sismolab.deleted_ids = set(state_dict.get("deleted_ids", []))
        sismolab.associations = state_dict.get("associations", [])

        if hasattr(sismolab, "report_queue") and "report_queue" in state_dict:
            if hasattr(sismolab.report_queue, "clear"):
                sismolab.report_queue.clear()
            for r_dict in state_dict["report_queue"]:
                sismolab.report_queue.enqueue(Report.from_dict(r_dict))

        if "history" in state_dict:
            sismolab.history = [Event.from_dict(e) for e in state_dict["history"]]

        if hasattr(sismolab, "avl_tree") and "active_tree_topology" in state_dict:
            from src.structures.AVLNode import AVLNode
            sismolab.avl_tree.root = PersistenceService.rebuild_tree_from_topology(
                state_dict["active_tree_topology"], 
                AVLNode
            )