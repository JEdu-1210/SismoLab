class Metrics:

    def __init__(self):

        # Cantidad de correcciones aceptadas.
        self._accepted_corrections = 0

        # Cantidad de reportes descartados.
        self._discarded_reports = 0

        # Cantidad de conflictos detectados.
        self._conflicts = 0

        # Cantidad de operaciones de archivo masivo.
        self._mass_archives = 0

        # Cantidad total de eventos archivados.
        self._archived_events = 0


        # Casos de balanceo AVL.
        self._ll_cases = 0
        self._rr_cases = 0
        self._lr_cases = 0
        self._rl_cases = 0


        # Giros elementales.
        self._left_rotations = 0
        self._right_rotations = 0


    # CORRECCIONES
    def increment_accepted_corrections(self):

        self._accepted_corrections += 1


    def get_accepted_corrections(self):

        return self._accepted_corrections


    # REPORTES DESCARTADOS
    def increment_discarded_reports(self):

        self._discarded_reports += 1


    def get_discarded_reports(self):

        return self._discarded_reports


    # CONFLICTOS

    def increment_conflicts(self):

        self._conflicts += 1


    def get_conflicts(self):

        return self._conflicts


    # ARCHIVOS MASIVOS

    def increment_mass_archives(self):

        self._mass_archives += 1


    def get_mass_archives(self):

        return self._mass_archives


    # EVENTOS ARCHIVADOS

    # Permite aumentar más de uno porque una operación
    # de archivo puede mover un subárbol completo.
    def increment_archived_events(
        self,
        amount=1
    ):

        self._archived_events += amount


    def get_archived_events(self):

        return self._archived_events



    # CASOS AVL

    def increment_ll_case(self):

        self._ll_cases += 1


    def increment_rr_case(self):

        self._rr_cases += 1


    def increment_lr_case(self):

        self._lr_cases += 1


    def increment_rl_case(self):

        self._rl_cases += 1


    def get_ll_cases(self):

        return self._ll_cases


    def get_rr_cases(self):

        return self._rr_cases


    def get_lr_cases(self):

        return self._lr_cases


    def get_rl_cases(self):

        return self._rl_cases



    # ROTACIONES ELEMENTALES

    def increment_left_rotation(self):

        self._left_rotations += 1


    def increment_right_rotation(self):

        self._right_rotations += 1


    def get_left_rotations(self):

        return self._left_rotations


    def get_right_rotations(self):

        return self._right_rotations

    # RESUMEN

    # Retorna todos los contadores actuales.
    # Será útil para interfaz, JSON, versiones y undo.
    def get_summary(self):

        return {

            "accepted_corrections":
                self._accepted_corrections,

            "discarded_reports":
                self._discarded_reports,

            "conflicts":
                self._conflicts,

            "mass_archives":
                self._mass_archives,

            "archived_events":
                self._archived_events,

            "ll_cases":
                self._ll_cases,

            "rr_cases":
                self._rr_cases,

            "lr_cases":
                self._lr_cases,

            "rl_cases":
                self._rl_cases,

            "left_rotations":
                self._left_rotations,

            "right_rotations":
                self._right_rotations
        }


    # Permite restaurar métricas desde un estado anterior.
    def load_summary(self, data):

        self._accepted_corrections = (
            data["accepted_corrections"]
        )

        self._discarded_reports = (
            data["discarded_reports"]
        )

        self._conflicts = (
            data["conflicts"]
        )

        self._mass_archives = (
            data["mass_archives"]
        )

        self._archived_events = (
            data["archived_events"]
        )

        self._ll_cases = (
            data["ll_cases"]
        )

        self._rr_cases = (
            data["rr_cases"]
        )

        self._lr_cases = (
            data["lr_cases"]
        )

        self._rl_cases = (
            data["rl_cases"]
        )

        self._left_rotations = (
            data["left_rotations"]
        )

        self._right_rotations = (
            data["right_rotations"]
        )