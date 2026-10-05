from src.models.UndoAction import UndoAction


class Stack:

    def __init__(self):

        self._actions = []


    # Agrega una acciÃ³n en la parte superior de la pila.
    def push(
        self,
        action: UndoAction
    ):

        self._actions.append(
            action
        )


    # Retira y retorna la Ãºltima acciÃ³n agregada.
    def pop(self):

        if self.is_empty():

            return None


        return self._actions.pop()


    # Retorna la acciÃ³n superior sin eliminarla.
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

    # Retorna una copia de las acciones
    # almacenadas en la pila.
    #
    # La Ãºltima posiciÃ³n corresponde
    # a la acciÃ³n que se desharÃ¡ primero.
    def get_actions(self):

        return list(
            self._actions
        )
    
    # VacÃ­a completamente la pila.
    def clear(self):

        self._actions.clear()
