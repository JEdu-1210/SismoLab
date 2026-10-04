from typing import Dict, Any, List, Tuple
from src.utils.Files import Files
from src.models.Returnings import BaseReturn, DataAndMsgReturn
from src.models.Event import Event


class PersistenceService:

    @staticmethod
    def load_by_insertions(filepath: str, sismolab: Any, bst_class: Any) -> DataAndMsgReturn:
        response = DataAndMsgReturn()
        read_res = Files.read_json(filepath)

        if not read_res.data:
            response.error = read_res.error or "No se pudo leer el archivo de eventos."
            return response

        data = read_res.data
        events_list = data.get("active_tree_events", data if isinstance(data, list) else [])

        # 1. Validar unicidad de IDs en la secuencia
        seen_ids = set()
        event_objects = []
        for e_dict in events_list:
            e_obj = Event.from_dict(e_dict) if hasattr(Event, "from_dict") else Event(
                identifier=e_dict["identifier"],
                magnitude=e_dict["magnitude"],
                depth=e_dict["depth"],
                x=e_dict["x"],
                y=e_dict["y"],
                date_time=e_dict["date_time"],
                revision=e_dict.get("revision", 1),
                priority=e_dict["priority"],
                is_populated_zone=e_dict.get("is_populated_zone", False)
            )
            if e_obj.identifier in seen_ids:
                response.error = f"Archivo inválido: Se encontró un ID duplicado ({e_obj.identifier}) en la secuencia de carga."
                return response
            seen_ids.add(e_obj.identifier)
            event_objects.append(e_obj)

        # 2. Instanciar árbol BST paralelo (sin balanceo)
        bst_tree = bst_class()

        # 3. Limpiar e insertar en ambos árboles
        if hasattr(sismolab.avl_tree, "clear"):
            sismolab.avl_tree.clear()
        else:
            sismolab.avl_tree.set_root(None)

        for event in event_objects:
            sismolab.avl_tree.insert(event, rebalance=True)
            bst_tree.insert(event)

        # 4. Compilar métricas comparativas usando los métodos reales de AVLTree
        avl_root = sismolab.avl_tree.get_root()
        bst_root = bst_tree.get_root() if hasattr(bst_tree, "get_root") else getattr(bst_tree, "root", None)

        response.data = {
            "avl_metrics": {
                "root_key": avl_root.get_key() if avl_root else None,
                "height": sismolab.avl_tree.height(),
                "max_depth": sismolab.avl_tree.height(),
                "leaf_count": sismolab.avl_tree.leaf_count()
            },
            "bst_metrics": {
                "root_key": bst_root.get_key() if (bst_root and hasattr(bst_root, "get_key")) else None,
                "height": bst_tree.height() if hasattr(bst_tree, "height") else -1,
                "max_depth": bst_tree.height() if hasattr(bst_tree, "height") else -1,
                "leaf_count": bst_tree.leaf_count() if hasattr(bst_tree, "leaf_count") else -1
            }
        }
        response.msg = "Carga por inserciones realizada con éxito en AVL y BST."
        return response

    @staticmethod
    def validate_and_load_topology(filepath: str, sismolab: Any) -> DataAndMsgReturn:
        response = DataAndMsgReturn()
        read_res = Files.read_json(filepath)

        if not read_res.data:
            response.error = read_res.error or "Error al leer el archivo de topología."
            return response

        state_dict = read_res.data
        errors: List[str] = []

        topology_data = state_dict.get("state", {}).get("active_tree_topology") or state_dict.get("active_tree_topology")

        if not topology_data:
            errors.append("El archivo no contiene una estructura 'active_tree_topology' válida.")
        else:
            # Validar orden BST, prioridades, alturas y ausencia de ciclos
            is_valid_order, is_balanced = PersistenceService._validate_topology_node(
                node_dict=topology_data,
                min_key=None,
                max_key=None,
                errors=errors,
                visited_ids=set(),
                sismolab=sismolab
            )

            is_stress = state_dict.get("state", {}).get("stress_mode", False)
            if not is_balanced and not is_stress:
                errors.append("Rechazado: La topología está desbalanceada y el Modo Estrés NO está activado en el archivo.")

        if errors:
            response.error = "Error de validación al cargar topología. Escenario conservado intacto."
            response.data = {"validation_errors": errors}
            return response

        from src.services.version_service import VersionService
        version_srv = VersionService()
        version_srv._apply_state(sismolab, state_dict.get("state", state_dict))

        response.msg = "Topología validada y cargada exitosamente."
        return response

    @staticmethod
    def _validate_topology_node(node_dict: dict, min_key: Any, max_key: Any, errors: List[str], visited_ids: set, sismolab: Any) -> Tuple[bool, bool]:
        if node_dict is None:
            return True, True

        event_dict = node_dict.get("event", {})
        event_id = event_dict.get("identifier")

        # Check de ciclos / duplicados
        if event_id in visited_ids:
            errors.append(f"Ciclo o ID duplicado detectado en la topología: Evento ID {event_id}")
            return False, False
        visited_ids.add(event_id)

        # Check de coherencia entre prioridad almacenada y calculada
        event_service = getattr(sismolab, "_event_service", None)
        if event_service:
            _, calc_p = event_service.calculate_event_data(
                event_dict.get("magnitude", 0),
                event_dict.get("depth", 0),
                event_dict.get("x", 0),
                event_dict.get("y", 0)
            )
            stored_p = event_dict.get("priority")
            if calc_p != stored_p:
                errors.append(f"Prioridad inconsistente en evento SIS-{event_id:06d}: Almacenada={stored_p}, Calculada={calc_p}.")

        # Check de orden de clave K = (P, M, I)
        key = (event_dict.get("priority"), event_dict.get("magnitude"), event_id)
        if min_key and key <= min_key:
            errors.append(f"Violación de orden BST en el nodo {event_id}: clave {key} <= min_key {min_key}")
        if max_key and key >= max_key:
            errors.append(f"Violación de orden BST en el nodo {event_id}: clave {key} >= max_key {max_key}")

        # Recursión en subárboles
        left_valid, left_balanced = PersistenceService._validate_topology_node(
            node_dict.get("left"), min_key, key, errors, visited_ids, sismolab
        )
        right_valid, right_balanced = PersistenceService._validate_topology_node(
            node_dict.get("right"), key, max_key, errors, visited_ids, sismolab
        )

        # Verificación de balanceo AVL: subárbol ausente tiene altura -1
        left_height = node_dict.get("left", {}).get("height", -1) if node_dict.get("left") else -1
        right_height = node_dict.get("right", {}).get("height", -1) if node_dict.get("right") else -1
        is_node_balanced = abs(left_height - right_height) <= 1

        return (left_valid and right_valid), (left_balanced and right_balanced and is_node_balanced)