import streamlit as st
from streamlit_option_menu import option_menu

# 1. CONFIGURACIÓN (Debe ir siempre de primero)
st.set_page_config(page_title="INMOLEASING", layout="wide")

# Ocultar menús de Streamlit para que se vea como una App real
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# 2. CONTROL DE SESIÓN
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# --- PANTALLA DE LOGIN ---
if not st.session_state.autenticado:
    cols = st.columns([1, 2, 1])
    with cols[1]:
        st.title("🏢 INMOLEASING")
        st.subheader("Acceso al Sistema")
        
        email_input = st.text_input("Correo electrónico")
        pass_input = st.text_input("Contraseña", type="password")
        
        if st.button("Entrar", use_container_width=True):
            try:
                #conn = st.connection("supabase", type="supabase")
                from supabase import create_client

                # Usa los secretos directamente
                url = st.secrets["connections"]["supabase"]["url"]
                key = st.secrets["connections"]["supabase"]["key"]
                supabase = create_client(url, key)
                res = conn.table("usuarios").select("*").eq("email", email_input).eq("password", pass_input).execute()
                
                if len(res.data) > 0:
                    st.session_state.autenticado = True
                    st.session_state.usuario = res.data[0]
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
            except Exception as e:
                st.error(f"Error de conexión: {e}")
    st.stop()

# --- SI EL USUARIO ESTÁ LOGUEADO, MOSTRAR EL CONTENIDO ---
# Barra lateral con nombre y botón de salida
st.sidebar.write(f"👤 Hola, **{st.session_state.usuario['nombre']}**")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

# TU MENÚ QUE YA FUNCIONABA
with st.sidebar:
    selected = option_menu(
        menu_title="INMOLEASING",
        options=["Menú Principal", "Usuarios", "Propietarios", "Inmuebles", "Arrendamientos", "Bancos", "Informes"],
        icons=["display", "person-badge", "people", "house", "file-earmark-text", "bank", "graph-up"],
        menu_icon="building",
        default_index=0,
    )

# 3. LÓGICA DE LAS PÁGINAS
if selected == "Menú Principal":
    st.title("🏠 Dashboard Principal")
    st.write(f"Bienvenido al sistema de gestión de moneda: {st.session_state.usuario['moneda']}")

elif selected == "Usuarios":
    st.title("👤 Gestión de Usuarios")
    st.info("Módulo en desarrollo")

elif selected == "Propietarios":
    st.title("👥 Propietarios")
    # Aquí puedes poner el formulario que hicimos antes