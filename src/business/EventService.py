from datetime import datetime
from business.PriorityService import PriorityService

class EventService:

    def __init__(
        self,
        sismolab
    ):

        self.sismolab = sismolab

    def calculate_event_data(
        self,
        magnitude,
        depth,
        x,
        y
    ):

        scenario = self.sismolab.get_scenario()

        is_populated_zone = scenario.is_point_in_populated_zone(x, y)

        priority = PriorityService.calculate_priority(
            magnitude,
            depth,
            is_populated_zone
        )

        return is_populated_zone, priority

    # Valida las reglas de un evento
    # que dependen del escenario.
    def validate_event(
        self,
        event
    ):

        # Primero se validan los datos
        # propios del evento.
        if not event.validateAttributes():

            return False


        scenario = (
            self.sismolab
            .get_scenario()
        )


        simulation_clock = (
            scenario
            .get_simulation_clock()
        )


        # El reloj del escenario también
        # debe ser un datetime válido.
        if not isinstance(
            simulation_clock,
            datetime
        ):

            print(
                "Error: simulation clock "
                "is not a valid datetime"
            )

            return False


        # El reloj debe trabajar en UTC.
        if (
            simulation_clock.tzinfo is None
            or
            simulation_clock.utcoffset()
            is None
        ):

            print(
                "Error: simulation clock "
                "must use UTC timezone"
            )

            return False


        if (
            simulation_clock
            .utcoffset()
            .total_seconds()
            != 0
        ):

            print(
                "Error: simulation clock "
                "must be in UTC"
            )

            return False


        # Un terremoto no puede haber ocurrido después del reloj de simulación.
        if (event.date_time > simulation_clock):

            print(
                "Error: event date "
                "cannot be later than "
                "the simulation clock"
            )

            return False

        return True
    