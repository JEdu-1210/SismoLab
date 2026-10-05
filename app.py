import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))
import streamlit as st
import json
import tempfile
import graphviz
from datetime import datetime

# Importación de modelos y servicios del backend

from src.services.persistencia import PersistenceService
from src.services.querry_service import QueryService
from src.services.undo_service import UndoService
from src.services.version_service import VersionService
from src.models.Scenario import Scenario
from src.models.SismoLab import SismoLab
from datetime import datetime,timezone

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA Y ESTADO GLOBAL (st.session_state)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="SismoLab - Motor AVL",
    page_icon="🌋",
    layout="wide"
)

# Inicializar instancias persistentes entre clics
if "sismolab" not in st.session_state:
    # Genera el objeto datetime válido en UTC y sin microsegundos
    initial_clock = datetime.now(timezone.utc).replace(microsecond=0)
    
    # Pasamos 'initial_clock' (objeto datetime), NO 'initial_clock_str'
    default_scenario = Scenario(initial_clock)
    st.session_state.sismolab = SismoLab(default_scenario)
    st.session_state.sismolab = SismoLab(default_scenario)
if "undo_srv" not in st.session_state:
    st.session_state.undo_srv = UndoService()
if "version_srv" not in st.session_state:
    st.session_state.version_srv = VersionService()

sismolab: SismoLab = st.session_state.sismolab
undo_srv: UndoService = st.session_state.undo_srv
version_srv: VersionService = st.session_state.version_srv

# Helper para registrar snapshots de Deshacer antes de mutaciones
def record_undo(action_type: str, desc: str):
    undo_srv.record_action(action_type, desc, sismolab)
def extract_queue_items(queue_obj):
    """Extrae los elementos de la cola adaptándose a su estructura interna."""
    if not queue_obj:
        return []
    if hasattr(queue_obj, "to_list"):
        return queue_obj.to_list()
    elif hasattr(queue_obj, "items"):
        return queue_obj.items
    elif hasattr(queue_obj, "_items"):
        return queue_obj._items
    elif hasattr(queue_obj, "queue"):
        return queue_obj.queue
    elif hasattr(queue_obj, "_queue"):
        return queue_obj._queue
    else:
        try:
            return list(queue_obj)
        except TypeError:
            return []

# Helper para renderizar el árbol en formato Graphviz
def generate_tree_dot(root_node, limit_L=3):
    dot = graphviz.Digraph(comment="Árbol AVL SismoLab")
    dot.attr(nodesep='0.3', ranksep='0.4')

    def _traverse(node, depth=0):
        if not node:
            return
        event = node.get_event() if hasattr(node, "get_event") else node.event
        p = event.priority
        
        # Colores por prioridad P
        colors = {3: "#ff6b6b", 2: "#feca57", 1: "#1dd1a1"}
        fillcolor = colors.get(p, "#ffffff")
        
        # Acceso costoso: P=3 y profundidad > L
        is_costly = (p == 3 and depth > limit_L)
        color = "#900000" if is_costly else "#222222"
        penwidth = "3.0" if is_costly else "1.0"

        label = f"SIS-{event.identifier:04d}\nP:{p} | M:{event.magnitude}\nH:{event.depth}km"
        dot.node(
            str(event.identifier),
            label=label,
            shape="circle",
            style="filled",
            fillcolor=fillcolor,
            color=color,
            penwidth=penwidth,
            fontname="Arial"
        )

        left = node.get_left() if hasattr(node, "get_left") else getattr(node, "left", None)
        right = node.get_right() if hasattr(node, "get_right") else getattr(node, "right", None)

        if left:
            left_event = left.get_event() if hasattr(left, "get_event") else left.event
            dot.edge(str(event.identifier), str(left_event.identifier))
            _traverse(left, depth + 1)
        if right:
            right_event = right.get_event() if hasattr(right, "get_event") else right.event
            dot.edge(str(event.identifier), str(right_event.identifier))
            _traverse(right, depth + 1)

    _traverse(root_node)
    return dot

