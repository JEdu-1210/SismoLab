from src.models.Event import Event


class Association:

    def __init__(
        self,
        reference_event: Event,
        aftershock_event: Event
    ):
        # Un evento no puede ser referencia de sÃ­ mismo
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

    def get_reference_event(self) -> Event:
        return self._reference_event

    def get_aftershock_event(self) -> Event:
        return self._aftershock_event

    def to_dict(self) -> dict:
        """
        Retorna la representaciÃ³n en diccionario serializable a JSON.
        """
        return {
            "reference_event_id": self._reference_event.identifier,
            "aftershock_event_id": self._aftershock_event.identifier,
            "reference_event": self._reference_event.to_dict() if hasattr(self._reference_event, "to_dict") else self._reference_event,
            "aftershock_event": self._aftershock_event.to_dict() if hasattr(self._aftershock_event, "to_dict") else self._aftershock_event
        }

