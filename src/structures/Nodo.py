

from typing import Optional

from models.evento import Evento
from dataclasses import dataclass,field


@dataclass
class Nodo:

    event: Evento
    left: Optional['Nodo']=None
    rigth: Optional['Nodo']=None
    heigth: int=1
    key: tuple[int,float,int] = field(init = False) 


    def __post_init__(self):
        self.key = self.event.obtener_clave()


    def is_leaf(self) -> bool:
        #Utility method to verify if the nodo has no children
        return self.left is None and self.rigth is None

    def update_key(self) -> None:
        #Recalculates key if event priority or magnitude is updated
        self.key = self.event.obtener_clave()