# -----------------------------------------------------------------------------
# 2. ENCABEZADO Y BARRA DE ESTADO GENERAL
# -----------------------------------------------------------------------------
st.title("🌋 SismoLab — Centro de Control Sísmico")

scenario = sismolab.get_scenario()
is_stress = scenario.is_stress_mode() if scenario else False

col_h1, col_h2, col_h3, col_h4, col_h5 = st.columns(5)
with col_h1:
    st.metric("Modo Activo", "ESTRÉS ⚠️" if is_stress else "NORMAL ✅")
with col_h2:
    st.metric("Reloj de Simulación", scenario.get_simulation_clock().strftime("%H:%M:%S") if scenario else "--")
with col_h3:
    st.metric("Eventos Activos", sismolab.get_avl_tree().count_nodes() if not sismolab.get_avl_tree().is_empty() else 0)
with col_h4:
    raw_queue = extract_queue_items(sismolab.get_report_queue())
    st.metric("Cola de Reportes", len(raw_queue))



with col_h5:
    if st.button("⏪ Deshacer (Undo)", disabled=not undo_srv.can_undo(), use_container_width=True):
        res = undo_srv.undo(sismolab)
        if res.error:
            st.error(res.error)
        else:
            st.success(res.msg)
            st.rerun()

st.divider()

# -----------------------------------------------------------------------------
# 3. PESTAÑAS PRINCIPALES DE NAVEGACIÓN
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "🌳 Árbol y Cola FIFO",
    "⚙️ Control del Escenario",
    "🔍 Consultas Analíticas (P.11)",
    "💾 Persistencia y Versiones"
])

# =============================================================================
# PESTAÑA 1: VISUALIZACIÓN DEL ÁRBOL Y PROCESAMIENTO DE COLA
# =============================================================================
with tab1:
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("Estructura del Árbol Activo")
        root = sismolab.get_avl_tree().get_root()
        limit_L = scenario.get_access_limit() if scenario else 3

        if root:
            dot_graph = generate_tree_dot(root, limit_L=limit_L)
            st.graphviz_chart(dot_graph, use_container_width=True)
        else:
            st.info("El catálogo activo no contiene nodos.")

    with col_right:
        st.subheader("Cola de Reportes (FIFO)")
        
        # Extracción segura de la cola usando el helper
        raw_queue = extract_queue_items(sismolab.get_report_queue())
        queue_items = [
            r.to_dict() if hasattr(r, "to_dict") else r
            for r in raw_queue
        ]

        if queue_items:
            st.dataframe(queue_items, use_container_width=True, height=250)
            if st.button("▶️ Procesar Siguiente Reporte", type="primary", use_container_width=True):
                record_undo("QUEUE_STEP", "Procesamiento de un reporte de la cola FIFO")
                from src.services.queue_processing_service import QueueProcessingService
                res = QueueProcessingService.process_next_report(sismolab)
                if res.error:
                    st.error(res.error)
                else:
                    st.success(res.msg)
                    st.rerun()
        else:
            st.caption("No hay reportes pendientes en la cola.")

