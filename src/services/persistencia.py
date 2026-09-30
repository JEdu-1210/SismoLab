from typing import Dict, Any, List, Optional
from src.utils.Files import Files
from src.models.Returnings import BaseReturn, DataAndMsgReturn
from src.models.Event import Event
from src.models.report import Report
from src.models.station import Station
from src.models.zone import Zone
from src.models.Scenario import Scenario


class Persistencia:

    @staticmethod
    def export_state(sismoLab: Any) -> Dict[str,Any]:

        return {
            "scenario": sismoLab.scenario.to_dict() if hasattr(sismoLab, "scenario") and sismoLab.scenario else None,
            "clock": getattr(sismoLab, 'clock', 0),
            "zones": [zone.to_dict() for zone in sismoLab.zones] if hasattr(sismoLab, 'zones') else [],
            "stations": [station.to_dict() for station in sismoLab.stations] if hasattr(sismoLab, 'stations') else [],
            "deleted_ids": list(sismoLab.deleted_ids) if hasattr(sismoLab, "deleted_ids") else [],
            "associations": getattr(sismoLab, "associations", []),
            "metrics": sismoLab.metrics.to_dict() if hasattr(sismoLab, "metrics") and sismoLab.metrics else {},
            "report_queue": [report.to_dict() for report in sismoLab.report_queue.get_all()] if hasattr(sismoLab, "report_queue") else [],
            "history": [event.to_dict() for event in sismoLab.history] if hasattr(sismoLab, "history") else [],
            "active_tree_topology": Persistencia._serialize_topologia(sismoLab.avl_tree.root) if hasattr(sismoLab, "avl_tree") and sismoLab.avl_tree and sismoLab.avl_tree.root else None,
            "active_tree_events": [node.event.to_dict() for node in sismoLab.avl_tree.in_order()] if hasattr(sismoLab, "avl_tree") and sismoLab.avl_tree else []
        }

    @staticmethod
    def save_state_to_file (filepath: str, sismoLab: Any)-> BaseReturn:
        state_data = Persistencia.export_state(sismoLab)
        return Files.write_json(filepath,state_data)

    @staticmethod
    def read_state_from_file(filepath: str)-> DataAndMsgReturn:
        return Files.read_json(filepath)

    @staticmethod
    def rebuild_tree_from_topology(topology_dict: Optional[Dict[str, Any]], node_class: Any) -> Any:
        if topology_dict is None:
            return None

        event_obj = Event.from_dict(topology_dict["event"])

        node = node_class(event = event_obj)
        node.heigth = topology_dict.get("height",1)

        node.left = Persistencia.rebuild_tree_from_topology(topology_dict.get("left"),node_class)
        node.right = Persistencia.rebuild_tree_from_topology(topology_dict.get("right"), node_class)