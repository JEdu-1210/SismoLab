import json
import os
import tempfile
from datetime import datetime, time, timedelta, timezone

import altair as alt
import graphviz
import pandas as pd
import streamlit as st

from src.business.AccessService import AccessService
from src.business.ArchiveService import ArchiveService
from src.business.AssociationService import AssociationService
from src.business.EventService import EventService
from src.models.Report import Report
from src.models.Scenario import Scenario
from src.models.SismoLab import SismoLab
from src.models.Station import Station
from src.models.Zone import Zone
from src.services.QueryService import QueryService
from src.services.audit_service import AuditService
from src.services.persistencia import PersistenceService
from src.services.queue_processing_service import QueueProcessingService
from src.services.undo_service import UndoService
from src.services.version_service import VersionService


# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="SismoLab AVL",
    page_icon="🌋",
    layout="wide",
)


# =============================================================================
# SESSION AND SERVICE INITIALIZATION
# =============================================================================

if "sismolab" not in st.session_state:
    initial_clock = datetime.now(timezone.utc).replace(microsecond=0)
    st.session_state.sismolab = SismoLab(Scenario(initial_clock))

if "undo_srv" not in st.session_state:
    st.session_state.undo_srv = UndoService()

if "version_srv" not in st.session_state:
    st.session_state.version_srv = VersionService()

if "burst_draft" not in st.session_state:
    st.session_state.burst_draft = []

if "last_operation" not in st.session_state:
    st.session_state.last_operation = None

if "last_queue_result" not in st.session_state:
    st.session_state.last_queue_result = None

if "continuous_results" not in st.session_state:
    st.session_state.continuous_results = []

if "archive_preview" not in st.session_state:
    st.session_state.archive_preview = None

if "last_audit" not in st.session_state:
    st.session_state.last_audit = None


sismolab = st.session_state.sismolab
undo_srv = st.session_state.undo_srv
version_srv = st.session_state.version_srv

# Services keep a reference to the same SismoLab object. Persistence/Undo replace
# its internal operational state, not the SismoLab instance itself.
event_srv = EventService(sismolab)
association_srv = AssociationService(sismolab)
access_srv = AccessService(sismolab)
archive_srv = ArchiveService(sismolab)
query_srv = QueryService(sismolab)
queue_srv = QueueProcessingService(sismolab, undo_srv)


# =============================================================================
# HELPERS
# =============================================================================

def utc_datetime(date_value, time_value):
    """Build an aware UTC datetime from Streamlit date/time widgets."""
    return datetime.combine(date_value, time_value).replace(tzinfo=timezone.utc)


