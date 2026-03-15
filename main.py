import streamlit as st
from streamlit_option_menu import option_menu
from supabase import create_client
import hashlib
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y VERSIÓN
# ==========================================
st.set_page_config(
    page_title="INMOLEASING WEB", 
    layout="wide", 
    page_icon="🏢"
)

APP_VERSION = "v1.4.0" 

import usuarios_modulo 
import propietarios_modulo 

# ==========================================
# 2. FUNCIONES DE SEGURIDAD
# ==========================================
def encriptar_password(password):
    """
    Convierte la contraseña en texto plano a un Hash SHA-256
    para que viaje y se almacene de forma segura.
    """
    return hashlib.sha256(password.encode()).hexdigest()

# ==========================================
# 3. CONEXIÓN A BASE DE DATOS
# ==========================================
@st.cache_resource 
def get_supabase_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_supabase_client()

# ==========================================
# 4. CONTROL DE SESIÓN
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# ==========================================
# 5. PANTALLA DE LOGIN
# ==========================================
if not st.session_state.autenticado:
    cols = st.columns([1, 2, 1])
    
    with cols[1]:
        st.title("🏢 INMOLEASING")
        st.markdown(f"**Acceso al Sistema** *(Versión {APP_VERSION})*")
        
        email_input = st.text_input("Correo electrónico")
        pass_input = st.text_input("Contraseña", type="password")
        
        if st.button("Entrar", use_container_width=True):
            try:
                # Encriptamos la clave digitada antes de enviarla
                pass_hash = encriptar_password(pass_input)
                
                # Consulta a Supabase verificando credenciales y estado activo
                res = supabase.table("usuarios").select("*").eq(
                    "email", email_input.lower()
                ).eq(
                    "password", pass_hash
                ).eq(
                    "estado", "ACTIVO"
                ).execute()
                
                # Si hay coincidencia, el usuario existe y las claves cuadran
                if len(res.data) > 0:
                    usuario_data = res.data[0]
                    
                    # Guardamos los datos en la memoria de la sesión
                    st.session_state.autenticado = True
                    st.session_state.usuario = usuario_data
                    st.session_state.usuario_actual = usuario_data['nombre'] 
                    st.session_state.moneda_usuario = usuario_data['moneda'] 
                    
                    # Actualizamos la fecha del último acceso en la base de datos
                    ahora = datetime.utcnow().isoformat()
                    supabase.table("usuarios").update({
                        "ultimo_acceso": ahora
                    }).eq("id", usuario_data['id']).execute()
                    
                    # Refrescamos la página para entrar al sistema
                    st.rerun()
                else:
                    st.error("❌ Usuario/contraseña incorrectos o cuenta INACTIVA.")
                    
            except Exception as e:
                st.error(f"Error de conexión con la base de datos: {e}")
                
    st.stop() # Detiene la ejecución aquí si no está autenticado

# ==========================================
# 6. MENÚ LATERAL Y NAVEGACIÓN
# ==========================================
def mostrar_proximamente(modulo):
    st.warning(f"### 🚧 Módulo en Desarrollo")
    st.write(f"Muy pronto tendrás aquí toda la **gestión de {modulo.lower()}**.")

with st.sidebar:
    st.title("🏢 INMOLEASING")
    st.write(f"👤 Hola, **{st.session_state.usuario.get('nombre', 'Usuario')}**")
    st.caption(f"Región/Moneda: **{st.session_state.get('moneda_usuario', 'ALL')}**")
    st.caption(f"Versión: {APP_VERSION}")
    
    selected = option_menu(
        menu_title="Menú Principal",
        options=[
            "Dashboard", 
            "Usuarios", 
            "Propietarios", 
            "Inmuebles", 
            "Arrendamientos", 
            "Finanzas", 
            "Informes"
        ],
        icons=[
            "speedometer2", 
            "person-gear", 
            "person-badge", 
            "house-door", 
            "file-earmark-check", 
            "bank", 
            "graph-up-arrow"
        ],
        menu_icon="cast",
        default_index=0,
    )
    
    st.markdown("---")
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.usuario_actual = None
        st.session_state.moneda_usuario = None
        st.rerun()

# ==========================================
# 7. ENRUTADOR DE MÓDULOS
# ==========================================
if selected == "Dashboard":
    st.header("📈 Dashboard Principal")
    mostrar_proximamente("Panel de Control")

elif selected == "Usuarios":
    usuarios_modulo.mostrar_modulo_usuarios(supabase)

elif selected == "Propietarios":
    propietarios_modulo.mostrar_modulo_propietarios(supabase)

elif selected == "Inmuebles":
    st.header("🏠 Gestión de Inmuebles")
    mostrar_proximamente("Inmuebles")

elif selected == "Arrendamientos":
    st.header("📝 Arrendamientos")
    mostrar_proximamente("Contratos")

elif selected == "Finanzas":
    st.header("🏦 Finanzas y Contabilidad")
    mostrar_proximamente("Bancos y Contabilidad")

elif selected == "Informes":
    st.header("📊 Informes de Gestión")
    mostrar_proximamente("Reportes Consolidados")