

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

        self.name = name

        self.x_min = float(x_min)
        self.x_max = float(x_max)

        self.y_min = float(y_min)
        self.y_max = float(y_max)

        self.is_populated = is_populated

        if self.validate_boundaries() == False:
            raise ValueError(
                "Invalid zone boundaries"
            )

        if type(self.is_populated) != bool:
            raise ValueError(
                "is_populated must be True or False"
            )


    def validate_boundaries(self):

        if self.x_min < 0.0:
            return False

        if self.x_max > 1000.0:
            return False

        if self.y_min < 0.0:
            return False

        if self.y_max > 1000.0:
            return False

        if self.x_min > self.x_max:
            return False

        if self.y_min > self.y_max:
            return False

        return True


    def contains_point(self, x, y):

        inside_x = (
            x >= self.x_min
            and
            x <= self.x_max
        )

        inside_y = (
            y >= self.y_min
            and
            y <= self.y_max
        )

        if inside_x and inside_y:
            return True

        return False