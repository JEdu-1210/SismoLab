from models.Report import Report


class ReportQueue:

    def __init__(self):

        # Lista que conserva los reportes
        # en el mismo orden en que llegan.
        self._reports = []


    # Agrega un reporte al final de la cola.
    def enqueue(
        self,
        report: Report
    ):

        self._reports.append(
            report
        )


    # Retira y retorna el primer reporte de la cola.
    #
    # Si la cola está vacía retorna None.
    def dequeue(self):

        if self.is_empty():

            return None


        return self._reports.pop(0)


    # Retorna el primer reporte sin eliminarlo.
    def peek(self):

        if self.is_empty():

            return None


        return self._reports[0]


    # Retorna True si la cola no contiene reportes.
    def is_empty(self):

        if len(self._reports) == 0:

            return True


        return False


    # Retorna la cantidad de reportes pendientes.
    def size(self):

        return len(
            self._reports
        )


    # Retorna una copia de los reportes
    # manteniendo el orden de la cola.
    def get_reports(self):

        return list(
            self._reports
        )


    # Agrega un reporte nuevamente al frente.
    #
    # Este método será útil al deshacer
    # un paso de procesamiento de la cola.
    def restore_front(
        self,
        report: Report
    ):

        self._reports.insert(
            0,
            report
        )


    # Elimina todos los reportes de la cola.
    def clear(self):

        self._reports.clear()