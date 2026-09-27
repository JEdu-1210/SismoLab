from models.Scenario import Scenario
from models.History import History
from models.Metrics import Metrics
from models.Version import Version
from models.Association import Association

from structures.AVLTree import AVLTree
from structures.BSTTree import BSTTree
from structures.ReportQueue import ReportQueue
from structures.Stack import Stack


class SismoLab:

    def __init__(
        self,
        scenario: Scenario
    ):

        # Escenario actual del sistema.
        self._scenario = scenario


        # Árbol principal de eventos activos.
        self._avl_tree = AVLTree()


        # Árbol utilizado para comparación estructural
        # con el AVL.
        self._bst_tree = BSTTree()


        # Histórico que conserva las raíces
        # de los subárboles archivados.
        self._history = History()


        # Cola FIFO de reportes pendientes.
        self._report_queue = ReportQueue()


        # Pila utilizada para las acciones de deshacer.
        self._undo_stack = Stack()


        # Contadores acumulativos del sistema.
        self._metrics = Metrics()


        # Versiones persistentes creadas por el usuario.
        self._versions = []


        # Asociaciones actualmente existentes
        # entre eventos.
        self._associations = []


        # Identificadores de eventos eliminados.
        #
        # No se pueden reutilizar hasta restaurar
        # un estado anterior.
        self._retired_ids = set()


    # SCENARIO

    def get_scenario(self):

        return self._scenario


    def set_scenario(
        self,
        scenario: Scenario
    ):

        self._scenario = scenario


    # AVL TREE

    def get_avl_tree(self):

        return self._avl_tree


    # BST TREE

    def get_bst_tree(self):

        return self._bst_tree


    # HISTORY

    def get_history(self):

        return self._history


    # REPORT QUEUE

    def get_report_queue(self):

        return self._report_queue


    # UNDO STACK

    def get_undo_stack(self):

        return self._undo_stack


    # METRICS

    def get_metrics(self):

        return self._metrics


    # VERSIONS

    # Retorna una copia de la lista de versiones.
    def get_versions(self):

        return list(
            self._versions
        )


    # Agrega una nueva versión.
    def add_version(
        self,
        version: Version
    ):

        self._versions.append(
            version
        )


    # Busca una versión por nombre.
    def get_version_by_name(
        self,
        name
    ):

        for version in self._versions:

            if version.get_name() == name:

                return version


        return None


    # Elimina una versión almacenada.
    def remove_version(
        self,
        version: Version
    ):

        if version not in self._versions:

            return False


        self._versions.remove(
            version
        )


        return True


    # ASSOCIATIONS
    # Retorna una copia de las asociaciones.
    def get_associations(self):

        return list(
            self._associations
        )


    # Agrega una asociación.
    def add_association(
        self,
        association: Association
    ):

        self._associations.append(
            association
        )


    # Elimina una asociación.
    def remove_association(
        self,
        association: Association
    ):

        if association not in self._associations:

            return False


        self._associations.remove(
            association
        )


        return True


    # RETIRED IDENTIFIERS

    # Registra un identificador como eliminado.
    def add_retired_id(
        self,
        identifier
    ):

        self._retired_ids.add(
            int(identifier)
        )


    # Elimina el ID del conjunto de retirados.
    #
    # Será útil al restaurar un estado anterior.
    def remove_retired_id(
        self,
        identifier
    ):

        identifier = int(identifier)


        if identifier not in self._retired_ids:

            return False


        self._retired_ids.remove(
            identifier
        )


        return True


    # Retorna True si un ID fue eliminado.
    def is_retired_id(
        self,
        identifier
    ):

        return (
            int(identifier)
            in
            self._retired_ids
        )


    # Retorna una copia del conjunto de IDs eliminados.
    def get_retired_ids(self):

        return set(
            self._retired_ids
        )