from src.structures.AVLNode import AVLNode


class AVLTree:

    def __init__(self):

        self._root = None

        # Registro temporal de casos de balanceo
        # y rotaciones realizadas por el AVL.
        self._rotation_log = []

    # =========================================================
    # RAÃZ Y ESTADO DEL ÃRBOL
    # =========================================================

    # Retorna la raÃ­z del Ã¡rbol.
    def get_root(self):

        return self._root


    # Cambia la raÃ­z del Ã¡rbol.
    # La raÃ­z nunca debe tener padre.
    def set_root(self, node):

        self._root = node

        if self._root is not None:
            self._root.set_parent(None)


    # =========================================================
    # ROTATION LOG
    # =========================================================

    # Limpia las rotaciones registradas.
    #
    # Se llama antes de comenzar una operaciÃ³n
    # para saber exactamente quÃ© rotaciones
    # produjo esa operaciÃ³n.
    def clear_rotation_log(self):

        self._rotation_log.clear()


    # Retorna una copia del registro.
    def get_rotation_log(self):

        return [
            dict(item)
            for item in self._rotation_log
        ]


    # Registra el tipo de caso AVL encontrado:
    # LL, RR, LR o RL.
    def _log_balance_case(
        self,
        case,
        node
    ):

        self._rotation_log.append({
            "kind": "case",
            "case": case,
            "node_id": node.get_event().identifier,
            "key": node.get_key()
        })


    # Registra un giro elemental.
    def _log_rotation(
        self,
        direction,
        node
    ):

        self._rotation_log.append({
            "kind": "rotation",
            "direction": direction,
            "pivot_id": node.get_event().identifier,
            "pivot_key": node.get_key()
        })

    # Retorna True si el Ã¡rbol estÃ¡ vacÃ­o.
    # Retorna False si contiene al menos un nodo.
    def is_empty(self):

        if self._root is None:
            return True

        return False


    # INSERTAR

    # Recibe un Event.
    # rebalance = True:
    # inserciÃ³n normal del AVL.
    #
    # rebalance = False:
    # inserciÃ³n en modo estrÃ©s.
    # Mantiene el orden BST pero no realiza rotaciones.
    #
    # Retorna:
    # - el AVLNode insertado.
    # - None si la llave ya existÃ­a.
    def insert(self, event, rebalance=True):

        new_node = AVLNode(event)


        # Si no existe raÃ­z, el nuevo nodo se convierte en raÃ­z.
        if self._root is None:

            self._root = new_node

            return new_node


        inserted_node = self._insert(
            new_node,
            self._root
        )


        # Si la llave ya existÃ­a, no se insertÃ³.
        if inserted_node is None:

            return None


        # En modo normal actualizamos y balanceamos.
        if rebalance:

            self._rebalance_upward(
                inserted_node.get_parent()
            )


        # En modo estrÃ©s no hacemos rotaciones,
        # pero las alturas deben seguir actualizadas.
        else:

            self._update_heights_upward(
                inserted_node.get_parent()
            )


        return inserted_node


    # MÃ©todo privado recursivo para insertar.
    def _insert(self, new_node, current_node):

        new_key = new_node.get_key()
        current_key = current_node.get_key()


        # No permitimos dos nodos con la misma llave.
        if new_key == current_key:

            return None

        """
        Cuando va a insertar un nuevoi evento, se debe guardar algo tipo asi: {'evento_id':'77u34tyr764'}
        """
        # Una llave menor va hacia la izquierda.
        if new_key < current_key:

            if current_node.get_left() is None:

                current_node.set_left(new_node)

                new_node.set_parent(
                    current_node
                )

                return new_node


            return self._insert(
                new_node,
                current_node.get_left()
            )


        # Una llave mayor va hacia la derecha.
        else:

            if current_node.get_right() is None:

                current_node.set_right(new_node)

                new_node.set_parent(
                    current_node
                )

                return new_node


            return self._insert(
                new_node,
                current_node.get_right()
            )


    # BUSCAR POR LLAVE
    # Busca utilizando la llave completa:
    # (priority, magnitude, identifier).
    #
    # Retorna:
    # - AVLNode si existe.
    # - None si no existe.
    def search(self, key):

        if self.is_empty():

            return None


        return self._search(
            key,
            self._root
        )


    def _search(self, key, current_node):

        if current_node is None:

            return None


        current_key = current_node.get_key()


        if key == current_key:

            return current_node


        if key < current_key:

            return self._search(
                key,
                current_node.get_left()
            )


        return self._search(
            key,
            current_node.get_right()
        )


    # BUSCAR POR LLAVE CONTANDO COMPARACIONES

    # Busca por K y ademÃ¡s cuenta cuÃ¡ntos nodos fueron visitados.
    #
    # Retorna una tupla:
    #
    # (nodo, cantidad_comparaciones)
    def search_with_comparisons(self, key):

        current_node = self._root

        comparisons = 0


        while current_node is not None:

            comparisons += 1

            current_key = current_node.get_key()


            if key == current_key:

                return current_node, comparisons


            if key < current_key:

                current_node = current_node.get_left()

            else:

                current_node = current_node.get_right()


        return None, comparisons


    # BUSCAR SOLAMENTE POR ID

    # Busca un Event utilizando Ãºnicamente su identifier.
    #
    # Como el AVL estÃ¡ ordenado por K=(P,M,I),
    # el ID por sÃ­ solo no permite decidir si ir
    # solamente a izquierda o derecha.
    #
    # Por eso puede ser necesario recorrer todo el Ã¡rbol.
    def search_by_id(self, identifier):

        if self.is_empty():

            return None


        return self._search_by_id(
            identifier,
            self._root
        )


    def _search_by_id(self, identifier, current_node):

        if current_node is None:

            return None


        current_event = current_node.get_event()


        if current_event.identifier == identifier:

            return current_node


        # Primero buscamos en el subÃ¡rbol izquierdo.
        found_node = self._search_by_id(
            identifier,
            current_node.get_left()
        )


        if found_node is not None:

            return found_node


        # Si no apareciÃ³ a la izquierda,
        # buscamos en el subÃ¡rbol derecho.
        return self._search_by_id(
            identifier,
            current_node.get_right()
        )


    # =========================================================
    # RECORRIDO EN ANCHURA
    # =========================================================

    def breadth_first(self):

        if self.is_empty():

            return []


        return self._breadth_first(
            self._root
        )


    def _breadth_first(self, root):

        queue = []

        traversal = []

        queue.append(root)


        while len(queue) > 0:

            current_node = queue.pop(0)

            traversal.append(
                current_node
            )


            if current_node.get_left() is not None:

                queue.append(
                    current_node.get_left()
                )


            if current_node.get_right() is not None:

                queue.append(
                    current_node.get_right()
                )


        return traversal


    # =========================================================
    # PREORDEN
    # RaÃ­z - Izquierda - Derecha
    # =========================================================

    def preorder(self):

        traversal = []

        self._preorder(
            self._root,
            traversal
        )

        return traversal


    def _preorder(self, current_node, traversal):

        if current_node is None:

            return


        traversal.append(
            current_node
        )


        self._preorder(
            current_node.get_left(),
            traversal
        )


        self._preorder(
            current_node.get_right(),
            traversal
        )


    # =========================================================
    # INORDEN
    # Izquierda - RaÃ­z - Derecha
    # =========================================================

    def inorder(self):

        traversal = []

        self._inorder(
            self._root,
            traversal
        )

        return traversal


    def _inorder(self, current_node, traversal):

        if current_node is None:

            return


        self._inorder(
            current_node.get_left(),
            traversal
        )


        traversal.append(
            current_node
        )


        self._inorder(
            current_node.get_right(),
            traversal
        )


    # =========================================================
    # INORDEN INVERSO
    # Derecha - RaÃ­z - Izquierda
    #
    # Devuelve las llaves de mayor a menor.
    # Nos servirÃ¡ para consultas Top-K.
    # =========================================================

    def reverse_inorder(self):

        traversal = []

        self._reverse_inorder(
            self._root,
            traversal
        )

        return traversal


    def _reverse_inorder(
        self,
        current_node,
        traversal
    ):

        if current_node is None:

            return


        self._reverse_inorder(
            current_node.get_right(),
            traversal
        )


        traversal.append(
            current_node
        )


        self._reverse_inorder(
            current_node.get_left(),
            traversal
        )


    # =========================================================
    # POSTORDEN
    # Izquierda - Derecha - RaÃ­z
    # =========================================================

    def postorder(self):

        traversal = []

        self._postorder(
            self._root,
            traversal
        )

        return traversal


    def _postorder(
        self,
        current_node,
        traversal
    ):

        if current_node is None:

            return


        self._postorder(
            current_node.get_left(),
            traversal
        )


        self._postorder(
            current_node.get_right(),
            traversal
        )


        traversal.append(
            current_node
        )


    # =========================================================
    # ALTURA
    # =========================================================

    # Retorna:
    # -1 si el nodo no existe.
    # altura guardada si existe.
    def _node_height(self, node):

        if node is None:

            return -1


        return node.get_height()


    # Actualiza la altura de un nodo.
    def _update_height(self, node):

        if node is None:

            return


        left_height = self._node_height(
            node.get_left()
        )


        right_height = self._node_height(
            node.get_right()
        )


        maximum_height = max(
            left_height,
            right_height
        )


        node.set_height(
            maximum_height + 1
        )


    # Actualiza alturas desde un nodo hasta la raÃ­z.
    def _update_heights_upward(self, node):

        current_node = node


        while current_node is not None:

            self._update_height(
                current_node
            )

            current_node = (
                current_node.get_parent()
            )


    # Retorna la altura del Ã¡rbol.
    #
    # Ãrbol vacÃ­o = -1.
    # Una sola raÃ­z = 0.
    def height(self):

        if self._root is None:

            return -1


        return self._root.get_height()


    # =========================================================
    # FACTOR DE BALANCE
    # =========================================================

    # Factor:
    #
    # altura izquierda - altura derecha
    def get_balance_factor(self, node):

        if node is None:

            return 0


        left_height = self._node_height(
            node.get_left()
        )


        right_height = self._node_height(
            node.get_right()
        )


        return (
            left_height
            -
            right_height
        )


    # =========================================================
    # DETECTAR CASO DE DESBALANCE
    # =========================================================

    # Retorna:
    # "LL"
    # "RR"
    # "LR"
    # "RL"
    # o None si no estÃ¡ desbalanceado.
    def _detect_imbalance_case(self, node):

        balance = self.get_balance_factor(
            node
        )


        # El Ã¡rbol pesa demasiado hacia la izquierda.
        if balance > 1:

            left_balance = (
                self.get_balance_factor(
                    node.get_left()
                )
            )


            # Izquierda - Izquierda.
            if left_balance >= 0:

                return "LL"


            # Izquierda - Derecha.
            return "LR"


        # El Ã¡rbol pesa demasiado hacia la derecha.
        if balance < -1:

            right_balance = (
                self.get_balance_factor(
                    node.get_right()
                )
            )


            # Derecha - Derecha.
            if right_balance <= 0:

                return "RR"


            # Derecha - Izquierda.
            return "RL"


        return None


    # =========================================================
    # GIRO SIMPLE A LA IZQUIERDA
    # Caso RR
    # =========================================================

    def _rotate_left(self, superior):

        self._log_rotation(
            "LEFT",
            superior
        )

        middle = superior.get_right()


        # Este subÃ¡rbol cambia de padre durante el giro.
        middle_left = middle.get_left()


        # Guardamos el padre antiguo del nodo superior.
        old_parent = superior.get_parent()


        # La mitad sube.
        middle.set_parent(
            old_parent
        )


        # Si superior era la raÃ­z,
        # middle pasa a ser la nueva raÃ­z.
        if old_parent is None:

            self._root = middle


        # Si superior era hijo izquierdo.
        elif old_parent.get_left() == superior:

            old_parent.set_left(
                middle
            )


        # Si superior era hijo derecho.
        else:

            old_parent.set_right(
                middle
            )


        # Superior baja y queda como hijo izquierdo de middle.
        middle.set_left(
            superior
        )

        superior.set_parent(
            middle
        )


        # El antiguo hijo izquierdo de middle
        # pasa a ser hijo derecho de superior.
        superior.set_right(
            middle_left
        )


        if middle_left is not None:

            middle_left.set_parent(
                superior
            )


        # Primero se actualiza el que quedÃ³ abajo.
        self._update_height(
            superior
        )


        # DespuÃ©s el que quedÃ³ arriba.
        self._update_height(
            middle
        )


        return middle


    # =========================================================
    # GIRO SIMPLE A LA DERECHA
    # Caso LL
    # =========================================================

    def _rotate_right(self, superior):

        self._log_rotation(
            "RIGHT",
            superior
        )
        middle = superior.get_left()


        middle_right = middle.get_right()


        old_parent = superior.get_parent()


        # La mitad sube.
        middle.set_parent(
            old_parent
        )


        # Si superior era raÃ­z,
        # middle se convierte en nueva raÃ­z.
        if old_parent is None:

            self._root = middle


        # Si superior era hijo izquierdo.
        elif old_parent.get_left() == superior:

            old_parent.set_left(
                middle
            )


        # Si superior era hijo derecho.
        else:

            old_parent.set_right(
                middle
            )


        # Superior baja a la derecha.
        middle.set_right(
            superior
        )

        superior.set_parent(
            middle
        )


        # El antiguo hijo derecho de middle
        # pasa a ser hijo izquierdo de superior.
        superior.set_left(
            middle_right
        )


        if middle_right is not None:

            middle_right.set_parent(
                superior
            )


        self._update_height(
            superior
        )


        self._update_height(
            middle
        )


        return middle


    # =========================================================
    # BALANCEAR UN NODO
    # =========================================================

    # Revisa un nodo y ejecuta la rotaciÃ³n necesaria.
    #
    # Retorna la nueva raÃ­z local del subÃ¡rbol.
    def _rebalance_node(self, node):

        if node is None:

            return None


        self._update_height(
            node
        )


        case = self._detect_imbalance_case(
            node
        )


        # No necesita rotaciÃ³n.
        if case is None:

            return node

        self._log_balance_case(
            case,
            node
        )

        # LL:
        # giro simple a la derecha.
        if case == "LL":

            return self._rotate_right(
                node
            )


        # RR:
        # giro simple a la izquierda.
        if case == "RR":

            return self._rotate_left(
                node
            )


        # LR:
        # primero gira el hijo izquierdo
        # hacia la izquierda.
        # DespuÃ©s gira el superior
        # hacia la derecha.
        if case == "LR":

            self._rotate_left(
                node.get_left()
            )

            return self._rotate_right(
                node
            )


        # RL:
        # primero gira el hijo derecho
        # hacia la derecha.
        # DespuÃ©s gira el superior
        # hacia la izquierda.
        if case == "RL":

            self._rotate_right(
                node.get_right()
            )

            return self._rotate_left(
                node
            )


    # =========================================================
    # BALANCEAR DESDE UN NODO HASTA LA RAÃZ
    # =========================================================

    def _rebalance_upward(self, node):

        current_node = node


        while current_node is not None:

            # Puede ocurrir una rotaciÃ³n y cambiar
            # cuÃ¡l nodo quedÃ³ arriba.
            new_local_root = (
                self._rebalance_node(
                    current_node
                )
            )


            current_node = (
                new_local_root.get_parent()
            )


    # ELIMINAR

    # Elimina utilizando la llave completa K.
    #
    # rebalance = True:
    # AVL normal.
    #
    # rebalance = False:
    # modo estrÃ©s, no realiza rotaciones.
    #
    # Retorna:
    # - Event eliminado.
    # - None si no existÃ­a.
    def delete(self, key, rebalance=True):

        node = self.search(
            key
        )


        if node is None:

            return None


        deleted_event = (
            node.get_event()
        )


        # El mÃ©todo devuelve desde quÃ© nodo
        # debemos comenzar a actualizar/balancear.
        start_node = self._delete_node(
            node
        )


        if rebalance:

            self._rebalance_upward(
                start_node
            )


        else:

            self._update_heights_upward(
                start_node
            )


        return deleted_event


    # Elimina fÃ­sicamente un nodo.
    #
    # Retorna el nodo desde el cual se deben
    # actualizar alturas y balance.
    def _delete_node(self, node):

        # -----------------------------------------------------
        # CASO 1:
        # Nodo sin hijos.
        # ----------------------------------------------------

        # data = {'evento': nodoantesdeeliminar.__dict__, 'type': 'delete'}
        # O esta otra forma
        # data = {'evento': nodoantesdeeliminar.to_dict(), 'type': ActionType.DELETE} #NOTA ActionType.DELETE debe ser string
        # FilesUtils.write_json()
        # Justo despues de esta linea ya se puede eliminar
        # 
        if (
            node.get_left() is None
            and
            node.get_right() is None
        ):

            parent = node.get_parent()


            if parent is None:

                self._root = None


            elif parent.get_left() == node:

                parent.set_left(None)


            else:

                parent.set_right(None)


            node.set_parent(None)


            return parent


        # -----------------------------------------------------
        # CASO 2:
        # Solo hijo izquierdo.
        # -----------------------------------------------------

        if (
            node.get_left() is not None
            and
            node.get_right() is None
        ):

            child = node.get_left()

            parent = node.get_parent()


            if parent is None:

                self._root = child

                child.set_parent(None)


            elif parent.get_left() == node:

                parent.set_left(child)

                child.set_parent(parent)


            else:

                parent.set_right(child)

                child.set_parent(parent)


            node.set_left(None)
            node.set_parent(None)


            if parent is None:

                return child


            return parent


        # -----------------------------------------------------
        # CASO 3:
        # Solo hijo derecho.
        # -----------------------------------------------------

        if (
            node.get_left() is None
            and
            node.get_right() is not None
        ):

            child = node.get_right()

            parent = node.get_parent()


            if parent is None:

                self._root = child

                child.set_parent(None)


            elif parent.get_left() == node:

                parent.set_left(child)

                child.set_parent(parent)


            else:

                parent.set_right(child)

                child.set_parent(parent)


            node.set_right(None)
            node.set_parent(None)


            if parent is None:

                return child


            return parent


        # -----------------------------------------------------
        # CASO 4:
        # Tiene dos hijos.
        #
        # Utilizamos el mayor nodo
        # del subÃ¡rbol izquierdo.
        # -----------------------------------------------------

        predecessor = self._maximum_from(
            node.get_left()
        )


        # Copiamos el Event del predecesor.
        node.set_event(
            predecessor.get_event()
        )


        # El predecesor no puede tener hijo derecho.
        # Puede tener hijo izquierdo.
        predecessor_parent = (
            predecessor.get_parent()
        )

        predecessor_child = (
            predecessor.get_left()
        )


        # Si el predecesor es hijo directo del nodo.
        if predecessor_parent == node:

            node.set_left(
                predecessor_child
            )


            if predecessor_child is not None:

                predecessor_child.set_parent(
                    node
                )


            start_node = node


        # Si estÃ¡ mÃ¡s abajo en el subÃ¡rbol.
        else:

            predecessor_parent.set_right(
                predecessor_child
            )


            if predecessor_child is not None:

                predecessor_child.set_parent(
                    predecessor_parent
                )


            start_node = (
                predecessor_parent
            )


        # Desconectamos el nodo antiguo.
        predecessor.set_parent(None)
        predecessor.set_left(None)
        predecessor.set_right(None)


        return start_node


    # =========================================================
    # MÃNIMO Y MÃXIMO
    # =========================================================

    def minimum(self):

        if self.is_empty():

            return None


        return self._minimum_from(
            self._root
        )


    def _minimum_from(self, node):

        current_node = node


        while current_node.get_left() is not None:

            current_node = (
                current_node.get_left()
            )


        return current_node


    def maximum(self):

        if self.is_empty():

            return None


        return self._maximum_from(
            self._root
        )


    def _maximum_from(self, node):

        current_node = node


        while current_node.get_right() is not None:

            current_node = (
                current_node.get_right()
            )


        return current_node


  
    # K-Ã‰SIMO MENOR

    def kth_smallest(self, k):

        traversal = self.inorder()


        if k < 1:

            return None


        if k > len(traversal):

            return None


        return traversal[k - 1]



    # CANTIDAD DE HOJAS

    def leaf_count(self):

        return self._leaf_count(
            self._root
        )


    def _leaf_count(self, node):

        if node is None:

            return 0


        if (
            node.get_left() is None
            and
            node.get_right() is None
        ):

            return 1


        left_leaves = self._leaf_count(
            node.get_left()
        )


        right_leaves = self._leaf_count(
            node.get_right()
        )


        return (
            left_leaves
            +
            right_leaves
        )


    # CANTIDAD DE NODOS

    # Puede recibir una raÃ­z especÃ­fica para conocer
    # el tamaÃ±o de un subÃ¡rbol.
    def count_nodes(self, node=None):

        if node is None:

            node = self._root


        return self._count_nodes(
            node
        )


    def _count_nodes(self, node):

        if node is None:

            return 0


        left_count = self._count_nodes(
            node.get_left()
        )


        right_count = self._count_nodes(
            node.get_right()
        )


        return (
            1
            +
            left_count
            +
            right_count
        )


    # =========================================================
    # PROFUNDIDAD DE UN NODO
    # =========================================================

    # La raÃ­z tiene profundidad 0.
    #
    # El mÃ©todo recorre los padres hasta llegar a la raÃ­z.
    def get_depth(self, node):

        if node is None:

            return None


        depth = 0

        current_node = node


        while current_node.get_parent() is not None:

            depth += 1

            current_node = (
                current_node.get_parent()
            )


        return depth


    # DESPRENDER UN SUBÃRBOL

    # Quita un subÃ¡rbol completo del AVL activo,
    # pero NO destruye sus nodos.
    # Esto permitirÃ¡ guardar la raÃ­z retornada
    # dentro de History.
    #
    # Los hijos internos permanecen conectados.
    #
    # Retorna:
    # - la raÃ­z del subÃ¡rbol separado.
    # - None si el nodo recibido era None.
    def detach_subtree(
        self,
        node,
        rebalance=True
    ):

        if node is None:

            return None


        parent = node.get_parent()


        # Si se estÃ¡ desprendiendo todo el Ã¡rbol.
        if parent is None:

            self._root = None

            node.set_parent(None)

            return node


        # Si era hijo izquierdo.
        if parent.get_left() == node:

            parent.set_left(None)


        # Si era hijo derecho.
        else:

            parent.set_right(None)


        # Ahora la raÃ­z archivada deja de tener padre.
        node.set_parent(None)


        # El Ã¡rbol activo debe actualizarse.
        if rebalance:

            self._rebalance_upward(
                parent
            )


        else:

            self._update_heights_upward(
                parent
            )


        return node


  
    # RECALCULAR TODAS LAS ALTURAS

    # Recalcula las alturas desde las hojas hacia la raÃ­z.
    #
    # Retorna la altura calculada del nodo recibido.
    def _recalculate_heights(self, node):

        if node is None:

            return -1


        left_height = self._recalculate_heights(
            node.get_left()
        )


        right_height = self._recalculate_heights(
            node.get_right()
        )


        calculated_height = (
            max(
                left_height,
                right_height
            )
            + 1
        )


        node.set_height(
            calculated_height
        )


        return calculated_height


    # MÃ©todo pÃºblico para recalcular todas las alturas.
    def recalculate_heights(self):

        return self._recalculate_heights(
            self._root
        )


    # BUSCAR UN NODO DESBALANCEADO

    # Busca primero en los niveles inferiores.
    # Esto permite corregir desde abajo hacia arriba.
    def _find_unbalanced_node(self, node):

        if node is None:

            return None


        found_left = (
            self._find_unbalanced_node(
                node.get_left()
            )
        )


        if found_left is not None:

            return found_left


        found_right = (
            self._find_unbalanced_node(
                node.get_right()
            )
        )


        if found_right is not None:

            return found_right


        balance = self.get_balance_factor(
            node
        )


        if (
            balance > 1
            or
            balance < -1
        ):

            return node


        return None

    # Busca un nodo desbalanceado y ademÃ¡s
    # cuenta cuÃ¡ntos nodos fueron examinados.
    def _find_unbalanced_node_with_count(
        self,
        node
    ):

        visited = 0


        def visit(current):

            nonlocal visited


            if current is None:
                return None


            visited += 1


            found_left = visit(
                current.get_left()
            )

            if found_left is not None:
                return found_left


            found_right = visit(
                current.get_right()
            )

            if found_right is not None:
                return found_right


            balance = self.get_balance_factor(
                current
            )


            if (
                balance > 1
                or
                balance < -1
            ):

                return current


            return None


        return visit(node), visited


    # Retorna True si todo el Ã¡rbol
    # cumple la condiciÃ³n AVL.
    def is_balanced(self):

        self.recalculate_heights()

        return (
            self._find_unbalanced_node(
                self._root
            )
            is None
        )

    # RECUPERACIÃ“N GLOBAL DESPUÃ‰S DEL MODO ESTRÃ‰S


    # Busca desbalances y realiza rotaciones
    # hasta que todo el Ã¡rbol vuelva a cumplir AVL.
    #
    # No vacÃ­a el Ã¡rbol ni lo reconstruye.

    # RECUPERACIÃ“N GLOBAL DESPUÃ‰S DEL MODO ESTRÃ‰S
    # Corrige el Ã¡rbol existente.
    # NO vacÃ­a el AVL.
    # NO reconstruye a partir de una lista.
    def recover_balance(self):

        nodes_examined = 0
        rebalance_steps = 0


        while True:

            # Primero aseguramos que las alturas
            # almacenadas sean correctas.
            self.recalculate_heights()


            (
                unbalanced_node,
                visited
            ) = (
                self._find_unbalanced_node_with_count(
                    self._root
                )
            )


            nodes_examined += visited


            # No quedan desbalances.
            if unbalanced_node is None:
                break


            # Arreglamos un desbalance del Ã¡rbol
            # existente.
            self._rebalance_node(
                unbalanced_node
            )


            rebalance_steps += 1


        self.recalculate_heights()


        return {
            "nodes_examined": nodes_examined,
            "rebalance_steps": rebalance_steps
        }


    # =========================================================
    # DIBUJAR EN CONSOLA
    # =========================================================

    # MÃ©todo Ãºnicamente Ãºtil para pruebas y depuraciÃ³n.
    def draw(self):

        if self._root is None:

            print("El Ã¡rbol estÃ¡ vacÃ­o")

            return


        self._draw(
            self._root,
            "",
            "R"
        )


    def _draw(
        self,
        current_node,
        space,
        position
    ):

        if current_node is None:

            return


        self._draw(
            current_node.get_right(),
            space + "     ",
            "D"
        )


        print(
            space
            +
            position
            +
            "â”€â”€ "
            +
            str(current_node.get_key())
            +
            " h="
            +
            str(current_node.get_height())
        )


        self._draw(
            current_node.get_left(),
            space + "     ",
            "I"
        )
