import streamlit as st
from streamlit_option_menu import option_menu
from supabase import create_client
from datetime import datetime
import pytz
import usuarios_modulo 

# 1. PRIMERO DEFINES LA FUNCIÓN

def get_supabase_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# 2. LUEGO CREAS LA VARIABLE (Esto iría después de la definición)
supabase = get_supabase_client()

# 3. CONFIGURACIÓN DE LA PÁGINA (Debe ser lo primero)
st.set_page_config(page_title="INMOLEASING WEB", layout="wide", page_icon="🏢")

# 5. CONTROL DE SESIÓN
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

# 6. MENÚ LATERAL
with st.sidebar:
    st.title("🏢 INMOLEASING")
        # Mostrar nombre del usuario logueado
    st.write(f"👤 Hola, **{st.session_state.usuario.get('nombre', 'Usuario')}**")
    
    selected = option_menu(
        menu_title="Menú Principal",
        options=["Usuarios", "Propietarios", "Inmuebles", "Arrendamientos", "Bancos", "Informes"],
        icons=["person-gear", "person-badge", "house-door", "file-earmark-check", "bank", "graph-up-arrow"],
        menu_icon="cast",
        default_index=0,
    )
    
    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

# --- LÓGICA DE NAVEGACIÓN ---

if selected == "Usuarios":
    st.header("👤 Gestión de Usuarios")
    usuarios_modulo.mostrar_modulo_usuarios(supabase) # <--- Llamas a la función    

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