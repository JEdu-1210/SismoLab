import json
from src.utils.Files import FilesUtils

def main():
    filename = "./Data/test.json"
    data = FilesUtils.read_json(filename)
    if data != None and data != {}:
     print(data.data)
    
        
    else:
        print('no data')
    print(data)

    #data2 = FilesUtils.write_json(filename,event.toDict)
    # Diagmos quel front me pide eliminar un evento, entonces el front me debe enviar esa key [3, 2,"S81727712"]
    # Antes de eliminar el evento se debe guardar ese evento, es decir, el NODO completo
    #current_event_status 
main()