class PriorityService:

    @staticmethod
    def calculate_priority(
        magnitude,
        depth,
        is_populated_zone
    ):

        magnitude = float(magnitude)
        depth = float(depth)

        # Prioridad alta:
        # M >= 6.0
        if magnitude >= 6.0:
            return 3

        # También es alta si:
        # M >= 4.5, H <= 30
        # y está en zona poblada.
        if (
            magnitude >= 4.5
            and depth <= 30.0
            and is_populated_zone
        ):
            return 3

        # Si no fue alta, pero
        # M >= 4.5, es prioridad media.
        if magnitude >= 4.5:
            return 2

        # Cualquier otro caso
        # es prioridad baja.
        return 1
