from math import isfinite


class Station:

    def __init__(
        self,
        name,
        x,
        y
    ):

        self._name = name

        self._x = float(x)
        self._y = float(y)


        if not self.validate_attributes():

            raise ValueError(
                "Invalid station data"
            )


    # Las estaciones permanecen
    # inmutables durante la ejecución.
    #
    # Se permiten lecturas pero
    # no existen setters.

    @property
    def name(self):

        return self._name


    @property
    def x(self):

        return self._x


    @property
    def y(self):

        return self._y


    def validate_attributes(self):

        if not isinstance(
            self._name,
            str
        ):

            print(
                "Error: station name "
                "must be a string"
            )

            return False


        if self._name.strip() == "":

            print(
                "Error: station name "
                "cannot be empty"
            )

            return False


        if not isfinite(
            self._x
        ):

            print(
                "Error: station x "
                "must be finite"
            )

            return False


        if not isfinite(
            self._y
        ):

            print(
                "Error: station y "
                "must be finite"
            )

            return False


        # Como las estaciones fueron
        # modeladas dentro del mismo plano
        # del escenario, se mantienen
        # dentro de 0 a 1000 km.
        if (
            self._x < 0.0
            or
            self._x > 1000.0
        ):

            print(
                "Error: station x "
                "must be inside "
                "[0.0, 1000.0]"
            )

            return False


        if (
            self._y < 0.0
            or
            self._y > 1000.0
        ):

            print(
                "Error: station y "
                "must be inside "
                "[0.0, 1000.0]"
            )

            return False


        return True


    def __str__(self):

        return (
            f"Station("
            f"{self._name}, "
            f"coordinates="
            f"({self._x}, "
            f"{self._y})"
            f")"
        )


    def to_dict(self):

        return {
            "name": (
                self._name
            ),

            "x": (
                self._x
            ),

            "y": (
                self._y
            )
        }