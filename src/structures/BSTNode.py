from models.Event import Event


class BSTNode:

    def __init__(self, event: Event):

        self._event = event

        self._left = None
        self._right = None
        self._parent = None


    # Retorna el evento que se encuentra almacenado en este nodo.
    def get_event(self):

        return self._event


    # Remplaza el evento que se encuentra almacenado en este nodo.
    def set_event(self, event: Event):

        self._event = event


    # Retorna la llave actual del evento.
    # La llave no se encuentra almacenada en el nodo.
    # Siempre se calcula a partir del evento.
    def get_key(self):

        return self._event.get_key()


    # Retorna el hijo izquierdo.
    def get_left(self):

        return self._left


    # Asigna el hijo izquierdo.
    def set_left(self, node):

        self._left = node


    # Retorna el hijo derecho.
    def get_right(self):

        return self._right


    # Asigna el hijo derecho.
    def set_right(self, node):

        self._right = node


    # Retorna el nodo padre.
    def get_parent(self):

        return self._parent


    # Asigna el nodo padre.
    def set_parent(self, node):

        self._parent = node