from src.structures.BSTNode import BSTNode


class BSTTree:

    def __init__(self):

        self._root = None


    # Retorna la raíz del árbol.
    def get_root(self):

        return self._root


    #  Asigna la raíz del árbol.
    def set_root(self, node):

        self._root = node

        if self._root is not None:
            self._root.set_parent(None)


    # Retorna True si el árbol está vacío.
    # Retorna False si el árbol tiene al menos un nodo.
    def is_empty(self):

        if self._root is None:
            return True

        return False


    # INSERT
    # Recibe un evento.
    # Crea un BSTNode y lo inserta usando la llave del Event.
    # Retorna:
    # - el nodo insertado si la inserción fue exitosa.
    # - None si la llave ya existe.
    def insert(self, event):

        new_node = BSTNode(event)

        if self._root is None:

            self._root = new_node
            return new_node

        return self._insert(
            new_node,
            self._root
        )


    # Método recursivo utilizado por insert().
    def _insert(self, new_node, current_node):

        new_key = new_node.get_key()
        current_key = current_node.get_key()

        # si la llave ya existe, no se inserta el nodo.
        if new_key == current_key:

            return None


        # si la  llave actual no tiene hijos, se inserta el nuevo nodo como hijo izquierdo o derecho según corresponda.
        # si la llave actual tiene hijos, se llama recursivamente a _insert() en el hijo izquierdo o derecho según corresponda.
        # llaves mayores van a la derecha.
        if new_key > current_key:

            if current_node.get_right() is None:

                current_node.set_right(new_node)
                new_node.set_parent(current_node)

                return new_node

            return self._insert(
                new_node,
                current_node.get_right()
            )


        # llaves menores van a la izquierda.
        else:

            if current_node.get_left() is None:

                current_node.set_left(new_node)
                new_node.set_parent(current_node)

                return new_node

            return self._insert(
                new_node,
                current_node.get_left()
            )


    # SEARCH BY KEY
    # busca un nodo usando la llave completa (priority, magnitude, identifier).
    # Retorna:
    # - BSTNode si se encuentra.
    # - None si no se encuentra.
    def search(self, key):

        if self.is_empty():
            return None

        return self._search(
            key,
            self._root
        )


    # Método recursivo utilizado por search().
    def _search(self, key, current_node):

        if current_node is None:
            return None

        current_key = current_node.get_key()


        if key == current_key:

            return current_node


        if key > current_key:

            return self._search(
                key,
                current_node.get_right()
            )


        return self._search(
            key,
            current_node.get_left()
        )


    # SEARCH BY KEY con conteo de comparaciones
    # busca un nodo usando la llave completa (priority, magnitude, identifier).
    # Retorna una tupla (node, comparisons) donde:
    # - node es el nodo encontrado o None.
    # - comparisons es el número de nodos examinados.
    #
    # Returns:
    # (node, comparisons)
    
    def search_with_comparisons(self, key):

        comparisons = 0
        current_node = self._root


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


    
    # SEARCH BY ID

    # busca un nodo usando el identificador del evento.
    # el árbol está ordenado por (priority, magnitude, identifier), no solo por identifier.
    # por esa razón, ambos subárboles pueden necesitar ser visitados.

    # Returns:
    # - BSTNode si es encontrado.
    # - None si no es encontrado.
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


        # buscar en el subárbol izquierdo
        found_node = self._search_by_id(
            identifier,
            current_node.get_left()
        )


        if found_node is not None:

            return found_node


        # si no se encontró en el subárbol izquierdo, buscar en el subárbol derecho
        return self._search_by_id(
            identifier,
            current_node.get_right()
        )


    # ---------------------------------------------------------
    # Recorrido de anchura
    # ---------------------------------------------------------

    # Returns a list of nodes ordered by levels.
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

            traversal.append(current_node)


            if current_node.get_left() is not None:

                queue.append(
                    current_node.get_left()
                )


            if current_node.get_right() is not None:

                queue.append(
                    current_node.get_right()
                )


        return traversal


    # ---------------------------------------------------------
    # PREORDER
    # Root - Left - Right
    # ---------------------------------------------------------

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


        traversal.append(current_node)


        self._preorder(
            current_node.get_left(),
            traversal
        )


        self._preorder(
            current_node.get_right(),
            traversal
        )


    # ---------------------------------------------------------
    # INORDER
    # Left - Root - Right
    # ---------------------------------------------------------

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


        traversal.append(current_node)


        self._inorder(
            current_node.get_right(),
            traversal
        )



    # ---------------------------------------------------------
    # REVERSE INORDER
    # Right - Root - Left
    #
    # Produce las claves en orden descendente.
    # ---------------------------------------------------------

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

        traversal.append(current_node)

        self._reverse_inorder(
            current_node.get_left(),
            traversal
        )


    # ---------------------------------------------------------
    # POSTORDER
    # Left - Right - Root
    # ---------------------------------------------------------

    def postorder(self):

        traversal = []

        self._postorder(
            self._root,
            traversal
        )

        return traversal


    def _postorder(self, current_node, traversal):

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


        traversal.append(current_node)


    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------

    # Deletes a node using its complete key.
    #
    # Returns:
    # - The deleted Event if the node existed.
    # - None if the node was not found.
    def delete(self, key):

        current_node = self.search(key)


        if current_node is None:

            return None


        deleted_event = current_node.get_event()


        # -----------------------------------------------------
        # CASE 1:
        # The node has no children.
        # -----------------------------------------------------

        if (
            current_node.get_left() is None
            and
            current_node.get_right() is None
        ):

            parent = current_node.get_parent()


            # The node is the root.
            if parent is None:

                self._root = None


            # The node is the left child.
            elif parent.get_left() == current_node:

                parent.set_left(None)


            # The node is the right child.
            else:

                parent.set_right(None)


            current_node.set_parent(None)

            return deleted_event


        # -----------------------------------------------------
        # CASE 2:
        # The node only has a left child.
        # -----------------------------------------------------

        if (
            current_node.get_left() is not None
            and
            current_node.get_right() is None
        ):

            child = current_node.get_left()

            parent = current_node.get_parent()


            # The node is the root.
            if parent is None:

                self._root = child

                child.set_parent(None)


            # The node is the left child of its parent.
            elif parent.get_left() == current_node:

                parent.set_left(child)

                child.set_parent(parent)


            # The node is the right child of its parent.
            else:

                parent.set_right(child)

                child.set_parent(parent)


            current_node.set_left(None)
            current_node.set_parent(None)

            return deleted_event


        # -----------------------------------------------------
        # CASE 3:
        # The node only has a right child.
        # -----------------------------------------------------

        if (
            current_node.get_left() is None
            and
            current_node.get_right() is not None
        ):

            child = current_node.get_right()

            parent = current_node.get_parent()


            # The node is the root.
            if parent is None:

                self._root = child

                child.set_parent(None)


            # The node is the left child of its parent.
            elif parent.get_left() == current_node:

                parent.set_left(child)

                child.set_parent(parent)


            # The node is the right child of its parent.
            else:

                parent.set_right(child)

                child.set_parent(parent)


            current_node.set_right(None)
            current_node.set_parent(None)

            return deleted_event


        # -----------------------------------------------------
        # CASE 4:
        # The node has two children.
        #
        # We use the greatest node from the left subtree,
        # just like the method used in class.
        # -----------------------------------------------------

        predecessor = current_node.get_left()


        # Find the greatest node in the left subtree.
        while predecessor.get_right() is not None:

            predecessor = predecessor.get_right()


        predecessor_parent = predecessor.get_parent()

        predecessor_left_child = predecessor.get_left()


        # Replace the Event stored in the node to delete
        # with the Event stored in the predecessor.
        current_node.set_event(
            predecessor.get_event()
        )


        # If the predecessor is the direct left child
        # of the current node.
        if predecessor_parent == current_node:

            current_node.set_left(
                predecessor_left_child
            )


            if predecessor_left_child is not None:

                predecessor_left_child.set_parent(
                    current_node
                )


        # Otherwise, the predecessor was the right child
        # of another node.
        else:

            predecessor_parent.set_right(
                predecessor_left_child
            )


            if predecessor_left_child is not None:

                predecessor_left_child.set_parent(
                    predecessor_parent
                )


        # Disconnect the old predecessor node.
        predecessor.set_parent(None)
        predecessor.set_left(None)
        predecessor.set_right(None)


        return deleted_event


    # ---------------------------------------------------------
    # MINIMUM
    # ---------------------------------------------------------

    # Returns the node with the smallest key.
    def minimum(self):

        if self.is_empty():

            return None


        return self._minimum(
            self._root
        )


    def _minimum(self, current_node):

        if current_node.get_left() is None:

            return current_node


        return self._minimum(
            current_node.get_left()
        )


    # ---------------------------------------------------------
    # MAXIMUM
    # ---------------------------------------------------------

    # Returns the node with the greatest key.
    def maximum(self):

        if self.is_empty():

            return None


        return self._maximum(
            self._root
        )


    def _maximum(self, current_node):

        if current_node.get_right() is None:

            return current_node


        return self._maximum(
            current_node.get_right()
        )


    # ---------------------------------------------------------
    # K-TH SMALLEST
    # ---------------------------------------------------------

    # Returns the k-th smallest node according to the key.
    #
    # k starts at 1.
    #
    # Example:
    # k = 1 -> smallest node.
    # k = 2 -> second smallest node.
    def kth_smallest(self, k):

        if self.is_empty():

            return None


        traversal = self.inorder()


        if k < 1:

            return None


        if k > len(traversal):

            return None


        return traversal[k - 1]


    # ---------------------------------------------------------
    # TREE HEIGHT
    # ---------------------------------------------------------

    # Returns:
    # -1 for an empty tree.
    #  0 for a tree with only the root.
    def height(self):

        return self._height(
            self._root
        )


    def _height(self, current_node):

        if current_node is None:

            return -1


        left_height = self._height(
            current_node.get_left()
        )


        right_height = self._height(
            current_node.get_right()
        )


        if left_height > right_height:

            return left_height + 1


        return right_height + 1


    # ---------------------------------------------------------
    # LEAF COUNT
    # ---------------------------------------------------------

    # Returns the number of leaf nodes.
    def leaf_count(self):

        return self._leaf_count(
            self._root
        )


    def _leaf_count(self, current_node):

        if current_node is None:

            return 0


        if (
            current_node.get_left() is None
            and
            current_node.get_right() is None
        ):

            return 1


        left_leaves = self._leaf_count(
            current_node.get_left()
        )


        right_leaves = self._leaf_count(
            current_node.get_right()
        )


        return left_leaves + right_leaves
