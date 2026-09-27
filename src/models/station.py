
class Station:

    def __init__(
        self,
        name,
        x,
        y
    ):

        self.name = name
        self.x = float(x)
        self.y = float(y)


    def __str__(self):

        return (
            f"Station({self.name}, "
            f"coordinates=({self.x}, {self.y}))"
        )