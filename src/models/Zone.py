from math import isfinite


class Zone:

    def __init__(
        self,
        name,
        x_min,
        x_max,
        y_min,
        y_max,
        is_populated
    ):

        self._name = name

        self._x_min = float(x_min)
        self._x_max = float(x_max)

        self._y_min = float(y_min)
        self._y_max = float(y_max)

        self._is_populated = (
            is_populated
        )


        if not self.validate_attributes():

            raise ValueError(
                "Invalid zone data"
            )


    # La zona es inmutable durante
    # la ejecución del escenario.
    #
    # Por eso solo tiene propiedades
    # de lectura y no setters.

    @property
    def name(self):

        return self._name


    @property
    def x_min(self):

        return self._x_min


    @property
    def x_max(self):

        return self._x_max


    @property
    def y_min(self):

        return self._y_min


    @property
    def y_max(self):

        return self._y_max


    @property
    def is_populated(self):

        return self._is_populated


    # Valida únicamente los datos
    # internos de esta zona.
    def validate_attributes(self):

        if not isinstance(
            self._name,
            str
        ):

            print(
                "Error: zone name "
                "must be a string"
            )

            return False


        if self._name.strip() == "":

            print(
                "Error: zone name "
                "cannot be empty"
            )

            return False


        # Todos los límites deben
        # ser números finitos.
        values = [
            self._x_min,
            self._x_max,
            self._y_min,
            self._y_max
        ]


        for value in values:

            if not isfinite(value):

                print(
                    "Error: zone boundaries "
                    "must be finite numbers"
                )

                return False


        # Todos los límites deben
        # permanecer dentro del plano.
        if (
            self._x_min < 0.0
            or
            self._x_max > 1000.0
            or
            self._y_min < 0.0
            or
            self._y_max > 1000.0
        ):

            print(
                "Error: zone boundaries "
                "must be inside "
                "[0.0, 1000.0]"
            )

            return False


        # Una zona debe tener área.
        #
        # Por eso el mínimo debe ser
        # estrictamente menor al máximo.
        if (
            self._x_min
            >=
            self._x_max
        ):

            print(
                "Error: x_min must be "
                "less than x_max"
            )

            return False


        if (
            self._y_min
            >=
            self._y_max
        ):

            print(
                "Error: y_min must be "
                "less than y_max"
            )

            return False


        # La condición de poblada o
        # no poblada la decide quien
        # crea la zona.
        if not isinstance(
            self._is_populated,
            bool
        ):

            print(
                "Error: is_populated "
                "must be True or False"
            )

            return False


        return True


    # Determina si unas coordenadas
    # pertenecen a esta zona.
    #
    # Los bordes también cuentan.
    def contains_point(
        self,
        x,
        y
    ):

        x = float(x)
        y = float(y)


        inside_x = (
            self._x_min
            <=
            x
            <=
            self._x_max
        )


        inside_y = (
            self._y_min
            <=
            y
            <=
            self._y_max
        )


        return (
            inside_x
            and
            inside_y
        )


    # Determina si esta zona comparte
    # área interior con otra zona.
    #
    # Compartir solamente un borde
    # o una esquina NO se considera
    # superposición.
    def overlaps_with(
        self,
        other_zone
    ):

        overlap_x = (
            max(
                self._x_min,
                other_zone.x_min
            )
            <
            min(
                self._x_max,
                other_zone.x_max
            )
        )


        overlap_y = (
            max(
                self._y_min,
                other_zone.y_min
            )
            <
            min(
                self._y_max,
                other_zone.y_max
            )
        )


        return (
            overlap_x
            and
            overlap_y
        )


    def __str__(self):

        return (
            f"Zone("
            f"{self._name}, "
            f"x=[{self._x_min}, "
            f"{self._x_max}], "
            f"y=[{self._y_min}, "
            f"{self._y_max}], "
            f"populated="
            f"{self._is_populated}"
            f")"
        )


    def to_dict(self):

        return {
            "name": (
                self._name
            ),

            "x_min": (
                self._x_min
            ),

            "x_max": (
                self._x_max
            ),

            "y_min": (
                self._y_min
            ),

            "y_max": (
                self._y_max
            ),

            "is_populated": (
                self._is_populated
            )
        }