# =============================================================================
# PESTAÑA 2: CONTROL DEL ESCENARIO Y PARÁMETROS
# =============================================================================
with tab2:
    st.subheader("Ajuste de Parámetros Globales")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        w_val = st.number_input("Horas de Asociación (W)", value=float(getattr(scenario, "w_hours", 48.0)))
    with c2:
        r_val = st.number_input("Radio en km (R)", value=float(getattr(scenario, "r_km", 40.0)))
    with c3:
        l_val = st.number_input("Límite de Acceso Costoso (L)", value=int(getattr(scenario, "access_limit", 3)))
    with c4:
        t_val = st.number_input("Antigüedad de Archivo (T)", value=float(getattr(scenario, "archive_age_hours", 72.0)))

    if st.button("Guardar Parámetros"):
        record_undo("CHANGE_PARAMS", "Modificación de parámetros globales del escenario")
        scenario.w_hours = w_val
        scenario.r_km = r_val
        scenario.set_access_limit(l_val)
        scenario.archive_age_hours = t_val
        st.success("Parámetros actualizados correctamente.")
        st.rerun()

    st.divider()

    st.subheader("Operaciones Especiales")
    col_op1, col_op2, col_op3 = st.columns(3)

    with col_op1:
        if st.button("⏰ Avanzar Reloj (+1 hora)", use_container_width=True):
            record_undo("ADVANCE_CLOCK", "Avance del reloj de simulación")
            from datetime import timedelta
            scenario.set_simulation_clock(scenario.get_simulation_clock() + timedelta(hours=1))
            st.rerun()

    with col_op2:
        toggle_label = "Desactivar Modo Estrés" if is_stress else "Activar Modo Estrés"
        if st.button(toggle_label, use_container_width=True):
            record_undo("TOGGLE_STRESS", "Conmutación del Modo Estrés")
            scenario.set_stress_mode(not is_stress)
            st.rerun()

    with col_op3:
        if st.button("🔄 Recuperación Global (Rebalanceo)", use_container_width=True):
            record_undo("GLOBAL_RECOVERY", "Ejecución de recuperación global in-place")
            sismolab.rebalance_from_stress()
            st.success("Recuperación global ejecutada.")
            st.rerun()

# =============================================================================
# PESTAÑA 3: CONSULTAS ANALÍTICAS (PUNTO 11)
# =============================================================================
with tab3:
    st.subheader("Consultas de Desempeño sobre el Árbol AVL")

    query_type = st.selectbox(
        "Seleccione la consulta a ejecutar:",
        [
            "1. Top-k eventos pendientes (Orden descendente por K)",
            "2A. Eventos por intervalo inclusivo de magnitud",
            "2B. Eventos por profundidad e intervalo de fechas",
            "3. Asociaciones de un evento (Candidatos, Referencia e Histórico)",
            "4. Eventos de prioridad alta con acceso costoso (Profundidad > L)"
        ]
    )

    if query_type.startswith("1."):
        k_val = st.number_input("Cantidad de eventos (k):", min_value=1, value=5)
        if st.button("Ejecutar Consulta Top-k"):
            res = QueryService.get_top_k_pending(sismolab, k_val)
            st.metric("Nodos del AVL examinados 🎯", res.data.get("examined_nodes", 0))
            st.dataframe(res.data.get("events", []), use_container_width=True)

    elif query_type.startswith("2A."):
        cm1, cm2 = st.columns(2)
        with cm1: min_m = st.number_input("Magnitud mínima:", value=3.0)
        with cm2: max_m = st.number_input("Magnitud máxima:", value=7.0)
        if st.button("Buscar por Magnitud"):
            res = QueryService.get_events_by_magnitude_range(sismolab, min_m, max_m)
            st.metric("Nodos del AVL examinados 🎯", res.data.get("examined_nodes", 0))
            st.dataframe(res.data.get("events", []), use_container_width=True)

    elif query_type.startswith("2B."):
        cd1, cd2, cd3 = st.columns(3)
        with cd1: limit_h = st.number_input("Profundidad máxima (km):", value=50.0)
        with cd2: d_start = st.date_input("Fecha inicio:", value=datetime(2026, 1, 1))
        with cd3: d_end = st.date_input("Fecha fin:", value=datetime(2026, 12, 31))
        if st.button("Buscar por Profundidad y Fecha"):
            res = QueryService.get_events_by_depth_and_date_range(sismolab, limit_h, str(d_start), str(d_end))
            st.metric("Nodos del AVL examinados 🎯", res.data.get("examined_nodes", 0))
            st.dataframe(res.data.get("events", []), use_container_width=True)

    elif query_type.startswith("3."):
        target_id = st.number_input("ID del evento:", min_value=1, value=101)
        if st.button("Consultar Asociaciones"):
            res = QueryService.get_event_associations(sismolab, target_id)
            if res.error:
                st.error(res.error)
            else:
                st.metric("Nodos del AVL examinados 🎯", res.data.get("examined_nodes", 0))
                st.json(res.data)

    elif query_type.startswith("4."):
        if st.button("Buscar Eventos Costosos (P=3 y Profundidad > L)"):
            res = QueryService.get_high_priority_costly_access(sismolab)
            st.metric("Nodos del AVL examinados 🎯", res.data.get("examined_nodes", 0))
            st.dataframe(res.data.get("costly_high_priority_events", []), use_container_width=True)

