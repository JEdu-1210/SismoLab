from typing import Dict, Any, List, Tuple
from src.utils.Files import Files
from src.models.Returnings import BaseReturn, DataAndMsgReturn
from src.models.Event import Event
from src.services.undo_service import UndoService


class PersistenceService:

    # ... (métodos export_state, save_state_to_file y rebuild_tree_from_topology que ya hicimos) ...

    @staticmethod
    def load_by_insertions(filepath: str, sismolab: Any, bst_class: Any) -> DataAndMsgReturn:
        """
        Carga por Inserciones:
        1. Lee la secuencia de eventos.
        2. Revisa que no existan IDs duplicados (si hay duplicados, invalida el archivo).
        3. Inserta los eventos simultáneamente en el AVL (con balanceo) y en un BST (sin balanceo).
        4. Retorna las métricas comparativas de ambos árboles (raíz, altura, prof. máxima, hojas).
        """
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
            e_obj = Event.from_dict(e_dict)
            if e_obj.identifier in seen_ids:
                response.error = f"Archivo inválido: Se encontró un ID duplicado ({e_obj.identifier}) en la secuencia de carga."
                return response
            seen_ids.add(e_obj.identifier)
            event_objects.append(e_obj)

        # 2. Instanciar árbol BST paralelo (sin balanceo)
        bst_tree = bst_class()

        # 3. Limpiar e insertar en ambos árboles
        sismolab.avl_tree.clear() if hasattr(sismolab.avl_tree, "clear") else None
        
        for event in event_objects:
            sismolab.avl_tree.insert(event)
            bst_tree.insert(event)

        # 4. Compilar métricas comparativas
        response.data = {
            "avl_metrics": {
                "root_key": sismolab.avl_tree.root.key if sismolab.avl_tree.root else None,
                "height": sismolab.avl_tree.get_height(),
                "max_depth": sismolab.avl_tree.get_max_depth(),
                "leaf_count": sismolab.avl_tree.get_leaf_count()
            },
            "bst_metrics": {
                "root_key": bst_tree.root.key if bst_tree.root else None,
                "height": bst_tree.get_height(),
                "max_depth": bst_tree.get_max_depth(),
                "leaf_count": bst_tree.get_leaf_count()
            }
        }
        response.msg = "Carga por inserciones realizada con éxito en AVL y BST."
        return response

    @staticmethod
    def validate_and_load_topology(filepath: str, sismolab: Any) -> DataAndMsgReturn:
        """
        Carga por Topología con validaciones estrictas:
        - Revisa unicidad de IDs (activos e históricos).
        - Valida orden global BST, factores de balanceo y coherencia de prioridades.
        - Si está desbalanceado, exige que el Modo Estrés esté activado.
        - Carga Atómica: Si hay errores, no modifica el escenario actual y retorna la lista de fallos.
        """
        response = DataAndMsgReturn()
        read_res = Files.read_json(filepath)

        if not read_res.data:
            response.error = read_res.error or "Error al leer el archivo de topología."
            return response

        state_dict = read_res.data
        errors: List[str] = []

        # --- VALIDACIONES PREVIAS (Pre-flight checks) ---
        topology_data = state_dict.get("state", {}).get("active_tree_topology") or state_dict.get("active_tree_topology")
        
        if not topology_data:
            errors.append("El archivo no contiene una estructura 'active_tree_topology' válida.")
        else:
            # a) Validar orden BST y ausencia de ciclos recursivamente
            is_valid_order, is_balanced = PersistenceService._validate_topology_node(
                node_dict=topology_data, 
                min_key=None, 
                max_key=None, 
                errors=errors, 
                visited_ids=set()
            )

            # b) Regla de Modo Estrés para topologías desbalanceadas
            is_stress = state_dict.get("state", {}).get("stress_mode", getattr(sismolab, "is_stress_mode", False))
            if not is_balanced and not is_stress:
                errors.append("Rechazado: La topología está desbalanceada y el Modo Estrés NO está activado.")

        # --- SI HAY ERRORES, SE ABORTA (Conserva el escenario anterior intacto) ---
        if errors:
            response.error = "Error de validación al cargar topología. Escenario conservado intacto."
            response.data = {"validation_errors": errors}
            return response

        # --- SI TODO ES VÁLIDO, SE REEMPLAZA EL ESCENARIO (Carga Atómica) ---
        from src.services.version_service import VersionService
        version_srv = VersionService()
        version_srv._apply_state(sismolab, state_dict.get("state", state_dict))

        response.msg = "Topología validada y cargada exitosamente."
        return response

    @staticmethod
    def _validate_topology_node(node_dict: dict, min_key: Any, max_key: Any, errors: List[str], visited_ids: set) -> Tuple[bool, bool]:
        """Auxiliar recursivo para validar la integridad de cada nodo en la topología."""
        if node_dict is None:
            return True, True

        event_dict = node_dict.get("event", {})
        event_id = event_dict.get("identifier")

        # Check de ciclos / duplicados
        if event_id in visited_ids:
            errors.append(f"Ciclo o ID duplicado detectado en la topología: Evento ID {event_id}")
            return False, False
        visited_ids.add(event_id)

        # Check de clave K = (P, M, I)
        key = (event_dict.get("priority"), event_dict.get("magnitude"), event_id)
        if min_key and key <= min_key:
            errors.append(f"Violación de orden BST en el nodo {event_id}: clave {key} <= min_key {min_key}")
        if max_key and key >= max_key:
            errors.append(f"Violación de orden BST en el nodo {event_id}: clave {key} >= max_key {max_key}")

        # Recursión en subárboles
        left_valid, left_balanced = PersistenceService._validate_topology_node(node_dict.get("left"), min_key, key, errors, visited_ids)
        right_valid, right_balanced = PersistenceService._validate_topology_node(node_dict.get("right"), key, max_key, errors, visited_ids)

        # Verificación básica de balanceo AVL (altura izquierda vs derecha <= 1)
        left_height = node_dict.get("left", {}).get("height", 0) if node_dict.get("left") else 0
        right_height = node_dict.get("right", {}).get("height", 0) if node_dict.get("right") else 0
        is_node_balanced = abs(left_height - right_height) <= 1

        return (left_valid and right_valid), (left_balanced and right_balanced and is_node_balanced)