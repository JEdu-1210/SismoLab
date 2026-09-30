from models.Event import Event


class Association:

    def __init__(
        self,
        reference_event: Event,
        aftershock_event: Event
    ):

        # Un evento no puede ser referencia de sí mismo.
        if (
            reference_event.identifier
            ==
            aftershock_event.identifier
        ):
            raise ValueError(
                "An event cannot be associated with itself"
            )

        self._reference_event = reference_event
        self._aftershock_event = aftershock_event


    # Retorna el evento que funciona como referencia.
    def get_reference_event(self):

        return self._reference_event


    # Retorna el evento considerado réplica.
    def get_aftershock_event(self):

        return self._aftershock_event


    def to_dict(self):
        return {
            "reference_event": self._reference_event,
            "aftershock_event": self._aftershock_event
        }
    