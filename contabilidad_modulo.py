import streamlit as st
import pandas as pd

def mostrar_modulo_contabilidad(supabase):
    st.header("💼 Contabilidad y Finanzas")
    st.caption("Control de Facturación, Tesorería, Impuestos y Libros Contables.")

    # --- Identificar al usuario ---
    var_sesion = st.session_state.get("usuario_actual", st.session_state.get("usuario", "ADMINISTRADOR"))
    usuario_actual = var_sesion.get("nombre", "ADMINISTRADOR") if isinstance(var_sesion, dict) else str(var_sesion)

    # --- LAS 4 PESTAÑAS MAESTRAS DEL MÓDULO ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard", 
        "🧾 Facturación (Cobros)", 
        "💸 Tesorería (Pagos y Bancos)", 
        "📚 Libro Diario (Asientos)"
    ])

    with tab1:
        st.subheader("Resumen Financiero")
        st.info("Aquí irán los gráficos de ingresos, gastos y cuentas por cobrar.")

    with tab2:
        st.subheader("Emisión de Documentos y Cuentas por Cobrar")
        st.info("Aquí emitiremos las facturas a inquilinos y registraremos sus pagos.")

    with tab3:
        st.subheader("Gestión de Bancos y Pagos a Propietarios")
        st.info("Aquí pagaremos las liquidaciones, registraremos gastos y haremos la conciliación.")

    with tab4:
        st.subheader("Contabilidad Estricta (NIIF)")
        st.info("Aquí veremos los asientos automáticos del Debe y Haber.")