# =============================================================================
# PESTAÑA 4: PERSISTENCIA Y VERSIONES (PUNTOS 12 Y 13)
# =============================================================================
with tab4:
    st.subheader("Carga y Exportación JSON del Escenario")

    col_load1, col_load2 = st.columns(2)

    with col_load1:
        st.markdown("### Carga por Inserciones")
        file_ins = st.file_uploader("Seleccione archivo JSON de eventos", type=["json"], key="u_ins")
        if file_ins and st.button("Procesar Carga por Inserción"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
                tmp.write(file_ins.getvalue())
                tmp_path = tmp.name

            record_undo("LOAD_INSERTIONS", "Carga por inserciones desde JSON")
            from src.structures.BSTTree import BSTTree
            res = PersistenceService.load_by_insertions(tmp_path, sismolab, BSTTree)

            if res.error:
                st.error(res.error)
            else:
                st.success(res.msg)
                st.json(res.data)
                st.rerun()

    with col_load2:
        st.markdown("### Carga por Topología (Atómica)")
        file_top = st.file_uploader("Seleccione archivo JSON de topología", type=["json"], key="u_top")
        if file_top and st.button("Procesar Carga por Topología"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
                tmp.write(file_top.getvalue())
                tmp_path = tmp.name

            record_undo("LOAD_TOPOLOGY", "Carga por topología desde JSON")
            res = PersistenceService.validate_and_load_topology(tmp_path, sismolab)

            if res.error:
                st.error(res.error)
                if "validation_errors" in res.data:
                    st.write(res.data["validation_errors"])
            else:
                st.success(res.msg)
                st.rerun()

    st.divider()

    st.subheader("Gestión de Versiones Nombradas Persistentes")
    cv1, cv2 = st.columns([1, 2])

    with cv1:
        v_name = st.text_input("Nombre de la versión:")
        v_desc = st.text_area("Descripción corta:")
        if st.button("💾 Guardar Versión"):
            res = version_srv.create_version(v_name, v_desc, sismolab)
            if not res.ok:
                st.error(res.error)
            else:
                st.success(f"Versión '{v_name}' creada exitosamente.")
                st.rerun()

    with cv2:
        v_list_res = version_srv.list_versions()
        versions = v_list_res.data or []

        if versions:
            st.dataframe(versions, use_container_width=True)
            sel_v = st.selectbox("Seleccionar versión guardada:", [v["name"] for v in versions])

            c_act1, c_act2 = st.columns(2)
            with c_act1:
                if st.button("🔄 Restaurar Versión Seleccionada"):
                    res = version_srv.restore_version(sel_v, sismolab)
                    if res.error:
                        st.error(res.error)
                    else:
                        st.success(res.msg)
                        st.rerun()

            with c_act2:
                if st.button("🗑️ Eliminar Versión Seleccionada"):
                    res = version_srv.delete_version(sel_v)
                    if not res.ok:
                        st.error(res.error)
                    else:
                        st.success(f"Versión '{sel_v}' eliminada.")
                        st.rerun()
        else:
            st.caption("No existen versiones guardadas en disco.")