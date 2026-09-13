from datetime import datetime
from typing import tuple,list,set, Optional


class evento:


    def __init__(self, eventoId:int, magnitud:float, profundidad:float,
                 x:float, y :float, fecha: datetime, estacion: str, revision:int=1, estado_pendiente: str="pendiente"
    ):

        self.eventoId = int(eventoId)
        self.magnitud= float(magnitud)
        self.profundidad = float(profundidad)
        self.x= float(x)
        self.y= float(y)
        self.fecha = datetime
        self.estacion = str(estacion)
        self.revision = int(revision)
        self.estado_pendiente = estado_pendiente


    #ID Inmutables
    def id(self)-> int:
        return self._id


    def actualizar_Zona_y_Prioridad(self,zonas:list)-> None:

        self.es_zona_poblada = any(
            zona.es_poblada and zona.contiene_punto(self.x,self.y)
            for zona in zonas
        )

        if self.magnitud >= 6.0 or (self.magnitud >= 4.5 and self.profundidad <=30.0 and self.es_zona_poblada
        ):
            self.prioridad = 3

        elif self.magnitud >= 4.5:
            self.prioridad =2

        else:
            self.prioridad = 1

    def obtener_clave(self) -> tuple[int,float,int]:

        return (self.prioridad,self.magnitud,self.id)

    def actualizar_evento(
            self,nuevaMagnitud:float,
            nuevaProfundidad:float,
            nuevaX:float,
            nuevaY:float,
            nuevaFecha: datetime,
            estacion: str,
            nuevaRevision: Optional[int]= None,
            zonas: list= []
    )->None:

        self.magnitud = float(nuevaMagnitud)
        self.profundidad = float(nuevaProfundidad)
        self.x = float(nuevaX)
        self.y = float(nuevaY)
        self.fecha = nuevaFecha


        if nuevaRevision is not None:
            self.revision = nuevaRevision

        else:
            self.revision += 1


    def __muestra__(self)-> str:
        return f"Eventp(SIS-{self._id:06d}, K={self.obtener_clave()}, Rev={self.revision})"
