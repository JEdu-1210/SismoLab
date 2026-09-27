from copy import deepcopy
from datetime import datetime


class UndoAction:

    def __init__(
        self,
        action_type,
        state_before,
        description=""
    ):

        self._action_type = action_type

        self._description = description


        # Guardamos una copia independiente.
        #
        # Así los cambios posteriores del sistema
        # no modifican el estado guardado.
        self._state_before = deepcopy(
            state_before
        )


        self._created_at = datetime.now()


    def get_action_type(self):

        return self._action_type


    def get_description(self):

        return self._description


    def get_state_before(self):

        return deepcopy(
            self._state_before
        )


    def get_created_at(self):

        return self._created_at