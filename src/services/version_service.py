import os
from pathlib import Path
from datetime import datetime
from typing import Any, List, Dict, Optional

from src.utils.Files import Files
from src.models.Returnings import BaseReturn, DataAndMsgReturn
from src.models.Version import Version
from src.services.persistencia import PersistenceService
from src.models.Event import Event
from src.models.Report import Report


class VersionService:

    def __init__(self, storage_dir: str = "data/versions"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_filepath(self, version_name: str) -> str:
        """Helper para generar un nombre de archivo seguro en disco."""
        safe_filename = "".join(c for c in version_name if c.isalnum() or c in ("_", "-")).rstrip()
        return str(self.storage_dir / f"{safe_filename}.json")

    def create_version(self, name: str, description: str, sismolab: Any) -> BaseReturn:
        """
        Captura el estado operativo actual de SismoLab (excluyendo la pila de undo)
        y lo persiste en disco como una versión nombrada.
        """
        response = BaseReturn()

        if not name or not name.strip():
            response.ok = False
            response.error = "El nombre de la versión no puede estar vacío."
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
            response.error = f"Error al guardar el archivo de versión: {save_result.error}"
            return response

        response.ok = True
        return response

    def list_versions(self) -> DataAndMsgReturn:
        """
        Escanea el directorio de versiones y retorna la lista de metadatos almacenados.
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
            response.msg = f"Se encontraron {len(versions_list)} versión(es) guardada(s)."
        except Exception as e:
            response.error = str(e)

        return response

    def restore_version(self, name: str, sismolab: Any) -> DataAndMsgReturn:
        """
        Carga una versión JSON desde el disco y restaura el estado operativo.
        Registra la restauración en la pila de deshacer para cumplir el Punto 13.
        """
        response = DataAndMsgReturn()
        filepath = self._get_filepath(name)

        if not Files.file_exists(filepath):
            response.msg = f"La versión '{name}' no existe en disco."
            return response

        read_res = Files.read_json(filepath)
        if not read_res.data:
            response.error = read_res.error or f"Error al leer el archivo de la versión '{name}'."
            return response

        version_data = read_res.data
        state_dict = version_data.get("state", {})

        try:
            # 1. Registrar snapshot previo en Undo para permitir deshacer la restauración
            if hasattr(sismolab, "_record_undo"):
                sismolab._record_undo("RESTORE_VERSION", f"Restaurar versión guardada '{name}'")

            # 2. Aplicar estado recuperado
            self._apply_state(sismolab, state_dict)
            response.data = version_data
            response.msg = f"Versión '{name}' restaurada exitosamente."
        except Exception as e:
            response.error = f"Error durante la restauración del estado: {str(e)}"

        return response

    def delete_version(self, name: str) -> BaseReturn:
        """Elimina el archivo de una versión guardada en disco."""
        response = BaseReturn()
        filepath = Path(self._get_filepath(name))

        if not filepath.is_file():
            response.ok = False
            response.error = f"Archivo de versión '{name}' no encontrado."
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
        Reconstruye los objetos vivos e indicadores dentro de SismoLab respetando la encapsulación.
        """
        if not state_dict:
            return

        scenario = sismolab.get_scenario() if hasattr(sismolab, "get_scenario") else getattr(sismolab, "scenario", None)

        # 1. Reloj, Modo Estrés y Parámetros en Scenario
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

        # 2. Identificadores Retirados
        retired_ids = set(state_dict.get("retired_ids", state_dict.get("deleted_ids", [])))
        if hasattr(sismolab, "_retired_ids"):
            sismolab._retired_ids = retired_ids

        # 3. Asociaciones
        if "associations" in state_dict and hasattr(sismolab, "_associations"):
            sismolab._associations = state_dict["associations"]

        # 4. Cola FIFO de Reportes
        report_queue = sismolab.get_report_queue() if hasattr(sismolab, "get_report_queue") else getattr(sismolab, "report_queue", None)
        if report_queue and "report_queue" in state_dict:
            if hasattr(report_queue, "clear"):
                report_queue.clear()
            for r_dict in state_dict["report_queue"]:
                report_obj = Report.from_dict(r_dict) if hasattr(Report, "from_dict") else Report(**r_dict)
                report_queue.enqueue(report_obj)

        # 5. Histórico
        history_obj = sismolab.get_history() if hasattr(sismolab, "get_history") else getattr(sismolab, "history", None)
        if history_obj and "history" in state_dict:
            if hasattr(history_obj, "load_from_dict"):
                history_obj.load_from_dict(state_dict["history"])
            elif hasattr(history_obj, "clear"):
                history_obj.clear()
                for e_dict in state_dict["history"]:
                    history_obj.add_event(Event.from_dict(e_dict) if hasattr(Event, "from_dict") else Event(**e_dict))

        # 6. Reconstrucción de la Topología AVL
        avl_tree = sismolab.get_avl_tree() if hasattr(sismolab, "get_avl_tree") else getattr(sismolab, "avl_tree", None)
        if avl_tree and ("active_tree_topology" in state_dict or "active_topology" in state_dict):
            topology_data = state_dict.get("active_tree_topology") or state_dict.get("active_topology")
            from src.structures.AVLNode import AVLNode
            reconstructed_root = PersistenceService.rebuild_tree_from_topology(topology_data, AVLNode)

            if hasattr(avl_tree, "set_root"):
                avl_tree.set_root(reconstructed_root)
            else:
                avl_tree.root = reconstructed_root