def remember_operation(name, message, data=None, ok=True):
    """Keep the last relevant operation visible after Streamlit reruns."""
    st.session_state.last_operation = {
        "operation": name,
        "ok": bool(ok),
        "message": str(message),
        "data": data,
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def show_service_result(result, operation_name, rerun_on_success=False):
    """Render a DataAndMsgReturn/BaseReturn and optionally rerun."""
    if not result.ok:
        message = result.error or "Operation failed"
        remember_operation(operation_name, message, getattr(result, "data", None), False)
        st.error(message)
        return False

    message = getattr(result, "msg", "") or "Operation completed successfully"
    data = getattr(result, "data", None)
    remember_operation(operation_name, message, data, True)
    st.success(message)

    if data:
        st.json(data)

    if rerun_on_success:
        st.rerun()

    return True


def event_row(event, node=None, tree=None):
    """Convert an Event to a GUI-friendly row."""
    row = event.to_dict()
    row["key"] = str(event.get_key())

    if node is not None and tree is not None:
        row["node_depth"] = tree.get_depth(node)
        row["node_height"] = node.get_height()
        row["balance_factor"] = tree.get_balance_factor(node)
        row["costly_access"] = node.is_costly_access()

    return row


def active_event_rows():
    tree = sismolab.get_avl_tree()
    return [
        event_row(node.get_event(), node, tree)
        for node in tree.inorder()
    ]


def historical_event_rows():
    return [event.to_dict() for event in sismolab.get_history().get_all_events()]


def tree_dot(root, tree_kind="AVL"):
    """Create a Graphviz representation with keys and links visible."""
    dot = graphviz.Digraph(comment=f"SismoLab {tree_kind}")
    dot.attr(rankdir="TB", nodesep="0.30", ranksep="0.45")
    dot.attr("node", shape="box", style="rounded,filled", fontname="Arial")

    def visit(node, depth=0):
        if node is None:
            return

        event = node.get_event()
        key = event.get_key()
        node_name = f"n{event.identifier}"

        fill_by_priority = {
            1: "#b8f2c8",
            2: "#ffe69a",
            3: "#ffb3b3",
        }

        costly = (
            tree_kind == "AVL"
            and hasattr(node, "is_costly_access")
            and node.is_costly_access()
        )

        extra = ""
        if tree_kind == "AVL":
            left_h = node.get_left().get_height() if node.get_left() else -1
            right_h = node.get_right().get_height() if node.get_right() else -1
            bf = left_h - right_h
            extra = f"\\nheight={node.get_height()} | BF={bf} | depth={depth}"
            if costly:
                extra += "\\nCOSTLY ACCESS"

        label = (
            f"SIS-{event.identifier:06d}"
            f"\\nK={key}"
            f"\\nM={event.magnitude} | H={event.depth}km"
            f"{extra}"
        )

        dot.node(
            node_name,
            label=label,
            fillcolor=fill_by_priority.get(event.priority, "white"),
            color="#b00020" if costly else "#333333",
            penwidth="3" if costly else "1",
        )

        left = node.get_left()
        right = node.get_right()

        if left is not None:
            left_name = f"n{left.get_event().identifier}"
            dot.edge(node_name, left_name, label="L")
            visit(left, depth + 1)

        if right is not None:
            right_name = f"n{right.get_event().identifier}"
            dot.edge(node_name, right_name, label="R")
            visit(right, depth + 1)

    visit(root)
    return dot


def render_geographic_plane():
    """Render the required fictitious 0..1000 km geographic plane."""
    scenario = sismolab.get_scenario()
    layers = []

    populated = [z.to_dict() for z in scenario.get_zones() if z.is_populated]
    non_populated = [z.to_dict() for z in scenario.get_zones() if not z.is_populated]

    def zone_layer(rows, color):
        if not rows:
            return None
        df = pd.DataFrame(rows)
        return (
            alt.Chart(df)
            .mark_rect(fill=color, opacity=0.15, stroke=color, strokeWidth=2)
            .encode(
                x=alt.X("x_min:Q", scale=alt.Scale(domain=[0, 1000]), title="X (km)"),
                x2="x_max:Q",
                y=alt.Y("y_min:Q", scale=alt.Scale(domain=[0, 1000]), title="Y (km)"),
                y2="y_max:Q",
                tooltip=["name:N", "x_min:Q", "x_max:Q", "y_min:Q", "y_max:Q"],
            )
        )

    pop_layer = zone_layer(populated, "#d62728")
    non_pop_layer = zone_layer(non_populated, "#2ca02c")
    if pop_layer is not None:
        layers.append(pop_layer)
    if non_pop_layer is not None:
        layers.append(non_pop_layer)

    stations = [station.to_dict() for station in scenario.get_stations()]
    if stations:
        station_df = pd.DataFrame(stations)
        layers.append(
            alt.Chart(station_df)
            .mark_point(shape="triangle-up", size=130, filled=True, color="#111111")
            .encode(
                x=alt.X("x:Q", scale=alt.Scale(domain=[0, 1000]), title="X (km)"),
                y=alt.Y("y:Q", scale=alt.Scale(domain=[0, 1000]), title="Y (km)"),
                tooltip=["name:N", "x:Q", "y:Q"],
            )
        )

    all_events = list(scenario.get_events_by_id().values())
    event_rows = []
    for event in all_events:
        event_rows.append(
            {
                "identifier": f"SIS-{event.identifier:06d}",
                "x": event.x,
                "y": event.y,
                "priority": str(event.priority),
                "magnitude": event.magnitude,
                "catalog": event.catalog_status.value,
                "attention": event.attention_status.value,
            }
        )

    if event_rows:
        event_df = pd.DataFrame(event_rows)

        active_df = event_df[event_df["catalog"] == "ACTIVE"]
        archived_df = event_df[event_df["catalog"] == "ARCHIVED"]
        deleted_df = event_df[event_df["catalog"] == "DELETED"]

        if not active_df.empty:
            layers.append(
                alt.Chart(active_df)
                .mark_circle(size=120, opacity=0.9)
                .encode(
                    x=alt.X("x:Q", scale=alt.Scale(domain=[0, 1000]), title="X (km)"),
                    y=alt.Y("y:Q", scale=alt.Scale(domain=[0, 1000]), title="Y (km)"),
                    color=alt.Color(
                        "priority:N",
                        title="Prioridad activa",
                        scale=alt.Scale(
                            domain=["1", "2", "3"],
                            range=["#2ca02c", "#f0ad00", "#d62728"],
                        ),
                    ),
                    tooltip=[
                        "identifier:N",
                        "priority:N",
                        "magnitude:Q",
                        "catalog:N",
                        "attention:N",
                        "x:Q",
                        "y:Q",
                    ],
                )
            )

        if not archived_df.empty:
            layers.append(
                alt.Chart(archived_df)
                .mark_point(shape="square", size=100, filled=True, color="#7f7f7f")
                .encode(
                    x=alt.X("x:Q", scale=alt.Scale(domain=[0, 1000])),
                    y=alt.Y("y:Q", scale=alt.Scale(domain=[0, 1000])),
                    tooltip=["identifier:N", "magnitude:Q", "catalog:N", "x:Q", "y:Q"],
                )
            )

        if not deleted_df.empty:
            layers.append(
                alt.Chart(deleted_df)
                .mark_point(shape="cross", size=120, color="#000000")
                .encode(
                    x=alt.X("x:Q", scale=alt.Scale(domain=[0, 1000])),
                    y=alt.Y("y:Q", scale=alt.Scale(domain=[0, 1000])),
                    tooltip=["identifier:N", "magnitude:Q", "catalog:N", "x:Q", "y:Q"],
                )
            )

    if not layers:
        st.info("No hay zonas, estaciones ni eventos para representar todavía.")
        return

    chart = alt.layer(*layers).properties(height=520).interactive()
    st.altair_chart(chart, use_container_width=True)
    st.caption(
        "Zonas rojas: pobladas · zonas verdes: no pobladas · triángulos: estaciones · "
        "círculos: activos · cuadrados: archivados · cruces: eliminados."
    )


def traversal_ids(items):
    return " → ".join(f"SIS-{item['identifier']:06d}" for item in items) or "(vacío)"


def temporary_json_file(uploaded_file):
    """Materialize a Streamlit uploaded JSON file only for the backend call."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    tmp.write(uploaded_file.getvalue())
    tmp.close()
    return tmp.name


# =============================================================================
# HEADER AND GLOBAL STATE
# =============================================================================

scenario = sismolab.get_scenario()
indicators_result = AuditService.get_indicators(sismolab)
indicators = indicators_result.data or {}
catalog_ind = indicators.get("catalog", {})
avl_ind = indicators.get("avl", {})

st.title("🌋 SismoLab AVL — Observatorio Sísmico")

h1, h2, h3, h4, h5, h6 = st.columns(6)
h1.metric("Modo", "ESTRÉS ⚠️" if scenario.is_stress_mode() else "NORMAL ✅")
h2.metric("Activos", catalog_ind.get("active_events", 0))
h3.metric("Históricos", catalog_ind.get("historical_events", 0))
h4.metric("Altura AVL", avl_ind.get("height", -1))
h5.metric("Cola FIFO", sismolab.get_report_queue().size())
h6.metric("Reloj", scenario.get_simulation_clock().strftime("%Y-%m-%d %H:%M"))

undo_col, op_col = st.columns([1, 4])
with undo_col:
    if st.button(
        "⏪ Deshacer",
        disabled=not undo_srv.can_undo(sismolab),
        use_container_width=True,
    ):
        result = undo_srv.undo(sismolab)
        if result.ok:
            remember_operation("Undo", result.msg, result.data, True)
            st.rerun()
        else:
            st.error(result.error)

with op_col:
    last_operation = st.session_state.last_operation
    if last_operation:
        status = "✅" if last_operation["ok"] else "❌"
        with st.expander(
            f"{status} Última operación: {last_operation['operation']} — {last_operation['message']}",
            expanded=False,
        ):
            st.write(last_operation["time"])
            if last_operation.get("data"):
                st.json(last_operation["data"])

st.divider()


# =============================================================================
# MAIN TABS
# =============================================================================

(
    tab_dashboard,
    tab_trees,
    tab_events,
    tab_queue,
    tab_scenario,
    tab_history_archive,
    tab_queries,
    tab_persistence,
    tab_audit,
) = st.tabs(
    [
        "📊 Indicadores",
        "🌳 AVL / BST",
        "🌋 Eventos",
        "📡 Reportes / Cola",
        "🗺️ Escenario",
        "📚 Histórico / Archivo",
        "🔍 Consultas",
        "💾 Persistencia / Undo",
        "✅ Auditoría",
    ]
)


# =============================================================================
# TAB 1: DASHBOARD / POINT 14 INDICATORS
# =============================================================================

with tab_dashboard:
    st.subheader("Indicadores exigidos por el punto 14")

    indicators = (AuditService.get_indicators(sismolab).data or {})
    catalog = indicators.get("catalog", {})
    avl_info = indicators.get("avl", {})
    bst_info = indicators.get("bst", {})
    event_info = indicators.get("events", {})
    metrics = indicators.get("metrics", {})

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Eventos activos", catalog.get("active_events", 0))
    c2.metric("Eventos históricos", catalog.get("historical_events", 0))
    c3.metric("Altura AVL", avl_info.get("height", -1))
    c4.metric("Hojas AVL", avl_info.get("leaf_count", 0))
    c5.metric("Altura BST", bst_info.get("height", -1))
    c6.metric("Hojas BST", bst_info.get("leaf_count", 0))

    st.markdown("#### Estado de eventos")
    e1, e2, e3, e4, e5 = st.columns(5)
    priorities = event_info.get("by_priority", {})
    e1.metric("Prioridad 1", priorities.get("1", 0))
    e2.metric("Prioridad 2", priorities.get("2", 0))
    e3.metric("Prioridad 3", priorities.get("3", 0))
    e4.metric("Pendientes", event_info.get("pending_attention", 0))
    e5.metric("Acceso costoso", event_info.get("costly_access", 0))

    st.markdown("#### Métricas acumuladas")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Correcciones", metrics.get("accepted_corrections", 0))
    m2.metric("Reportes descartados", metrics.get("discarded_reports", 0))
    m3.metric("Conflictos", metrics.get("conflicts", 0))
    m4.metric("Archivos masivos", metrics.get("mass_archives", 0))
    m5.metric("Eventos archivados", metrics.get("archived_events", 0))

    r1, r2, r3, r4, r5, r6 = st.columns(6)
    r1.metric("LL", metrics.get("ll_cases", 0))
    r2.metric("RR", metrics.get("rr_cases", 0))
    r3.metric("LR", metrics.get("lr_cases", 0))
    r4.metric("RL", metrics.get("rl_cases", 0))
    r5.metric("Giros izquierda", metrics.get("left_rotations", 0))
    r6.metric("Giros derecha", metrics.get("right_rotations", 0))

    st.markdown("#### Recorridos AVL")
    st.write("**Inorden:**", traversal_ids(avl_info.get("inorder", [])))
    st.write("**Preorden:**", traversal_ids(avl_info.get("preorder", [])))
    st.write("**Postorden:**", traversal_ids(avl_info.get("postorder", [])))
    st.write("**Por niveles:**", traversal_ids(avl_info.get("breadth_first", [])))

    st.markdown("#### Catálogo activo")
    rows = active_event_rows()
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No hay eventos activos.")


# =============================================================================
# TAB 2: AVL / BST GRAPHICAL COMPARISON
# =============================================================================

with tab_trees:
    st.subheader("Vista gráfica comparativa AVL / BST")
    st.caption("Cada nodo muestra su clave K=(P, M, I). Los enlaces L/R representan hijo izquierdo/derecho.")

    left_col, right_col = st.columns(2)

    with left_col:
        st.markdown("### AVL activo")
        avl_root = sismolab.get_avl_tree().get_root()
        if avl_root is None:
            st.info("AVL vacío.")
        else:
            st.graphviz_chart(tree_dot(avl_root, "AVL"), use_container_width=True)

    with right_col:
        st.markdown("### BST comparativo")
        bst_root = sismolab.get_bst_tree().get_root()
        if bst_root is None:
            st.info("BST vacío.")
        else:
            st.graphviz_chart(tree_dot(bst_root, "BST"), use_container_width=True)

    st.divider()
    if st.button("Comparar estructura actual AVL vs BST", use_container_width=True):
        result = query_srv.compare_current_avl_bst()
        if result.ok:
            remember_operation("Comparación AVL/BST", result.msg, result.data, True)
            st.json(result.data)
        else:
            st.error(result.error)

    if st.button("Comparar distintos órdenes de inserción", use_container_width=True):
        result = query_srv.compare_insertion_orders()
        if result.ok:
            remember_operation("Comparación de órdenes", result.msg, result.data, True)
            data = result.data or {}
            order_rows = []
            for name, details in data.get("orders", {}).items():
                order_rows.append(
                    {
                        "order": name,
                        "insertion_ids": details.get("insertion_ids"),
                        "avl_height": details.get("avl", {}).get("height"),
                        "avl_leaves": details.get("avl", {}).get("leaf_count"),
                        "avl_search_comparisons": details.get("avl", {}).get("search_comparisons"),
                        "bst_height": details.get("bst", {}).get("height"),
                        "bst_leaves": details.get("bst", {}).get("leaf_count"),
                        "bst_search_comparisons": details.get("bst", {}).get("search_comparisons"),
                    }
                )
            st.dataframe(order_rows, use_container_width=True, hide_index=True)
            with st.expander("Detalle completo"):
                st.json(data)
        else:
            st.error(result.error)


# =============================================================================
# TAB 3: EVENT MANAGEMENT
# =============================================================================

with tab_events:
    st.subheader("Gestión de eventos")
    create_tab, inspect_tab, correct_tab, state_tab = st.tabs(
        ["Alta manual", "Consultar", "Corregir", "Atención / Eliminar"]
    )

    stations = scenario.get_stations()
    station_names = [station.name for station in stations]
    clock = scenario.get_simulation_clock()

    with create_tab:
        if not station_names:
            st.warning("Debe registrar al menos una estación en la pestaña Escenario antes de crear eventos.")
        else:
            with st.form("create_event_form"):
                a1, a2, a3 = st.columns(3)
                identifier = a1.number_input("Identificador", min_value=1, step=1, value=1)
                magnitude = a2.number_input("Magnitud", min_value=0.0, value=4.5, step=0.1)
                depth = a3.number_input("Profundidad hipocentro (km)", min_value=0.0, value=30.0, step=1.0)

                b1, b2, b3 = st.columns(3)
                x = b1.number_input("X (km)", min_value=0.0, max_value=1000.0, value=100.0)
                y = b2.number_input("Y (km)", min_value=0.0, max_value=1000.0, value=100.0)
                station_name = b3.selectbox("Estación", station_names)

                d1, d2 = st.columns(2)
                event_date = d1.date_input("Fecha", value=clock.date(), key="create_date")
                event_time = d2.time_input(
                    "Hora UTC",
                    value=clock.timetz().replace(tzinfo=None),
                    key="create_time",
                )

                submitted = st.form_submit_button("Crear evento", type="primary")

            if submitted:
                success, message, event = event_srv.create_manual_event(
                    identifier,
                    magnitude,
                    depth,
                    x,
                    y,
                    utc_datetime(event_date, event_time),
                    station_name,
                )
                if success:
                    remember_operation("Alta manual", message, event.to_dict(), True)
                    st.success(message)
                    st.rerun()
                else:
                    remember_operation("Alta manual", message, None, False)
                    st.error(message)

    with inspect_tab:
        inspect_id = st.number_input("ID a consultar", min_value=1, step=1, value=1, key="inspect_id")
        if st.button("Consultar evento", key="inspect_button"):
            success, message, details = event_srv.get_event_details(inspect_id)
            if success:
                st.success(message)
                st.json(details)
            else:
                st.error(message)

    with correct_tab:
        correction_id = st.number_input("ID activo a corregir", min_value=1, step=1, value=1, key="corr_id")
        st.caption("Marque solamente los campos que realmente desea cambiar. La revisión aumenta automáticamente.")

        c1, c2, c3 = st.columns(3)
        change_m = c1.checkbox("Cambiar magnitud")
        change_h = c2.checkbox("Cambiar profundidad")
        change_xy = c3.checkbox("Cambiar epicentro")

        v1, v2 = st.columns(2)
        new_m = v1.number_input("Nueva magnitud", min_value=0.0, value=6.2, step=0.1, disabled=not change_m)
        new_h = v2.number_input("Nueva profundidad", min_value=0.0, value=15.0, step=1.0, disabled=not change_h)

        p1, p2 = st.columns(2)
        new_x = p1.number_input("Nuevo X", min_value=0.0, max_value=1000.0, value=100.0, disabled=not change_xy)
        new_y = p2.number_input("Nuevo Y", min_value=0.0, max_value=1000.0, value=100.0, disabled=not change_xy)

        change_dt = st.checkbox("Cambiar fecha/hora")
        dt1, dt2 = st.columns(2)
        new_date = dt1.date_input("Nueva fecha", value=clock.date(), disabled=not change_dt, key="corr_date")
        new_time = dt2.time_input(
            "Nueva hora UTC",
            value=clock.timetz().replace(tzinfo=None),
            disabled=not change_dt,
            key="corr_time",
        )

        if st.button("Aplicar corrección", type="primary"):
            success, message, event = event_srv.correct_manual_event(
                correction_id,
                magnitude=new_m if change_m else None,
                depth=new_h if change_h else None,
                x=new_x if change_xy else None,
                y=new_y if change_xy else None,
                date_time=utc_datetime(new_date, new_time) if change_dt else None,
            )
            if success:
                remember_operation("Corrección manual", message, event.to_dict(), True)
                st.success(message)
                st.rerun()
            else:
                remember_operation("Corrección manual", message, None, False)
                st.error(message)

    with state_tab:
        action_id = st.number_input("ID del evento", min_value=1, step=1, value=1, key="state_id")
        a1, a2 = st.columns(2)

        with a1:
            if st.button("✅ Marcar como revisado", use_container_width=True):
                success, message, event = event_srv.mark_event_as_reviewed(action_id)
                if success:
                    remember_operation("Cambio de atención", message, event.to_dict(), True)
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

        with a2:
            if st.button("🗑️ Eliminar evento", use_container_width=True):
                success, message, event = event_srv.delete_event(action_id)
                if success:
                    remember_operation("Eliminación individual", message, event.to_dict(), True)
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)


# =============================================================================
# TAB 4: REPORT BURSTS, FIFO, STEP/CONTINUOUS PROCESSING, STRESS
# =============================================================================

with tab_queue:
    st.subheader("Ráfagas de reportes y cola FIFO")

    burst_tab, process_tab, stress_tab = st.tabs(
        ["Preparar ráfaga", "Procesar cola", "Modo estrés / Recuperación"]
    )

    with burst_tab:
        stations = scenario.get_stations()
        station_names = [station.name for station in stations]

        if not station_names:
            st.warning("Debe registrar estaciones antes de preparar reportes.")
        else:
            clock = scenario.get_simulation_clock()
            with st.form("report_draft_form"):
                q1, q2, q3 = st.columns(3)
                report_id = q1.number_input("Event ID", min_value=1, step=1, value=1, key="report_id")
                revision = q2.number_input("Revisión", min_value=0, step=1, value=1)
                report_station = q3.selectbox("Estación emisora", station_names, key="report_station")

                q4, q5, q6, q7 = st.columns(4)
                report_mag = q4.number_input("Magnitud", min_value=0.0, value=4.5, step=0.1, key="report_mag")
                report_depth = q5.number_input("Profundidad km", min_value=0.0, value=30.0, key="report_depth")
                report_x = q6.number_input("X", min_value=0.0, max_value=1000.0, value=100.0, key="report_x")
                report_y = q7.number_input("Y", min_value=0.0, max_value=1000.0, value=100.0, key="report_y")

                q8, q9 = st.columns(2)
                report_date = q8.date_input("Fecha ocurrencia", value=clock.date(), key="report_date")
                report_time = q9.time_input(
                    "Hora UTC",
                    value=clock.timetz().replace(tzinfo=None),
                    key="report_time",
                )

                add_report = st.form_submit_button("Agregar reporte al borrador")

            if add_report:
                station = scenario.get_station_by_name(report_station)
                try:
                    report = Report(
                        report_id,
                        revision,
                        station,
                        report_mag,
                        report_depth,
                        report_x,
                        report_y,
                        utc_datetime(report_date, report_time),
                    )
                    st.session_state.burst_draft.append(report)
                    st.success("Reporte agregado al borrador de la ráfaga.")
                except Exception as exc:
                    st.error(str(exc))

        draft = st.session_state.burst_draft
        st.markdown("#### Borrador de ráfaga")
        if draft:
            st.dataframe([r.to_dict() for r in draft], use_container_width=True, hide_index=True)
            b1, b2 = st.columns(2)
            if b1.button("📥 Enviar ráfaga a la cola", type="primary", use_container_width=True):
                result = queue_srv.enqueue_burst(draft)
                if result.ok:
                    st.session_state.burst_draft = []
                    remember_operation("Encolar ráfaga", result.msg, result.data, True)
                    st.rerun()
                else:
                    st.error(result.error)
            if b2.button("Vaciar borrador", use_container_width=True):
                st.session_state.burst_draft = []
                st.rerun()
        else:
            st.info("El borrador está vacío.")

    with process_tab:
        queue_view = queue_srv.get_queue_view()
        st.markdown("#### Orden FIFO visible")
        if queue_view:
            st.dataframe(queue_view, use_container_width=True, hide_index=True)
        else:
            st.info("No hay reportes pendientes.")

        p1, p2, p3 = st.columns([1, 1, 1])

        if p1.button("▶️ Procesar un reporte", type="primary", use_container_width=True):
            result = queue_srv.process_next_report()
            if result.ok:
                st.session_state.last_queue_result = result.data
                remember_operation("Paso de cola", result.msg, result.data, True)
                st.rerun()
            else:
                st.error(result.error)

        pause_seconds = p2.number_input("Pausa entre pasos (s)", min_value=0.0, value=0.5, step=0.1)
        max_steps_ui = p3.number_input("Máximo de pasos (0 = todos)", min_value=0, value=0, step=1)

        if st.button("⏩ Procesamiento continuo", use_container_width=True):
            result = queue_srv.process_continuous(
                pause_seconds=pause_seconds,
                max_steps=None if max_steps_ui == 0 else int(max_steps_ui),
            )
            if result.ok:
                data = result.data or {}
                st.session_state.continuous_results = data.get("steps", [])
                remember_operation("Procesamiento continuo", result.msg, data, True)
                st.rerun()
            else:
                st.error(result.error)

        if st.session_state.last_queue_result:
            st.markdown("#### Último reporte procesado")
            last = st.session_state.last_queue_result
            d1, d2, d3, d4 = st.columns(4)
            d1.metric("Estación", last.get("station"))
            d2.metric("Evento", last.get("event_id"))
            d3.metric("Revisión", last.get("revision"))
            d4.metric("Decisión", last.get("decision"))
            st.write("**Mensaje:**", last.get("message"))
            st.write("**Rotaciones producidas:**")
            rotations = last.get("rotations", [])
            if rotations:
                st.dataframe(rotations, use_container_width=True, hide_index=True)
            else:
                st.caption("Este paso no produjo rotaciones.")

        if st.session_state.continuous_results:
            with st.expander("Resultados del último procesamiento continuo"):
                for index, step in enumerate(st.session_state.continuous_results, start=1):
                    st.markdown(f"**Paso {index}**")
                    st.json(step)

    with stress_tab:
        current_stress = scenario.is_stress_mode()
        if current_stress:
            st.warning("Modo ESTRÉS activo: las rotaciones del AVL están aplazadas.")
            if st.button("🔄 Ejecutar recuperación global", type="primary", use_container_width=True):
                result = queue_srv.recover_avl_balance()
                if result.ok:
                    remember_operation("Recuperación global", result.msg, result.data, True)
                    st.rerun()
                else:
                    remember_operation("Recuperación global", result.error, result.data, False)
                    st.error(result.error)
                    if result.data:
                        st.json(result.data)
        else:
            st.success("Modo NORMAL activo: el AVL debe permanecer balanceado.")
            if st.button("⚠️ Activar modo estrés", use_container_width=True):
                result = queue_srv.enter_stress_mode()
                if result.ok:
                    remember_operation("Activar estrés", result.msg, result.data, True)
                    st.rerun()
                else:
                    st.error(result.error)


# =============================================================================
# TAB 5: SCENARIO, STATIONS, ZONES, PARAMETERS, CLOCK, GEOGRAPHIC PLOT
# =============================================================================

with tab_scenario:
    st.subheader("Escenario y plano geográfico")
    setup_tab, params_tab, map_tab = st.tabs(["Estaciones / Zonas", "Parámetros / Reloj", "Plano 0–1000 km"])

    geometry_locked = len(scenario.get_events_by_id()) > 0

    with setup_tab:
        if geometry_locked:
            st.info("La geometría está bloqueada porque el escenario ya contiene identidades de eventos.")

        left, right = st.columns(2)

        with left:
            st.markdown("#### Estaciones")
            station_rows = [station.to_dict() for station in scenario.get_stations()]
            if station_rows:
                st.dataframe(station_rows, use_container_width=True, hide_index=True)
            else:
                st.caption("No hay estaciones registradas.")

            with st.form("station_form"):
                station_name = st.text_input("Nombre de estación")
                sx = st.number_input("X estación", min_value=0.0, max_value=1000.0, value=50.0)
                sy = st.number_input("Y estación", min_value=0.0, max_value=1000.0, value=50.0)
                add_station = st.form_submit_button("Agregar estación", disabled=geometry_locked)

            if add_station:
                try:
                    station = Station(station_name, sx, sy)
                    if scenario.add_station(station):
                        remember_operation("Agregar estación", f"Estación '{station.name}' agregada", station.to_dict(), True)
                        st.rerun()
                    else:
                        st.error("La estación no pudo agregarse (posible nombre duplicado).")
                except Exception as exc:
                    st.error(str(exc))

        with right:
            st.markdown("#### Zonas")
            zone_rows = [zone.to_dict() for zone in scenario.get_zones()]
            if zone_rows:
                st.dataframe(zone_rows, use_container_width=True, hide_index=True)
            else:
                st.caption("No hay zonas registradas.")

            with st.form("zone_form"):
                zone_name = st.text_input("Nombre de zona")
                z1, z2 = st.columns(2)
                x_min = z1.number_input("x_min", min_value=0.0, max_value=1000.0, value=0.0)
                x_max = z2.number_input("x_max", min_value=0.0, max_value=1000.0, value=200.0)
                z3, z4 = st.columns(2)
                y_min = z3.number_input("y_min", min_value=0.0, max_value=1000.0, value=0.0)
                y_max = z4.number_input("y_max", min_value=0.0, max_value=1000.0, value=200.0)
                populated = st.checkbox("Zona poblada", value=True)
                add_zone = st.form_submit_button("Agregar zona", disabled=geometry_locked)

            if add_zone:
                try:
                    zone = Zone(zone_name, x_min, x_max, y_min, y_max, populated)
                    if scenario.add_zone(zone):
                        remember_operation("Agregar zona", f"Zona '{zone.name}' agregada", zone.to_dict(), True)
                        st.rerun()
                    else:
                        st.error("La zona no pudo agregarse: revise nombre y superposición interior.")
                except Exception as exc:
                    st.error(str(exc))

    with params_tab:
        st.markdown("#### W y R — asociaciones")
        w1, w2 = st.columns(2)
        w_value = w1.number_input("W (horas)", min_value=0.01, value=float(scenario.get_w_hours()))
        r_value = w2.number_input("R (km)", min_value=0.01, value=float(scenario.get_r_km()))
        if st.button("Actualizar W / R"):
            result = undo_srv.update_association_limits(
                sismolab,
                association_srv,
                w_hours=w_value,
                r_km=r_value,
            )
            if show_service_result(result, "Cambio W/R"):
                st.rerun()

        st.markdown("#### L — acceso costoso")
        l_value = st.number_input("L", min_value=0, value=int(scenario.get_access_limit()), step=1)
        if st.button("Actualizar L"):
            result = undo_srv.update_access_limit(sismolab, access_srv, int(l_value))
            if show_service_result(result, "Cambio L"):
                st.rerun()

        st.markdown("#### T — antigüedad de archivo")
        t_value = st.number_input("T (horas)", min_value=0.01, value=float(scenario.get_archive_age_hours()))
        if st.button("Actualizar T"):
            result = undo_srv.update_archive_age(sismolab, t_value)
            if show_service_result(result, "Cambio T"):
                st.rerun()

        st.markdown("#### Reloj de simulación")
        current_clock = scenario.get_simulation_clock()
        cl1, cl2 = st.columns(2)
        clock_date = cl1.date_input("Nueva fecha", value=current_clock.date(), key="clock_date")
        clock_time = cl2.time_input(
            "Nueva hora UTC",
            value=(current_clock + timedelta(hours=1)).timetz().replace(tzinfo=None),
            key="clock_time",
        )
        if st.button("Avanzar reloj"):
            result = undo_srv.advance_simulation_clock(
                sismolab,
                utc_datetime(clock_date, clock_time),
            )
            if show_service_result(result, "Avance del reloj"):
                st.rerun()

    with map_tab:
        render_geographic_plane()


# =============================================================================
# TAB 6: HISTORY AND MASS ARCHIVE
# =============================================================================

with tab_history_archive:
    st.subheader("Histórico y archivo masivo")
    hist_col, archive_col = st.columns([1.4, 1])

    with hist_col:
        st.markdown("### Eventos históricos")
        history_rows = historical_event_rows()
        if history_rows:
            st.dataframe(history_rows, use_container_width=True, hide_index=True)
        else:
            st.info("El histórico está vacío.")

        roots = sismolab.get_history().get_archived_roots()
        if roots:
            st.write("Raíces de subárboles archivados:", [root.get_event().identifier for root in roots])

    with archive_col:
        st.markdown("### Archivar rama de eventos antiguos")
        if st.button("1️⃣ Buscar mejor rama elegible", use_container_width=True):
            success, message, details = archive_srv.get_archive_preview()
            if success:
                st.session_state.archive_preview = details
                st.success(message)
            else:
                st.session_state.archive_preview = None
                st.warning(message)

        preview = st.session_state.archive_preview
        if preview:
            st.json(preview)
            if st.button("2️⃣ Confirmar archivo masivo", type="primary", use_container_width=True):
                success, message, result_data = archive_srv.archive_old_events_branch()
                if success:
                    st.session_state.archive_preview = None
                    remember_operation("Archivo masivo", message, result_data, True)
                    st.rerun()
                else:
                    remember_operation("Archivo masivo", message, result_data, False)
                    st.error(message)


# =============================================================================
# TAB 7: POINT 11 QUERIES
# =============================================================================

with tab_queries:
    st.subheader("Consultas analíticas del punto 11")

    query_name = st.selectbox(
        "Consulta",
        [
            "Top-k pendientes por K descendente",
            "Rango inclusivo de magnitud",
            "Profundidad + intervalo de fechas",
            "Asociaciones de un evento",
            "Prioridad alta con acceso costoso",
            "Comparar AVL/BST actuales",
            "Comparar órdenes de inserción",
        ],
    )

    if query_name == "Top-k pendientes por K descendente":
        k = st.number_input("k", min_value=1, value=5, step=1)
        if st.button("Ejecutar top-k"):
            result = query_srv.get_top_k_pending(int(k))
            if result.ok:
                st.metric("Nodos AVL examinados", result.data.get("examined_nodes", 0))
                st.dataframe(result.data.get("events", []), use_container_width=True, hide_index=True)
                st.json(result.data.get("cost_analysis", {}))
            else:
                st.error(result.error)

    elif query_name == "Rango inclusivo de magnitud":
        q1, q2 = st.columns(2)
        min_m = q1.number_input("Magnitud mínima", value=3.0)
        max_m = q2.number_input("Magnitud máxima", value=7.0)
        if st.button("Buscar por magnitud"):
            result = query_srv.get_events_by_magnitude_range(min_m, max_m)
            if result.ok:
                st.metric("Nodos AVL examinados", result.data.get("examined_nodes", 0))
                st.dataframe(result.data.get("events", []), use_container_width=True, hide_index=True)
                st.json(result.data.get("cost_analysis", {}))
            else:
                st.error(result.error)

    elif query_name == "Profundidad + intervalo de fechas":
        q1, q2, q3 = st.columns(3)
        max_depth = q1.number_input("Profundidad máxima (km)", min_value=0.0, value=50.0)
        start_date = q2.date_input("Fecha inicial", value=scenario.get_simulation_clock().date() - timedelta(days=30))
        end_date = q3.date_input("Fecha final", value=scenario.get_simulation_clock().date())
        if st.button("Buscar por profundidad y fecha"):
            start_dt = datetime.combine(start_date, time.min).replace(tzinfo=timezone.utc)
            end_dt = datetime.combine(end_date, time.max).replace(tzinfo=timezone.utc)
            result = query_srv.get_events_by_depth_and_date_range(max_depth, start_dt, end_dt)
            if result.ok:
                st.metric("Nodos AVL examinados", result.data.get("examined_nodes", 0))
                st.dataframe(result.data.get("events", []), use_container_width=True, hide_index=True)
                st.json(result.data.get("cost_analysis", {}))
            else:
                st.error(result.error)

    elif query_name == "Asociaciones de un evento":
        event_id = st.number_input("Event ID", min_value=1, step=1, value=1, key="assoc_query_id")
        if st.button("Consultar asociaciones"):
            result = query_srv.get_event_associations(int(event_id))
            if result.ok:
                st.metric("Nodos AVL examinados", result.data.get("examined_nodes", 0))
                st.json(result.data)
            else:
                st.error(result.error)

    elif query_name == "Prioridad alta con acceso costoso":
        if st.button("Buscar accesos costosos"):
            result = query_srv.get_high_priority_costly_access()
            if result.ok:
                st.metric("Nodos AVL examinados", result.data.get("examined_nodes", 0))
                st.dataframe(result.data.get("events", []), use_container_width=True, hide_index=True)
                st.json(result.data.get("cost_analysis", {}))
            else:
                st.error(result.error)

    elif query_name == "Comparar AVL/BST actuales":
        ids_text = st.text_input("IDs opcionales separados por coma (vacío = todos)")
        if st.button("Comparar AVL y BST"):
            identifiers = None
            if ids_text.strip():
                try:
                    identifiers = [int(part.strip()) for part in ids_text.split(",") if part.strip()]
                except ValueError:
                    st.error("Los IDs deben ser enteros separados por coma.")
                    identifiers = []
            if identifiers != []:
                result = query_srv.compare_current_avl_bst(identifiers)
                if result.ok:
                    st.json(result.data)
                else:
                    st.error(result.error)

    else:
        if st.button("Comparar órdenes de inserción"):
            result = query_srv.compare_insertion_orders()
            if result.ok:
                st.json(result.data)
            else:
                st.error(result.error)


# =============================================================================
# TAB 8: PERSISTENCE, VERSIONS AND UNDO HISTORY
# =============================================================================

with tab_persistence:
    st.subheader("Persistencia, versiones y deshacer")
    load_tab, export_tab, versions_tab, undo_tab = st.tabs(
        ["Cargar JSON", "Exportar JSON", "Versiones", "Historial Undo"]
    )

    with load_tab:
        l1, l2 = st.columns(2)

        with l1:
            st.markdown("### Carga por inserciones")
            insertion_file = st.file_uploader("JSON de eventos", type=["json"], key="insertions_json")
            if insertion_file and st.button("Cargar por inserciones"):
                path = temporary_json_file(insertion_file)
                try:
                    result = undo_srv.load_by_insertions(path, sismolab)
                    if result.ok:
                        remember_operation("Carga por inserciones", result.msg, result.data, True)
                        st.success(result.msg)
                        st.json(result.data)
                        st.rerun()
                    else:
                        st.error(result.error)
                finally:
                    if os.path.exists(path):
                        os.unlink(path)

        with l2:
            st.markdown("### Carga por topología")
            topology_file = st.file_uploader("JSON estructural", type=["json"], key="topology_json")
            if topology_file and st.button("Cargar por topología"):
                path = temporary_json_file(topology_file)
                try:
                    result = undo_srv.load_by_topology(path, sismolab)
                    if result.ok:
                        remember_operation("Carga por topología", result.msg, result.data, True)
                        st.success(result.msg)
                        st.rerun()
                    else:
                        st.error(result.error)
                finally:
                    if os.path.exists(path):
                        os.unlink(path)

    with export_tab:
        payload = {
            "schema": PersistenceService.SCHEMA_NAME,
            "schema_version": PersistenceService.SCHEMA_VERSION,
            "state": PersistenceService.export_state(sismolab),
        }
        json_text = json.dumps(payload, indent=2, ensure_ascii=False)
        st.download_button(
            "⬇️ Descargar estado estructural JSON",
            data=json_text,
            file_name="sismolab_state.json",
            mime="application/json",
            use_container_width=True,
        )
        with st.expander("Vista previa del JSON"):
            st.json(payload)

    with versions_tab:
        v1, v2 = st.columns([1, 1.5])
        with v1:
            version_name = st.text_input("Nombre de la versión")
            version_description = st.text_area("Descripción")
            if st.button("💾 Guardar versión", use_container_width=True):
                result = version_srv.create_version(version_name, version_description, sismolab)
                if result.ok:
                    remember_operation("Guardar versión", result.msg, result.data, True)
                    st.rerun()
                else:
                    st.error(result.error)

        with v2:
            versions_result = version_srv.list_versions()
            versions = (versions_result.data or {}).get("versions", []) if versions_result.ok else []
            if versions:
                st.dataframe(versions, use_container_width=True, hide_index=True)
                selected_version = st.selectbox("Versión", [item["name"] for item in versions])
                v21, v22 = st.columns(2)
                if v21.button("🔄 Restaurar", use_container_width=True):
                    result = version_srv.restore_version(selected_version, sismolab)
                    if result.ok:
                        remember_operation("Restaurar versión", result.msg, result.data, True)
                        st.rerun()
                    else:
                        st.error(result.error)
                if v22.button("🗑️ Eliminar", use_container_width=True):
                    result = version_srv.delete_version(selected_version)
                    if result.ok:
                        remember_operation("Eliminar versión", f"Version '{selected_version}' deleted", None, True)
                        st.rerun()
                    else:
                        st.error(result.error)
            else:
                st.info("No hay versiones persistentes guardadas.")

    with undo_tab:
        history_result = undo_srv.get_undo_history(sismolab)
        history_data = history_result.data or {}
        actions = history_data.get("actions", [])
        st.metric("Acciones disponibles para deshacer", history_data.get("count", 0))
        if actions:
            st.dataframe(actions, use_container_width=True, hide_index=True)
            st.caption("metric_effects explica qué contadores cambió cada acción.")
        else:
            st.info("La pila de retroceso está vacía.")


# =============================================================================
# TAB 9: FULL AUDIT
# =============================================================================

with tab_audit:
    st.subheader("Verificar estructura")
    st.caption("Disponible tanto en modo normal como en modo estrés.")

    if st.button("✅ Ejecutar auditoría completa", type="primary", use_container_width=True):
        result = AuditService.verify_structure(sismolab)
        st.session_state.last_audit = result.to_dict()
        remember_operation("Auditoría", result.msg, result.data, result.ok)

    audit_snapshot = st.session_state.last_audit
    if audit_snapshot:
        if audit_snapshot.get("ok"):
            data = audit_snapshot.get("data", {}) or {}
            if data.get("is_valid"):
                st.success("La estructura es válida para el modo actual.")
            else:
                st.error("La auditoría detectó inconsistencias críticas.")

            a1, a2, a3, a4 = st.columns(4)
            a1.metric("Activos examinados", data.get("active_events_examined", 0))
            a2.metric("Históricos examinados", data.get("archived_events_examined", 0))
            a3.metric("Inconsistencias críticas", data.get("critical_inconsistencies", 0))
            a4.metric("Desbalances esperados", data.get("expected_unbalances", 0))

            event_reports = data.get("event_reports", [])
            global_issues = data.get("global_issues", [])
            all_issues = data.get("issues", [])

            if event_reports:
                st.markdown("#### Reporte por evento inconsistente")
                st.json(event_reports)

            if global_issues:
                st.markdown("#### Problemas globales")
                st.dataframe(global_issues, use_container_width=True, hide_index=True)

            if all_issues:
                with st.expander("Todas las observaciones"):
                    st.dataframe(all_issues, use_container_width=True, hide_index=True)
            elif data.get("is_valid"):
                st.info("No se detectaron errores estructurales.")

            with st.expander("Resultado completo de auditoría"):
                st.json(data)
        else:
            st.error(audit_snapshot.get("error") or "Audit failed")
    else:
        st.info("Ejecute la auditoría para generar el reporte.")
