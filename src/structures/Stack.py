from models.UndoAction import UndoAction


class Stack:

    def __init__(self):

        self._actions = []


    # Agrega una acción en la parte superior de la pila.
    def push(
        self,
        action: UndoAction
    ):

        self._actions.append(
            action
        )


    # Retira y retorna la última acción agregada.
    def pop(self):

        if self.is_empty():

            return None


        return self._actions.pop()


    # Retorna la acción superior sin eliminarla.
    def peek(self):

        if self.is_empty():

            return None


        return self._actions[-1]


    # Retorna True si no existen acciones.
    def is_empty(self):

        if len(self._actions) == 0:

            return True


        return False


    # Retorna la cantidad de acciones almacenadas.
    def size(self):

        return len(
            self._actions
        )


    # Vacía completamente la pila.
    def clear(self):

        self._actions.clear()