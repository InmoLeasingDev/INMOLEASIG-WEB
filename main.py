import streamlit as st
from streamlit_option_menu import option_menu
from supabase import create_client
from datetime import datetime  # <--- Agrega esta
import pytz                    # <--- Y esta

# 1. CONFIGURACIÓN DE LA PÁGINA (Debe ser lo primero)
st.set_page_config(page_titl)
# 2. CONEXIÓN A SUPABASE (El nuevo motor que no falla)
@st.cache_resource
def get_supabase_client():
    url = st.secrets["connections"]["supabase"]["url"]
    key = st.secrets["connections"]["supabase"]["key"]
    return create_client(url, key)

conn = get_supabase_client()

# 3. CONTROL DE SESIÓN
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
                # Consulta con el nuevo motor (usamos .execute())
                res = conn.table("usuarios").select("*").eq("email", email_input).eq("password", pass_input).execute()
                
                if len(res.data) > 0:
                    st.session_state.autenticado = True
                    st.session_state.usuario = res.data[0]
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
            except Exception as e:
                st.error(f"Error de conexión: {e}")
    st.stop() # Detiene la ejecución aquí si no se ha logueado

# --- TODO LO QUE SIGUE ES TU CÓDIGO RECUPERADO ---

# Función para mostrar el mensaje de "En construcción"
def mostrar_proximamente(modulo):
    st.warning(f"### 🚧 Módulo en Desarrollo")
    st.write(f"Muy pronto tendrás aquí toda la **gestión de {modulo.lower()}**.")
    st.info("Estamos trabajando para integrar las bases de datos y funciones de este apartado.")

# 1. MENÚ LATERAL
with st.sidebar:
    st.title("🏢 INMOLEASING")
    
    # 1. Nombre del Usuario y Saludo
    st.write(f"👤 Hola, **{st.session_state.usuario.get('nombre', 'Usuario')}**")
    
    # 2. Menú de Navegación (Lo que más se usa)
    selected = option_menu(
        menu_title="Menú Principal",
        options=["Usuarios", "Propietarios", "Inmuebles", "Arrendamientos", "Bancos", "Informes"],
        icons=["person-gear", "person-badge", "house-door", "file-earmark-check", "bank", "graph-up-arrow"],
        menu_icon="cast",
        default_index=0,
    )
    
    # 3. Botón de Cerrar Sesión
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

    # --- ESPACIO FLEXIBLE ---
    # Esto empuja los relojes hacia abajo si hay espacio en la pantalla
    st.markdown("<br><br>", unsafe_allow_html=True) 
    
    # 4. RELOJES (Al final de todo)
    st.markdown("---")
    tz_madrid = pytz.timezone('Europe/Madrid')
    tz_bogota = pytz.timezone('America/Bogota')
    
    hora_madrid = datetime.now(tz_madrid).strftime("%H:%M")
    hora_bogota = datetime.now(tz_bogota).strftime("%H:%M")
    
    c1, c2 = st.columns(2)
    c1.metric("🇪🇸 Madrid", hora_madrid)
    c2.metric("🇨🇴 Bogotá", hora_bogota)

# xyz
#with st.sidebar:
#    st.title("🏢 INMOLEASING")
#    # Lógica de relojes
#    tz_madrid = pytz.timezone('Europe/Madrid')
#    tz_bogota = pytz.timezone('America/Bogota')
#    hora_madrid = datetime.now(tz_madrid).strftime("%H:%M")
#    hora_bogota = datetime.now(tz_bogota).strftime("%H:%M")
#    
#    # Diseño de relojes en columnas
#    c1, c2 = st.columns(2)
#    c1.metric("MADRID", hora_madrid)
#    c2.metric("BOGOTA", hora_bogota)
#    
#    st.markdown("---") # Separador visual
#    # Mostrar nombre del usuario logueado
#    st.write(f"👤 Hola, **{st.session_state.usuario.get('nombre', 'Usuario')}**")
#    
#    selected = option_menu(
#        menu_title="Menú Principal",
#        options=["Usuarios", "Propietarios", "Inmuebles", "Arrendamientos", "Bancos", "Informes"],
#        icons=["person-gear", "person-badge", "house-door", "file-earmark-check", "bank", "graph-up-arrow"],
#        menu_icon="cast",
#        default_index=0,
#    )
#    
#    if st.button("Cerrar Sesión"):
#        st.session_state.autenticado = False
#        st.rerun()
# XYZ

# --- LÓGICA DE NAVEGACIÓN ---

if selected == "Usuarios":
    st.header("👤 Gestión de Usuarios")
    mostrar_proximamente("Usuarios")

elif selected == "Propietarios":
    st.header("🤝 Propietarios")
    sub_tab = st.tabs(["Fichas Propietarios", "Contratos Propietarios"])
    with sub_tab[0]:
        mostrar_proximamente("Fichas de Propietarios")
    with sub_tab[1]:
        mostrar_proximamente("Contratos de Mandato")

elif selected == "Inmuebles":
    st.header("🏠 Gestión de Inmuebles")
    sub_tab = st.tabs(["Unidades", "Inventarios", "Incidencias"])
    with sub_tab[0]:
        mostrar_proximamente("Unidades Habitacionales")
    with sub_tab[1]:
        mostrar_proximamente("Inventarios Detallados")
    with sub_tab[2]:
        mostrar_proximamente("Reporte de Incidencias")

elif selected == "Arrendamientos":
    st.header("📝 Arrendamientos")
    sub_tab = st.tabs(["Contratos Arriendo", "Suministros"])
    with sub_tab[0]:
        mostrar_proximamente("Contratos de Arrendamiento")
    with sub_tab[1]:
        mostrar_proximamente("Control de Suministros")

elif selected == "Bancos":
    st.header("🏦 Conciliación Bancaria")
    mostrar_proximamente("Bancos y Movimientos")

elif selected == "Informes":
    st.header("📊 Informes de Gestión")
    mostrar_proximamente("Informes y Estadísticas")