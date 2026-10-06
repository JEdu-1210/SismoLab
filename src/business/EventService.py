from datetime import datetime
from src.business.PriorityService import PriorityService
from src.models.Event import Event
from src.models.Status import CatalogStatus, AttentionStatus
from src.business.AssociationService import AssociationService
from src.business.AccessService import AccessService
from src.services.undo_service import UndoService
from src.services.persistencia import PersistenceService

class EventService:

    def __init__(
        self,
        sismolab
    ):

        self.sismolab = sismolab

        self.association_service = (
            AssociationService(
                sismolab
            )
        )

        self.sismolab = sismolab

        self.access_service = (
            AccessService(
                sismolab
            )
        )

        self.undo_service = UndoService()

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


    # CREACIÓN MANUAL DE EVENTOS
    # Recibe los datos ingresados por el usuario, la revisión inicial de una creación
    # manual siempre es 1
    def create_manual_event(
        self,
        identifier,
        magnitude,
        depth,
        x,
        y,
        date_time,
        station_name
    ):

        scenario = self.sismolab.get_scenario()


        # Primero comprobamos que el ID
        # pueda convertirse correctamente.
        try:
            identifier = int(identifier)

        except (TypeError, ValueError):

            return (
                False,
                "Invalid identifier",
                None
            )


        # El identificador no puede haber sido
        # utilizado anteriormente por ningún evento.
        if scenario.has_event_id(identifier):

            return (
                False,
                "The identifier already exists",
                None
            )


        # La estación debe existir
        # dentro del Scenario.
        station = scenario.get_station_by_name(
            station_name
        )

        if station is None:

            return (
                False,
                "The station does not exist",
                None
            )


        # Calculamos los dos datos derivados:
        # - pertenencia a zona poblada
        # - prioridad
        # llamando al metodo de arriba, que a su vez llama a PriorityService.calculate_priority
        try:

            (
                is_populated_zone,
                priority
            ) = self.calculate_event_data(
                magnitude,
                depth,
                x,
                y
            )

        except (TypeError, ValueError):

            return (
                False,
                "Invalid event data",
                None
            )


        # Creamos el objeto Event.
        # Todavía NO se ha modificado ninguna estructura del sistema.
        try:

            event = Event(
                identifier,
                magnitude,
                depth,
                x,
                y,
                date_time,
                1,
                priority,
                is_populated_zone
            )

        except (TypeError, ValueError):

            return (
                False,
                "Invalid event data",
                None
            )


        # Validamos sus atributos y las reglas relacionadas con Scenario.
        if not self.validate_event(event):

            return (
                False,
                "Invalid event data",
                None
            )


        # La estación que originó el alta queda registrada como aceptada.
        event.add_accepted_station(
            station.name
        )


        # El AVL es la estructura central
        # de eventos activos.
        avl_tree = self.sismolab.get_avl_tree()

        # El BST conserva los mismos eventos activos
        # para permitir la comparación estructural.
        bst_tree = self.sismolab.get_bst_tree()

        # En modo estrés el AVL conserva el orden BST,
        # pero no realiza rotaciones.
        rebalance = not scenario.is_stress_mode()

        state_before = (
            self.undo_service
            .capture_state(
                self.sismolab
            )
        )

        avl_tree.clear_rotation_log()

        # Primero insertamos en el AVL.
        inserted_avl_node = avl_tree.insert(
            event,
            rebalance=rebalance
        )

        if inserted_avl_node is None:

            return (
                False,
                "The event could not be inserted in the AVL",
                None
            )


        # Luego insertamos el mismo Event en el BST.
        inserted_bst_node = bst_tree.insert(event)

        # Si el BST falla, deshacemos la inserción
        # realizada anteriormente en el AVL.
        if inserted_bst_node is None:

            avl_tree.delete(
                event.get_key(),
                rebalance=rebalance
            )

            return (
                False,
                "The event could not be inserted in the BST",
                None
            )


        # Finalmente registramos la identidad
        # del Event dentro del Scenario.
        registered = scenario.register_event(event)


        # Esta situación no debería ocurrir porque
        # ya comprobamos el ID, pero si ocurriera
        # retiramos el Event de ambos árboles.
        if not registered:

            avl_tree.delete(
                event.get_key(),
                rebalance=rebalance
            )

            bst_tree.delete(
                event.get_key()
            )

            return (
                False,
                "The identifier already exists",
                None
            )

        # Una nueva alta puede cambiar las asociaciones de varios Events.
        self.association_service.recalculate_all()

        # La inserción pudo cambiar profundidades del AVL.
        self.access_service.update_access_marks()

        self.sismolab.get_metrics().register_rotation_log(
            avl_tree.get_rotation_log()
        )
        # Después conectaremos aquí:
        # - métricas
        # - Undo
        # - actualización de la GUI

        self.undo_service.push_snapshot(
            self.sismolab,
            "CREATE_EVENT",
            (
                f"Create event "
                f"SIS-{event.identifier:06d}"
            ),
            state_before
        )

        return (
            True,
            "Event created successfully",
            event
        )


    # Busca las asociaciones en las que participa un Event.
    def get_event_associations(
        self,
        event
    ):

        associations = []

        for association in self.sismolab.get_associations():

            reference_event = (
                association.get_reference_event()
            )

            aftershock_event = (
                association.get_aftershock_event()
            )


            # El evento consultado funciona
            # como referencia de otro evento.
            if reference_event.identifier == event.identifier:

                associations.append({
                    "type": "REFERENCE_FOR",
                    "related_event_id": (
                        aftershock_event.identifier
                    )
                })


            # El evento consultado está asociado
            # como posible réplica de otro.
            elif aftershock_event.identifier == event.identifier:

                associations.append({
                    "type": "AFTERSHOCK_OF",
                    "related_event_id": (
                        reference_event.identifier
                    )
                })


        return associations



    # CONSULTA DE UN EVENTO
    # Busca un Event por su identificador
    # y prepara la información que posteriormente
    # mostrará la GUI. Se retorna un diccionario con los detalles del Event que se encontró,
    #  o None si no se encontró.
    def get_event_details(
        self,
        identifier
    ):

        scenario = self.sismolab.get_scenario()


        # Primero se comprueba que el ID tenga un formato válido.
        try:
            identifier = int(identifier)

        except (TypeError, ValueError):

            return (
                False,
                "Invalid identifier",
                None
            )


        # La búsqueda por ID se realiza utilizando el diccionario auxiliar.
        event = scenario.get_event_by_id(
            identifier
        )


        if event is None:

            return (
                False,
                "Event not found",
                None
            )


        # Información general del Event.
        details = event.to_dict()

        details["key"] = event.get_key()


        # Las asociaciones pueden existir
        # tanto para activos como archivados.
        details["associations"] = (
            self.get_event_associations(
                event
            )
        )


        # Si no está activo, no buscamos nodo
        # dentro del AVL.
        if event.catalog_status.value != "ACTIVE":

            details["node_depth"] = None
            details["node_height"] = None
            details["balance_factor"] = None
            details["costly_access"] = None
            details["access_limit"] = (
                scenario.get_access_limit()
            )
            details["visited_nodes"] = None
            
            return (
                True,
                "Event found",
                details
            )


        # Un Event activo debe existir
        # dentro del AVL con su K actual.
        avl_tree = self.sismolab.get_avl_tree()

        node = avl_tree.search(
            event.get_key()
        )


        # Si el Event dice ACTIVE pero no existe
        # en el AVL, existe una inconsistencia.
        if node is None:

            return (
                False,
                "Active event is not present in the AVL",
                None
            )


        # Profundidad estructural del nodo.
        details["node_depth"] = (
            avl_tree.get_depth(node)
        )


        # Altura almacenada del nodo.
        details["node_height"] = (
            node.get_height()
        )


        # Factor de balance:
        # altura izquierda - altura derecha.
        details["balance_factor"] = (
            avl_tree.get_balance_factor(
                node
            )
        )

        details["costly_access"] = (
            node.is_costly_access()
        )

        details["access_limit"] = (
            scenario.get_access_limit()
        )

        details["visited_nodes"] = (
            details["node_depth"] + 1
        )
        
        return (
            True,
            "Event found",
            details
        )

    
    # CORRECCIÓN MANUAL DE UN EVENTO
    # Reemplaza uno o varios datos de un Event activo.
    # El identifier nunca puede modificarse.
    # Los valores que lleguen como None conservan el valor original del Event.
    def correct_manual_event(
        self,
        identifier,
        magnitude=None,
        depth=None,
        x=None,
        y=None,
        date_time=None
    ):

        scenario = self.sismolab.get_scenario()


        # Debe modificarse al menos un dato.
        if all(
            value is None
            for value in (
                magnitude,
                depth,
                x,
                y,
                date_time
            )
        ):

            return (
                False,
                "No correction data was provided",
                None
            )


        # Validamos el identificador.
        try:
            identifier = int(identifier)

        except (TypeError, ValueError):

            return (
                False,
                "Invalid identifier",
                None
            )


        # Localizamos el Event mediante
        # el diccionario auxiliar del Scenario.
        event = scenario.get_event_by_id(
            identifier
        )

        if event is None:

            return (
                False,
                "Event not found",
                None
            )


        # Solamente pueden corregirse manualmente eventos activos.
        if (
            event.catalog_status
            !=
            CatalogStatus.ACTIVE
        ):

            return (
                False,
                "Only active events can be corrected",
                None
            )


        # 1. Preparar los datos resultantes que tendrá el Event después de la corrección.
        # Pero todavía NO modificamos el Event real.

        new_magnitude = (
            event.magnitude
            if magnitude is None
            else magnitude
        )
        # Esto dice que si magnitude es None,
        # new_magnitude será el valor original del evento, de lo contrario, 
        # será el nuevo valor proporcionado.
        new_depth = (
            event.depth
            if depth is None
            else depth
        )

        new_x = (
            event.x
            if x is None
            else x
        )

        new_y = (
            event.y
            if y is None
            else y
        )

        new_date_time = (
            event.date_time
            if date_time is None
            else date_time
        )

        new_revision = event.revision + 1


        # 2. Calcular los datos derivados.

        try:

            (
                new_is_populated_zone,
                new_priority
            ) = self.calculate_event_data(
                new_magnitude,
                new_depth,
                new_x,
                new_y
            )

        except (TypeError, ValueError):

            return (
                False,
                "Invalid correction data",
                None
            )


        # 3. Crear un Event candidato.
        # Sirve únicamente para comprobar que todos
        # los datos nuevos sean válidos ANTES de
        # modificar cualquier estructura.

        try:

            candidate = Event(
                identifier,
                new_magnitude,
                new_depth,
                new_x,
                new_y,
                new_date_time,
                new_revision,
                new_priority,
                new_is_populated_zone
            )

        except (TypeError, ValueError):

            return (
                False,
                "Invalid correction data",
                None
            )


        if not self.validate_event(candidate):

            return (
                False,
                "Invalid correction data",
                None
            )


        # 4. Conservar el estado anterior.

        old_state = {
            "magnitude": event.magnitude,
            "depth": event.depth,
            "x": event.x,
            "y": event.y,
            "date_time": event.date_time,
            "revision": event.revision,
            "priority": event.priority,
            "is_populated_zone": (
                event.is_populated_zone
            ),
            "attention_status": (
                event.attention_status
            )
        }

        old_key = event.get_key()
        new_key = candidate.get_key()

        key_changed = (
            old_key != new_key
        )


        avl_tree = self.sismolab.get_avl_tree()
        bst_tree = self.sismolab.get_bst_tree()

        rebalance = (
            not scenario.is_stress_mode()
        )
        
        state_before = (
            self.undo_service
            .capture_state(
                self.sismolab
            )
        )

        avl_tree.clear_rotation_log()

        # 5. Si K cambia, primero comprobamos que
        #    el Event exista en AMBOS árboles.
        # Si no cambio no es necesario retirarlo y reinsertarlo, porque la clave sigue siendo la misma.
        if key_changed:

            if avl_tree.search(old_key) is None:

                return (
                    False,
                    "Active event is not present in the AVL",
                    None
                )

            if bst_tree.search(old_key) is None:

                return (
                    False,
                    "Active event is not present in the BST",
                    None
                )


            # Retiramos usando la K ANTERIOR.
            deleted_avl = avl_tree.delete(
                old_key,
                rebalance=rebalance
            )

            # Si por alguna razón falla el AVL,
            # recuperamos exactamente el estado anterior.
            if deleted_avl is None:

                PersistenceService.apply_state(
                    self.sismolab,
                    state_before
                )

                return (
                    False,
                    "The event could not be removed from the AVL",
                    None
                )


            deleted_bst = bst_tree.delete(
                old_key
            )

            # Si el AVL ya cambió pero falla el BST,
            # restauramos TODO el snapshot anterior.
            if deleted_bst is None:

                PersistenceService.apply_state(
                    self.sismolab,
                    state_before
                )

                return (
                    False,
                    "The event could not be removed from the BST",
                    None
                )
        # 6. Aplicar los datos nuevos al Event real.

        event.magnitude = candidate.magnitude
        event.depth = candidate.depth

        event.x = candidate.x
        event.y = candidate.y

        event.date_time = candidate.date_time

        event.revision = candidate.revision

        event.priority = candidate.priority

        event.is_populated_zone = (
            candidate.is_populated_zone
        )


        # Toda corrección aceptada
        # devuelve el Event a pendiente.
        event.mark_as_pending()


        # 7. Si K cambió, reinsertamos el mismo Event
        #    en AVL y BST con su nueva clave.
        if key_changed:

            inserted_avl = avl_tree.insert(
                event,
                rebalance=rebalance
            )

            inserted_bst = bst_tree.insert(
                event
            )

            if (
                inserted_avl is None
                or
                inserted_bst is None
            ):

                PersistenceService.apply_state(
                    self.sismolab,
                    state_before
                )

                return (
                    False,
                    "The correction could not be applied",
                    None
                )


        # 8. Actualizar métricas.

        metrics = self.sismolab.get_metrics()

        metrics.increment_accepted_corrections()


        # Una corrección puede cambiar magnitud,
        # tiempo o ubicación y por tanto alterar
        # varias asociaciones.
        self.association_service.recalculate_all()

        # Una corrección puede cambiar K
        # y producir reinserciones/rotaciones.
        self.access_service.update_access_marks()

        self.sismolab.get_metrics().register_rotation_log(
            avl_tree.get_rotation_log()
        )
        # Posteriormente registrar Undo , refrescar la GUI

        self.undo_service.push_snapshot(
            self.sismolab,
            "MANUAL_CORRECTION",
            (
                f"Correct event "
                f"SIS-{event.identifier:06d}"
            ),
            state_before
        )
        
        return (
            True,
            "Event corrected successfully",
            event
        )


    # MARCAR EVENTO COMO REVISADO

    def mark_event_as_reviewed(
        self,
        identifier
    ):

        scenario = self.sismolab.get_scenario()

        # Validar identificador.
        try:
            identifier = int(identifier)

        except (TypeError, ValueError):
            return (
                False,
                "Invalid identifier",
                None
            )

        # Buscar el Event por ID.
        event = scenario.get_event_by_id(
            identifier
        )

        if event is None:
            return (
                False,
                "Event not found",
                None
            )

        # Solo los eventos activos tienen
        # estado de atención pendiente/revisado.
        if event.catalog_status != CatalogStatus.ACTIVE:
            return (
                False,
                "Only active events can be reviewed",
                None
            )

        # Si ya estaba revisado no necesitamos
        # realizar ninguna modificación.
        if event.attention_status == AttentionStatus.REVIEWED:
            return (
                True,
                "Event is already reviewed",
                event
            )

        #estado anterior para undo
        state_before = (
            self.undo_service
            .capture_state(
                self.sismolab
            )
        )

        # No modifica K, por lo tanto NO se toca AVL ni BST.
        event.mark_as_reviewed()

        self.undo_service.push_snapshot(
            self.sismolab,
            "MARK_REVIEWED",
            (
                f"Mark event "
                f"SIS-{event.identifier:06d} "
                f"as reviewed"
            ),
            state_before
        )

        return (
            True,
            "Event marked as reviewed",
            event
        )

    # ELIMINACIÓN INDIVIDUAL DE UN EVENTO

    def delete_event(
        self,
        identifier
    ):

        scenario = self.sismolab.get_scenario()

        # Validar identificador.
        try:
            identifier = int(identifier)

        except (TypeError, ValueError):
            return (
                False,
                "Invalid identifier",
                None
            )

        # Buscar el Event mediante el diccionario auxiliar.
        event = scenario.get_event_by_id(
            identifier
        )

        if event is None:
            return (
                False,
                "Event not found",
                None
            )

        # Solo puede eliminarse individualmente un evento activo. 
        # lo comprobamos con el ENUM CatalogStatus.ACTIVE
        if event.catalog_status != CatalogStatus.ACTIVE:
            return (
                False,
                "Only active events can be deleted",
                None
            )


        old_key = event.get_key()
        avl_tree = self.sismolab.get_avl_tree()
        bst_tree = self.sismolab.get_bst_tree()
        rebalance = not scenario.is_stress_mode()


        # Antes de modificar cualquier estructura
        # comprobamos que exista en ambos árboles.
        if avl_tree.search(old_key) is None:
            return (
                False,
                "Active event is not present in the AVL",
                None
            )

        if bst_tree.search(old_key) is None:
            return (
                False,
                "Active event is not present in the BST",
                None
            )

        state_before = (
            self.undo_service
            .capture_state(
                self.sismolab
            )
        )

        avl_tree.clear_rotation_log()
        # Aquí despues registraremos el estado previo para Undo.

        # Retirar únicamente este Event del AVL.
        deleted_avl = avl_tree.delete(
            old_key,
            rebalance=rebalance
        )

        if deleted_avl is None:

            PersistenceService.apply_state(
                self.sismolab,
                state_before
            )

            return (
                False,
                "The event could not be deleted from the AVL",
                None
            )


        # Retirar el mismo Event del BST.
        deleted_bst = bst_tree.delete(
            old_key
        )

        if deleted_bst is None:

            PersistenceService.apply_state(
                self.sismolab,
                state_before
            )

            return (
                False,
                "The event could not be deleted from the BST",
                None
            )


        # La eliminación física de los árboles terminó correctamente.
        # Ahora modificamos su estado de catálogo.
        event.delete()


        # Registrar permanentemente el ID como eliminado.
        self.sismolab.add_retired_id(
            identifier
        )


        # OJO
        # NO eliminamos el Event del diccionario scenario._events_by_id.
        # Debemos conservar sus datos para:
        # - consultas
        # - Undo
        # - versiones
        # - rechazar reportes posteriores.

        # El Event eliminado deja de participar en asociaciones. Otros Events que lo utilizaban como
        # referencia buscarán automáticamente la siguiente mejor referencia válida.
        self.association_service.recalculate_all()

        # La eliminación y sus posibles rotaciones cambian profundidades.
        self.access_service.update_access_marks()

        self.sismolab.get_metrics().register_rotation_log(
            avl_tree.get_rotation_log()
        )       
        # Posteriormente también agregaremos:
        # - registro de Undo
        # - actualización de indicadores/GUI
        
        self.undo_service.push_snapshot(
            self.sismolab,
            "DELETE_EVENT",
            (
                f"Delete event "
                f"SIS-{event.identifier:06d}"
            ),
            state_before
        )

        return (
            True,
            "Event deleted successfully",
            event
        )

    # CREAR EVENTO DESDE REPORTE

    def create_event_from_report(
        self,
        candidate,
        station
    ):

        scenario = self.sismolab.get_scenario()


        # Aunque ReportService ya comprobó el ID,
        # protegemos nuevamente la operación.
        if scenario.has_event_id(
            candidate.identifier
        ):

            return (
                False,
                "The identifier already exists",
                None
            )


        candidate.add_accepted_station(
            station.name
        )


        avl_tree = self.sismolab.get_avl_tree()
        bst_tree = self.sismolab.get_bst_tree()

        rebalance = not scenario.is_stress_mode()


        inserted_avl = avl_tree.insert(
            candidate,
            rebalance=rebalance
        )


        if inserted_avl is None:

            return (
                False,
                "The event could not be inserted in the AVL",
                None
            )


        inserted_bst = bst_tree.insert(
            candidate
        )


        if inserted_bst is None:

            avl_tree.delete(
                candidate.get_key(),
                rebalance=rebalance
            )

            return (
                False,
                "The event could not be inserted in the BST",
                None
            )


        if not scenario.register_event(
            candidate
        ):

            avl_tree.delete(
                candidate.get_key(),
                rebalance=rebalance
            )

            bst_tree.delete(
                candidate.get_key()
            )

            return (
                False,
                "The identifier already exists",
                None
            )


        # El alta puede cambiar las asociaciones
        # de otros Events.
        self.association_service.recalculate_all()

        self.access_service.update_access_marks()

        # Posteriormente:
        # - Undo
        # - GUI

        return (
            True,
            "Event created from report",
            candidate
        )

    # CONFIRMAR EVENTO MEDIANTE REPORTE

    def confirm_event_report(
        self,
        event,
        station
    ):

        # accepted_stations es un set,
        # por eso repetir la misma estación
        # nunca genera duplicados.
        event.add_accepted_station(
            station.name
        )


        # Una confirmación NO cambia:
        # - revision
        # - priority
        # - K
        # - attention_status
        # - catalog_status
        # Por eso tampoco toca AVL/BST.

        return (
            True,
            "Event confirmed",
            event
        )

    # ACTUALIZAR EVENTO ACTIVO DESDE REPORTE

    def update_event_from_report(
        self,
        event,
        candidate,
        station
    ):

        scenario = self.sismolab.get_scenario()


        if (
            event.catalog_status
            != CatalogStatus.ACTIVE
        ):

            return (
                False,
                "The event is not active",
                None
            )


        old_key = event.get_key()
        new_key = candidate.get_key()

        key_changed = (
            old_key != new_key
        )


        old_state = {
            "magnitude": event.magnitude,
            "depth": event.depth,
            "x": event.x,
            "y": event.y,
            "date_time": event.date_time,
            "revision": event.revision,
            "priority": event.priority,
            "is_populated_zone": (
                event.is_populated_zone
            ),
            "attention_status": (
                event.attention_status
            ),
            "accepted_stations": set(
                event.accepted_stations
            )
        }


        avl_tree = self.sismolab.get_avl_tree()
        bst_tree = self.sismolab.get_bst_tree()

        rebalance = not scenario.is_stress_mode()


        # Si K cambia debemos retirar
        # utilizando la K anterior.
        if key_changed:

            if avl_tree.search(old_key) is None:

                return (
                    False,
                    "Active event is not present in the AVL",
                    None
                )


            if bst_tree.search(old_key) is None:

                return (
                    False,
                    "Active event is not present in the BST",
                    None
                )


            avl_tree.delete(
                old_key,
                rebalance=rebalance
            )

            bst_tree.delete(
                old_key
            )


        # Aplicar la revisión recibida.
        event.magnitude = candidate.magnitude
        event.depth = candidate.depth

        event.x = candidate.x
        event.y = candidate.y

        event.date_time = candidate.date_time

        event.revision = candidate.revision
        event.priority = candidate.priority

        event.is_populated_zone = (
            candidate.is_populated_zone
        )


        event.add_accepted_station(
            station.name
        )

        event.mark_as_pending()


        if key_changed:

            inserted_avl = avl_tree.insert(
                event,
                rebalance=rebalance
            )

            inserted_bst = bst_tree.insert(
                event
            )


            if (
                inserted_avl is None
                or inserted_bst is None
            ):

                if inserted_avl is not None:

                    avl_tree.delete(
                        new_key,
                        rebalance=rebalance
                    )


                if inserted_bst is not None:

                    bst_tree.delete(
                        new_key
                    )


                # Restaurar Event.
                event.magnitude = (
                    old_state["magnitude"]
                )

                event.depth = (
                    old_state["depth"]
                )

                event.x = old_state["x"]
                event.y = old_state["y"]

                event.date_time = (
                    old_state["date_time"]
                )

                event.revision = (
                    old_state["revision"]
                )

                event.priority = (
                    old_state["priority"]
                )

                event.is_populated_zone = (
                    old_state[
                        "is_populated_zone"
                    ]
                )

                event.attention_status = (
                    old_state[
                        "attention_status"
                    ]
                )

                event.accepted_stations = set(
                    old_state[
                        "accepted_stations"
                    ]
                )


                avl_tree.insert(
                    event,
                    rebalance=rebalance
                )

                bst_tree.insert(
                    event
                )


                return (
                    False,
                    "The report correction could not be applied",
                    None
                )


        self.sismolab.get_metrics() \
            .increment_accepted_corrections()


        self.association_service.recalculate_all()
        self.access_service.update_access_marks()

        # Posteriormente registrar Undo.

        return (
            True,
            "Event updated from report",
            event
        )

    # REACTIVAR EVENTO ARCHIVADO DESDE REPORTE

    def reactivate_archived_event_from_report(
        self,
        event,
        candidate,
        station
    ):

        scenario = self.sismolab.get_scenario()


        if (
            event.catalog_status
            != CatalogStatus.ARCHIVED
        ):

            return (
                False,
                "The event is not archived",
                None
            )


        history = self.sismolab.get_history()


        # Primero comprobamos que realmente
        # esté almacenado en History.
        archived_node = history.search_by_id(
            event.identifier
        )


        if archived_node is None:

            return (
                False,
                "Archived event is not present in History",
                None
            )


        # Guardamos datos por seguridad.
        old_state = {
            "magnitude": event.magnitude,
            "depth": event.depth,
            "x": event.x,
            "y": event.y,
            "date_time": event.date_time,
            "revision": event.revision,
            "priority": event.priority,
            "is_populated_zone": (
                event.is_populated_zone
            ),
            "attention_status": (
                event.attention_status
            ),
            "catalog_status": (
                event.catalog_status
            ),
            "accepted_stations": set(
                event.accepted_stations
            )
        }


        # Sacamos SOLO este Event del History.
        extracted_event = (
            history.extract_event_by_id(
                event.identifier
            )
        )


        if extracted_event is None:

            return (
                False,
                "The archived event could not be extracted",
                None
            )


        # Seguimos trabajando con el mismo
        # objeto Event y la misma identidad.
        event.magnitude = candidate.magnitude
        event.depth = candidate.depth

        event.x = candidate.x
        event.y = candidate.y

        event.date_time = candidate.date_time

        event.revision = candidate.revision
        event.priority = candidate.priority

        event.is_populated_zone = (
            candidate.is_populated_zone
        )


        event.add_accepted_station(
            station.name
        )

        event.activate()
        event.mark_as_pending()


        avl_tree = self.sismolab.get_avl_tree()
        bst_tree = self.sismolab.get_bst_tree()

        rebalance = not scenario.is_stress_mode()


        inserted_avl = avl_tree.insert(
            event,
            rebalance=rebalance
        )


        if inserted_avl is None:

            # Caso de inconsistencia interna.
            # Restauramos los datos del Event.
            event.magnitude = old_state["magnitude"]
            event.depth = old_state["depth"]
            event.x = old_state["x"]
            event.y = old_state["y"]

            event.date_time = (
                old_state["date_time"]
            )

            event.revision = (
                old_state["revision"]
            )

            event.priority = (
                old_state["priority"]
            )

            event.is_populated_zone = (
                old_state[
                    "is_populated_zone"
                ]
            )

            event.attention_status = (
                old_state[
                    "attention_status"
                ]
            )

            event.catalog_status = (
                old_state[
                    "catalog_status"
                ]
            )

            event.accepted_stations = set(
                old_state[
                    "accepted_stations"
                ]
            )


            return (
                False,
                "The reactivated event could not be inserted in the AVL",
                None
            )


        inserted_bst = bst_tree.insert(
            event
        )


        if inserted_bst is None:

            avl_tree.delete(
                event.get_key(),
                rebalance=rebalance
            )

            return (
                False,
                "The reactivated event could not be inserted in the BST",
                None
            )


        # Como cambió la información vigente,
        # las asociaciones pueden cambiar.
        self.association_service.recalculate_all()


        self.sismolab.get_metrics() \
            .increment_accepted_corrections()

        self.access_service.update_access_marks()

        return (
            True,
            "Archived event reactivated successfully",
            event
        )
