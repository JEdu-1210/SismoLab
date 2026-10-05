from copy import deepcopy
from datetime import datetime


class Version:

    def __init__(
        self,
        name,
        state
    ):

        if name is None or name == "":

            raise ValueError(
                "Version name cannot be empty"
            )


        self._name = name


        # Guardamos una copia independiente
        # del estado operativo.
        self._state = deepcopy(
            state
        )


        self._created_at = datetime.now()


    def get_name(self):

        return self._name


    def get_state(self):

        return deepcopy(
            self._state
        )


    def get_created_at(self):

        return self._created_at
