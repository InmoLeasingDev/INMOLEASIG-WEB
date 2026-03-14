import streamlit as st
from streamlit_option_menu import option_menu
from supabase import create_client

# 1. CONFIGURACIÓN DE PÁGINA (Debe ser lo primero)
st.set_page_config(page_title="INMOLEASING", layout="wide", page_icon="🏢")

# Ocultar menús nativos de Streamlit para apariencia profesional
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# 2. CONEXIÓN A SUPABASE (Forma compatible)
@st.cache_resource
def get_supabase_client():
    # Asegúrate de que en Streamlit Cloud > Settings > Secrets tengas:
    # [connections.supabase]
    # url = "tu_url"
    # key = "tu_key"
    url = st.secrets["connections"]["supabase"]["url"]
    key = st.secrets["connections"]["supabase"]["key"]
    return create_client(url, key)

# Inicializamos la conexión
try:
    conn = get_supabase_client()
except Exception as e:
    st.error(f"Error crítico de configuración: {e}")
    st.stop()

# 3. CONTROL DE SESIÓN
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# --- PANTALLA DE LOGIN ---
if not st.session_state.autenticado:
    cols = st.columns([1, 2, 1])
    with cols[1]:
        st.title("🏢 INMOLEASING")
        st.subheader("Acceso al Sistema")
        
        email_input = st.text_input("Correo electrónico", placeholder="ejemplo@correo.com")
        pass_input = st.text_input("Contraseña", type="password")
        
        if st.button("Entrar", use_container_width=True):
            try:
                # Consulta a la tabla usuarios
                res = conn.table("usuarios").select("*").eq("email", email_input).eq("password", pass_input).execute()
                
                if len(res.data) > 0:
                    st.session_state.autenticado = True
                    st.session_state.usuario = res.data[0]
                    st.success("✅ Acceso concedido")
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
            except Exception as e:
                st.error(f"Error al validar credenciales: {e}")
    st.stop() 

# --- INTERFAZ PRINCIPAL (Solo se ve si el login es exitoso) ---

# Sidebar: Usuario y Botón de Salir
st.sidebar.markdown(f"### 👤 Bienvenido\n**{st.session_state.usuario.get('nombre', 'Usuario')}**")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

# Menú Lateral
with st.sidebar:
    selected = option_menu(
        menu_title="INMOLEASING",
        options=["Menú Principal", "Usuarios", "Propietarios", "Inmuebles", "Arrendamientos", "Bancos", "Informes"],
        icons=["display", "person-badge", "people", "house", "file-earmark-text", "bank", "graph-up"],
        menu_icon="building",
        default_index=0,
    )

# 4. LÓGICA DE NAVEGACIÓN
if selected == "Menú Principal":
    st.title("🏠 Dashboard Principal")
    moneda = st.session_state.usuario.get('moneda', 'USD')
    st.write(f"Bienvenido al sistema de gestión. Moneda configurada: **{moneda}**")
    
    # Aquí puedes agregar métricas rápidas
    c1, c2, c3 = st.columns(3)
    c1.metric("Inmuebles Activos", "24")
    c2.metric("Arrendamientos", "12")
    c3.metric("Pendientes", "3")

elif selected == "Usuarios":
    st.title("👤 Gestión de Usuarios")
    st.info("Módulo de administración de personal en desarrollo.")

elif selected == "Propietarios":
    st.title("👥 Propietarios")
    st.write("Listado y registro de propietarios del sistema.")

elif selected == "Inmuebles":
    st.title("house Gestión de Inmuebles")
    st.write("Administración de propiedades y disponibilidad.")

# (Agrega el resto de elif para las demás opciones según necesites)