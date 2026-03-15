import streamlit as st
from streamlit_option_menu import option_menu
from supabase import create_client

# 1. CONFIGURACIÓN DE PÁGINA Y VERSIÓN (¡Debe ir primero!)
st.set_page_config(page_title="INMOLEASING WEB", layout="wide", page_icon="🏢")

# --- CONTROL DE VERSIONES ---
APP_VERSION = "v1.2.0" # Actualizado por la unificación de Finanzas

import usuarios_modulo 

# 2. CONEXIÓN A BASE DE DATOS
@st.cache_resource 
def get_supabase_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_supabase_client()

# 3. CONTROL DE SESIÓN
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# --- PANTALLA DE LOGIN ---
if not st.session_state.autenticado:
    cols = st.columns([1, 2, 1])
    with cols[1]:
        st.title("🏢 INMOLEASING")
        st.markdown(f"**Acceso al Sistema** *(Versión {APP_VERSION})*")
        
        email_input = st.text_input("Correo electrónico")
        pass_input = st.text_input("Contraseña", type="password")
        
        if st.button("Entrar", use_container_width=True):
            try:
                res = supabase.table("usuarios").select("*").eq("email", email_input).eq("password", pass_input).eq("estado", "ACTIVO").execute()
                
                if len(res.data) > 0:
                    st.session_state.autenticado = True
                    st.session_state.usuario = res.data[0]
                    st.session_state.usuario_actual = res.data[0]['nombre'] 
                    st.rerun()
                else:
                    st.error("❌ Usuario/contraseña incorrectos o cuenta INACTIVA.")
            except Exception as e:
                st.error(f"Error de conexión: {e}")
    st.stop()

# --- MENÚ LATERAL ---
def mostrar_proximamente(modulo):
    st.warning(f"### 🚧 Módulo en Desarrollo")
    st.write(f"Muy pronto tendrás aquí toda la **gestión de {modulo.lower()}**.")

with st.sidebar:
    st.title("🏢 INMOLEASING")
    st.write(f"👤 Hola, **{st.session_state.usuario.get('nombre', 'Usuario')}**")
    st.caption(f"Versión: {APP_VERSION}")
    
    selected = option_menu(
        menu_title="Menú Principal",
        options=["Dashboard", "Usuarios", "Propietarios", "Inmuebles", "Arrendamientos", "Finanzas", "Informes"],
        icons=["speedometer2", "person-gear", "person-badge", "house-door", "file-earmark-check", "bank", "graph-up-arrow"],
        menu_icon="cast",
        default_index=0,
    )
    
    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.session_state.usuario_actual = None
        st.rerun()

# --- LÓGICA DE NAVEGACIÓN ---
if selected == "Dashboard":
    st.header("📈 Dashboard Principal")
    mostrar_proximamente("Panel de Control (Dashboard)")

elif selected == "Usuarios":
    usuarios_modulo.mostrar_modulo_usuarios(supabase)

elif selected == "Propietarios":
    st.header("🤝 Propietarios")
    sub_tab = st.tabs(["Fichas Propietarios", "Contratos Propietarios"])
    with sub_tab[0]:
        mostrar_proximamente("Fichas de Propietarios")
    with sub_tab[1]:
        mostrar_proximamente("Contratos de Mandato")

elif selected == "Inmuebles":
    st.header("🏠 Gestión de Inmuebles")
    sub_tab = st.tabs(["Inmuebles Principales", "Unidades Habitacionales", "Inventarios", "Incidencias"])
    with sub_tab[0]:
        mostrar_proximamente("Inmuebles")
    with sub_tab[1]:
        mostrar_proximamente("Unidades")
    with sub_tab[2]:
        mostrar_proximamente("Inventarios Detallados")
    with sub_tab[3]:
        mostrar_proximamente("Reporte de Incidencias")

elif selected == "Arrendamientos":
    st.header("📝 Arrendamientos")
    sub_tab = st.tabs(["Arrendatarios", "Contratos Arriendo", "Suministros"])
    for i, tab_name in enumerate(["Arrendatarios", "Contratos", "Suministros"]):
        with sub_tab[i]:
            mostrar_proximamente(tab_name)

elif selected == "Finanzas":
    st.header("🏦 Finanzas y Contabilidad")
    sub_tab = st.tabs(["Bancos y Conciliación", "Cuentas por Cobrar (CXC)", "Cuentas por Pagar (CXP)", "PyG", "Balance"])
    for i, tab_name in enumerate(["Bancos", "CXC", "CXP", "PyG", "Balance"]):
        with sub_tab[i]:
            mostrar_proximamente(tab_name)

elif selected == "Informes":
    st.header("📊 Informes de Gestión")
    mostrar_proximamente("Reportes Consolidados")