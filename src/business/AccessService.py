from src.models.Status import CatalogStatus


class AccessService:

    def __init__(
        self,
        sismolab
    ):

        self.sismolab = sismolab


    # ACTUALIZAR MARCAS
    # Recalcula la marca de acceso costoso
    # para todos los nodos activos del AVL.
    def update_access_marks(self):

        scenario = self.sismolab.get_scenario()
        avl_tree = self.sismolab.get_avl_tree()

        access_limit = (
            scenario.get_access_limit()
        )


        for node in avl_tree.breadth_first():

            event = node.get_event()

            depth = avl_tree.get_depth(
                node
            )


            costly_access = (
                event.priority == 3
                and
                depth > access_limit
            )


            node.set_costly_access(
                costly_access
            )


    # CAMBIAR L

    # Cambia el lÃ­mite de acceso
    # y actualiza inmediatamente
    # todas las marcas.
    def update_access_limit(
        self,
        access_limit
    ):

        scenario = self.sismolab.get_scenario()


        if not scenario.set_access_limit(
            access_limit
        ):

            return (
                False,
                "Access limit must be a "
                "non-negative integer",
                None
            )


        self.update_access_marks()


        return (
            True,
            "Access limit updated successfully",
            {
                "access_limit": (
                    scenario.get_access_limit()
                )
            }
        )


    # INFORMACIÃ“N DE ACCESO DE UN EVENTO

    def get_event_access_info(
        self,
        identifier
    ):

        scenario = self.sismolab.get_scenario()


        try:
            identifier = int(identifier)

        except (TypeError, ValueError):

            return (
                False,
                "Invalid identifier",
                None
            )


        event = scenario.get_event_by_id(
            identifier
        )


        if event is None:

            return (
                False,
                "Event not found",
                None
            )


        # La marca solamente aplica
        # a eventos activos.
        if (
            event.catalog_status
            !=
            CatalogStatus.ACTIVE
        ):

            return (
                False,
                "Only active events have "
                "AVL access information",
                None
            )


        avl_tree = self.sismolab.get_avl_tree()


        # Aprovechamos el mÃ©todo que ya tenÃ­a
        # el AVL para contar nodos visitados.
        (
            node,
            comparisons
        ) = avl_tree.search_with_comparisons(
            event.get_key()
        )


        if node is None:

            return (
                False,
                "Active event is not present "
                "in the AVL",
                None
            )


        depth = avl_tree.get_depth(
            node
        )

        access_limit = (
            scenario.get_access_limit()
        )


        costly_access = (
            event.priority == 3
            and
            depth > access_limit
        )


        # Dejamos tambiÃ©n actualizada
        # la marca almacenada en el nodo.
        node.set_costly_access(
            costly_access
        )


        details = {
            "identifier": event.identifier,
            "priority": event.priority,
            "node_depth": depth,
            "access_limit": access_limit,
            "visited_nodes": comparisons,
            "costly_access": costly_access
        }


        return (
            True,
            "Access information calculated",
            details
        )
