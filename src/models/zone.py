

from dataclasses import dataclass


@dataclass(fronzen=True)
class Zone:
    name:str
    x_min:float
    x_max:float
    y_min:float
    y_max:float
    is_populated:bool


    def __post_init__(self):

        if self.x_min < 0.0 or self.min >1000.0 or self.x_max <0.0 or self.x_max >1000.0:

            raise ValueError(f"X coordinates for zone '{self.name}' must be between 0.0 and 1000.0")

        if self.y_min <0.0 or self.y_min >1000.0 or self.y_max < 0.0 or self.y_max > 1000.0:

            raise ValueError(f"Y coordinate for zone '{self.name}' must be between 0.0 and 1000.0")

        if self.x_min > self.x_max or self.y_min > self.y_max:
            raise ValueError(f"Invalid boundaries in zone '{self.name}': minimum values cannot exceed maximum values")

    def contains_point(self, x: float, y: float) -> bool:
        return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max




