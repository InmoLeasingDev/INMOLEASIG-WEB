import streamlit as st
import pandas as pd
# --- NUESTRA LIBRERÍA MAESTRA ---
from herramientas import log_accion

# ==========================================
# MÓDULO PRINCIPAL: INMUEBLES
# ==========================================
def mostrar_modulo_inmuebles(supabase):
    st.header("🏢 Gestión de Inmuebles e Inventarios")
    MOD_VERSION = "v1.0 (Esqueleto)"
    st.caption(f"⚙️ Módulo Inmuebles {MOD_VERSION} | Control de Propiedades, Unidades, Mandatos e Inventarios.")

    # --- Identificar al usuario para los logs ---
    var_sesion = st.session_state.get("usuario_actual", st.session_state.get("usuario", "ADMINISTRADOR"))
    usuario_actual = var_sesion.get("nombre", "ADMINISTRADOR") if isinstance(var_sesion, dict) else str(var_sesion)

    # --- CREACIÓN DE LAS 4 PESTAÑAS MAESTRAS ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏢 1. Propiedades", 
        "🚪 2. Unidades", 
        "🤝 3. Mandatos", 
        "🛋️ 4. Inventarios"
    ])

    # ==========================================
    # TAB 1: PROPIEDADES (El Cascarón)
    # ==========================================
    with tab1:
        st.subheader("Catálogo de Propiedades Base")
        st.info("💡 Aquí daremos de alta el edificio o casa principal (Ej: Edificio Los Alpes, Casa Calle 5).")
        
        # Prueba de lectura de la tabla que creamos en SQL
        try:
            res_inm = supabase.table("inmuebles").select("*").execute()
            df_inm = pd.DataFrame(res_inm.data) if res_inm.data else pd.DataFrame()
            
            if not df_inm.empty:
                st.dataframe(df_inm, use_container_width=True)
            else:
                st.write("Aún no hay propiedades registradas en la base de datos.")
        except Exception as e:
            st.error(f"Error de conexión con la tabla inmuebles: {e}")

        st.button("➕ Simular Botón: Nueva Propiedad", disabled=True)

    # ==========================================
    # TAB 2: UNIDADES (Las Divisiones)
    # ==========================================
    with tab2:
        st.subheader("Gestión de Unidades Rentables")
        st.info("💡 Aquí dividiremos la propiedad seleccionada en Apartamentos, Locales o Habitaciones para poder alquilarlas.")
        st.button("➕ Simular Botón: Añadir Unidad", disabled=True)

    # ==========================================
    # TAB 3: MANDATOS (Dueños y Porcentajes)
    # ==========================================
    with tab3:
        st.subheader("Distribución de Propiedad (Relación N:M)")
        st.info("💡 Aquí usaremos la tabla puente 'inmuebles_propietarios' para definir qué % de la renta le toca a cada dueño y a qué cuenta se paga.")
        st.button("➕ Simular Botón: Asignar Propietario a Inmueble", disabled=True)

    # ==========================================
    # TAB 4: INVENTARIOS (Mobiliario)
    # ==========================================
    with tab4:
        st.subheader("Control de Bienes y Mobiliario")
        st.info("💡 Control de activos. Si dejas la 'Unidad' en blanco, el sistema sabrá que pertenece a las Zonas Comunes del edificio.")
        st.button("➕ Simular Botón: Registrar Mobiliario", disabled=True)