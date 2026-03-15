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

APP_VERSION = "v1.5.0" # Añadido Módulo de Operadores

import usuarios_modulo 
import operadores_modulo
# import propietarios_modulo  <--- Sigue apagado hasta que lo creemos

# ==========================================
# 2. FUNCIONES DE SEGURIDAD
# ==========================================
def encriptar_password(password):
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
        
        email_input = st.text_input("Correo electrónico").strip()
        pass_input = st.text_input("Contraseña", type="password").strip()
        
        if st.button("Entrar", use_container_width=True):
            try:
                email_limpio = email_input.lower()
                pass_hash = encriptar_password(pass_input)
                
                # Buscamos SOLO por correo
                res = supabase.table("usuarios").select("*").eq("email", email_limpio).execute()
                
                if len(res.data) == 0:
                    st.error(f"❌ No se encontró el correo: '{email_limpio}'")
                else:
                    usuario_data = res.data[0]
                    
                    # BLINDAJE DEFINITIVO: Limpiamos los datos que vienen de la Base de Datos
                    estado_db = str(usuario_data.get('estado', '')).strip().upper()
                    pass_db = str(usuario_data.get('password', '')).strip()
                    
                    if estado_db != 'ACTIVO':
                        st.error(f"❌ Cuenta encontrada, pero su estado es: '{estado_db}' (Debe ser ACTIVO)")
                        
                    elif pass_db != pass_hash:
                        st.error("❌ La contraseña no coincide.")
                        
                    # SI TODO ESTÁ PERFECTO:
                    else:
                        st.session_state.autenticado = True
                        st.session_state.usuario = usuario_data
                        st.session_state.usuario_actual = usuario_data['nombre'] 
                        st.session_state.moneda_usuario = usuario_data['moneda'] 
                        
                        ahora = datetime.utcnow().isoformat()
                        supabase.table("usuarios").update({"ultimo_acceso": ahora}).eq("id", usuario_data['id']).execute()
                        
                        st.rerun()
                        
            except Exception as e:
                st.error(f"Error de conexión con la base de datos: {e}")
                
    st.stop()

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
            "Operadores",
            "Propietarios", 
            "Inmuebles", 
            "Arrendamientos", 
            "Finanzas", 
            "Informes"
        ],
        icons=[
            "speedometer2", 
            "person-gear", 
            "briefcase",
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

elif selected == "Operadores":
    operadores_modulo.mostrar_modulo_operadores(supabase)

elif selected == "Propietarios":
    st.header("🤝 Propietarios")
    mostrar_proximamente("Propietarios")

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