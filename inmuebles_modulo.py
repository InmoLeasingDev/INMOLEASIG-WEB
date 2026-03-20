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
    # ==========================================
    # TAB 1: PROPIEDADES (El Cascarón)
    # ==========================================
    with tab1:
        st.subheader("Catálogo de Propiedades Base")
        st.info("💡 Aquí daremos de alta el edificio o casa principal (Ej: Edificio Los Alpes, Casa Calle 5).")
        
        # --- 1. FORMULARIO NUEVA PROPIEDAD ---
        with st.expander("➕ Añadir Nueva Propiedad", expanded=False):
            with st.form("form_nueva_propiedad"):
                st.write("Datos Generales del Inmueble")
                c1, c2, c3 = st.columns(3)
                n_nom = c1.text_input("Nombre / Dirección Principal *", placeholder="Ej: Edificio Central")
                n_tip = c2.selectbox("Tipo de Propiedad *", ["EDIFICIO", "CASA", "LOCAL COMERCIAL", "LOTE/TERRENO", "OTRO"])
                n_ciu = c3.text_input("Ciudad *")
                
                st.write("Datos del Seguro (Opcional)")
                c4, c5, c6 = st.columns(3)
                n_ase = c4.text_input("Aseguradora")
                n_pol = c5.text_input("Número de Póliza")
                n_tel_ase = c6.text_input("Teléfono Aseguradora")
                
                if st.form_submit_button("💾 Guardar Propiedad"):
                    if n_nom and n_tip and n_ciu:
                        datos_insert = {
                            "nombre": n_nom.strip().upper(),
                            "tipo": n_tip,
                            "ciudad": n_ciu.strip().upper(),
                            "aseguradora": n_ase.strip().upper(),
                            "numero_poliza": n_pol.strip().upper(),
                            "telefono_aseguradora": n_tel_ase.strip(),
                            "estado": "ACTIVO"
                        }
                        try:
                            supabase.table("inmuebles").insert(datos_insert).execute()
                            log_accion(supabase, usuario_actual, "CREAR PROPIEDAD", n_nom.strip().upper())
                            st.success("✅ Propiedad registrada con éxito.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")
                    else:
                        st.warning("⚠️ Los campos con asterisco (*) son obligatorios.")

        st.markdown("---")
        
        # --- 2. TABLA DE PROPIEDADES ---
        try:
            res_inm = supabase.table("inmuebles").select("*").order("id", desc=True).execute()
            df_inm = pd.DataFrame(res_inm.data) if res_inm.data else pd.DataFrame()
            
            if not df_inm.empty:
                df_display = df_inm[['id', 'nombre', 'tipo', 'ciudad', 'aseguradora', 'estado']].copy()
                df_display.rename(columns={'id': 'ID', 'nombre': 'NOMBRE', 'tipo': 'TIPO', 'ciudad': 'CIUDAD', 'aseguradora': 'ASEGURADORA', 'estado': 'ESTADO'}, inplace=True)
                st.dataframe(df_display, use_container_width=True, hide_index=True)
            else:
                st.info("Aún no hay propiedades registradas en la base de datos.")
        except Exception as e:
            st.error(f"Error de conexión con la tabla inmuebles: {e}")

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