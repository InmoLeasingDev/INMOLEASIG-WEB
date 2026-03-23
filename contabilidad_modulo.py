import streamlit as st
import pandas as pd

def mostrar_modulo_contabilidad(supabase):
    # 1. ¡Ícono corregido para que haga match con el menú lateral!
    st.header("🏦 Contabilidad y Finanzas")
    st.caption("Control de Facturación, Tesorería, Impuestos y Libros Contables.")

    # --- Identificar al usuario ---
    var_sesion = st.session_state.get("usuario_actual", st.session_state.get("usuario", "ADMINISTRADOR"))
    usuario_actual = var_sesion.get("nombre", "ADMINISTRADOR") if isinstance(var_sesion, dict) else str(var_sesion)

    # --- LAS 5 PESTAÑAS MAESTRAS DEL MÓDULO ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Dashboard", 
        "🧾 Facturación (CxC)", 
        "💸 Tesorería (CxP y Bancos)", 
        "📚 Libro Diario",
        "🏛️ Estados Financieros y Cierres"
    ])

    with tab1:
        st.subheader("Resumen Financiero")
        st.info("Aquí irán los gráficos de ingresos, gastos y cuentas por cobrar.")

    with tab2:
        st.subheader("Emisión de Documentos y Cuentas por Cobrar")
        st.info("Aquí emitiremos las facturas a inquilinos y registraremos sus deudas.")

    with tab3:
        st.subheader("Gestión de Bancos y Pagos a Proveedores/Propietarios")
        st.info("Aquí registraremos salidas de dinero, comisiones y haremos la conciliación.")

    with tab4:
        st.subheader("Libro Diario (Asientos Contables)")
        st.info("Aquí veremos los asientos automáticos del Debe y Haber en tiempo real.")

    # --- LA NUEVA PESTAÑA PARA EL CFO ---
    with tab5:
        st.subheader("Reportes Oficiales y Cierres de Periodo")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 📄 Estados Financieros")
            st.button("⚖️ Generar Balance General", disabled=True)
            st.button("📈 Generar Estado de Resultados (P&G)", disabled=True)
            
        with c2:
            st.markdown("#### 🔒 Cierres Contables")
            st.button("🔐 Ejecutar Cierre de Mes", disabled=True)
            st.button("📆 Ejecutar Cierre de Año", disabled=True)
            st.info("Un mes cerrado bloqueará cualquier modificación pasada para proteger la contabilidad.")