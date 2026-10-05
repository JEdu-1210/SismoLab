from src.models.Event import Event


class AVLNode:

    def __init__(self, event: Event):

        self._event = event
        # Indica si el acceso a este nodo
        # se considera costoso segÃºn el lÃ­mite L.
        self._costly_access = False

        # Una hoja tiene altura 0.
        self._height = 0

        self._left = None
        self._right = None
        self._parent = None


    # Retorna el evento guardado en el nodo.
    def get_event(self):

        return self._event


    # Cambia el evento guardado en el nodo.
    def set_event(self, event: Event):

        self._event = event


    # Retorna la llave actual del evento.
    # La llave NO se guarda en el nodo.
    # Siempre se obtiene desde Event.
    def get_key(self):

        return self._event.get_key()


    # Retorna la altura almacenada.
    def get_height(self):

        return self._height


    # Cambia la altura almacenada.
    def set_height(self, height):

        self._height = height

    # Retorna True si el nodo tiene acceso costoso.
    def is_costly_access(self):

        return self._costly_access

    # Cambia la marca de acceso costoso.
    def set_costly_access(
        self,
        value
    ):

        self._costly_access = bool(value)

    # Retorna el hijo izquierdo.
    def get_left(self):

        return self._left


    # Cambia el hijo izquierdo.
    def set_left(self, node):

        self._left = node


    # Retorna el hijo derecho.
    def get_right(self):

        return self._right


    # Cambia el hijo derecho.
    def set_right(self, node):

        self._right = node


    # Retorna el padre.
    def get_parent(self):

        return self._parent


    # Cambia el padre.
    def set_parent(self, node):

        self._parent = node
