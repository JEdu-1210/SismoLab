from src.structures.AVLNode import AVLNode
from src.structures.AVLTree import AVLTree

class History:

    def __init__(self):

        # Cada elemento de esta lista es la raÃ­z
        # de un subÃ¡rbol AVL archivado.
        self._archived_roots = []


    # Retorna una copia de la lista de raÃ­ces archivadas.
    #
    # La copia evita que otra clase modifique directamente
    # nuestra lista interna.
    def get_archived_roots(self):

        return list(
            self._archived_roots
        )


    # Retorna True si no existen subÃ¡rboles archivados.
    def is_empty(self):

        if len(self._archived_roots) == 0:
            return True

        return False


    # Recibe la raÃ­z de un subÃ¡rbol previamente
    # separado del AVL activo y la guarda.
    def add_archived_root(
        self,
        root: AVLNode
    ):

        if root is None:
            return False


        # Una raÃ­z archivada no debe tener padre.
        root.set_parent(None)


        self._archived_roots.append(
            root
        )


        return True


    # Elimina una raÃ­z archivada de la colecciÃ³n.
    #
    # Esto NO elimina los nodos de ese subÃ¡rbol.
    # Solamente deja de estar almacenado por History.
    def remove_archived_root(
        self,
        root: AVLNode
    ):

        if root not in self._archived_roots:

            return False


        self._archived_roots.remove(
            root
        )


        return True


    # Busca un nodo archivado utilizando solamente
    # el identificador del Event.
    #
    # Como la llave del Ã¡rbol es (P, M, I),
    # debemos recorrer los subÃ¡rboles.
    def search_by_id(
        self,
        identifier
    ):

        for root in self._archived_roots:

            found_node = (
                self._search_by_id(
                    identifier,
                    root
                )
            )


            if found_node is not None:

                return found_node


        return None


    # MÃ©todo recursivo utilizado por search_by_id().
    def _search_by_id(
        self,
        identifier,
        current_node
    ):

        if current_node is None:

            return None


        event = current_node.get_event()


        if event.identifier == identifier:

            return current_node


        # Buscar primero en el subÃ¡rbol izquierdo.
        found_node = self._search_by_id(
            identifier,
            current_node.get_left()
        )


        if found_node is not None:

            return found_node


        # Si no apareciÃ³, buscar en el derecho.
        return self._search_by_id(
            identifier,
            current_node.get_right()
        )

    # Extrae un solo Event del histÃ³rico.
    # Los demÃ¡s Events archivados permanecen dentro de History.
    def extract_event_by_id(
        self,
        identifier
    ):

        identifier = int(identifier)


        for index, root in enumerate(
            self._archived_roots
        ):

            archived_node = self._search_by_id(
                identifier,
                root
            )


            if archived_node is None:
                continue


            # Utilizamos temporalmente un AVLTree
            # para poder reutilizar su eliminaciÃ³n.
            temporary_tree = AVLTree()

            temporary_tree.set_root(
                root
            )


            extracted_event = temporary_tree.delete(
                archived_node.get_key(),
                rebalance=True
            )


            if extracted_event is None:
                return None


            new_root = temporary_tree.get_root()


            # Si era el Ãºnico nodo de esa rama,
            # desaparece esa raÃ­z del History.
            if new_root is None:

                self._archived_roots.pop(
                    index
                )


            # Si quedaron nodos archivados,
            # guardamos la nueva raÃ­z resultante.
            else:

                new_root.set_parent(None)

                self._archived_roots[
                    index
                ] = new_root


            return extracted_event


        return None
    # Retorna todos los eventos archivados.
    def get_all_events(self):

        events = []


        for root in self._archived_roots:

            self._collect_events(
                root,
                events
            )


        return events


    def _collect_events(
        self,
        current_node,
        events
    ):

        if current_node is None:

            return


        events.append(
            current_node.get_event()
        )


        self._collect_events(
            current_node.get_left(),
            events
        )


        self._collect_events(
            current_node.get_right(),
            events
        )


    # Retorna la cantidad total de eventos archivados.
    def count_events(self):

        total = 0


        for root in self._archived_roots:

            total += self._count_nodes(
                root
            )


        return total


    def _count_nodes(
        self,
        current_node
    ):

        if current_node is None:

            return 0


        left_count = self._count_nodes(
            current_node.get_left()
        )


        right_count = self._count_nodes(
            current_node.get_right()
        )


        return (
            1
            +
            left_count
            +
            right_count
        )

    def to_dict(self):
        return {
            "archived_roots": [self._serialize_node(root) for root in self._archived_roots]
        }

    def _serialize_node(self, node):
        if node is None:
            return None

        event = node.get_event()
        return {
            "event": event.to_dict() if hasattr(event, "to_dict") else event,
            "height": node.get_height(),
            "left": self._serialize_node(node.get_left()),
            "right": self._serialize_node(node.get_right())
        }
    
