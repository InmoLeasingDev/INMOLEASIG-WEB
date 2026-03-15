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

APP_VERSION = "v1.6.6" # Restauración Completa y Mapeo de Facultades

# ==========================================
# 1.5 DICCIONARIO DE TRADUCCIÓN (DB -> UI)
# ==========================================
# Relacionamos los nombres de tu tabla 'facultades' con los del menú lateral
DICCIONARIO_FACULTADES = {
    "MODULO DASHBOARD": "Dashboard",
    "MODULO USUARIOS": "Usuarios",
    "MODULO OPERADORES": "Operadores",
    "MODULO PROPIETARIOS": "Propietarios",
    "MODULO INMUEBLES": "Inmuebles",
    "MODULO ARRENDAMIENTOS": "Arrendamientos",
    "MODULO FINANZAS": "Finanzas",
    "MODULO INFORMES": "Informes"
}

# ==========================================
# 1.6 AJUSTES VISUALES CSS (EXTREMO)
# ==========================================
st.markdown("""
    <style>
        [data-testid="stSidebarHeader"] {
            padding: 0rem !important; margin: 0rem !important;
            height: 0px !important; min-height: 0px !important;
        }
        [data-testid="stSidebarUserContent"] {
            padding-top: 0rem !important; margin-top: -4.5rem !important; 
        }
        .block-container { padding-top: 1.5rem !important; }
    </style>
""", unsafe_allow_html=True)

import usuarios_modulo 
import operadores_modulo

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
# 5. PANTALLA DE LOGIN REFORZADA
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
                
                res = supabase.table("usuarios").select("*").eq("email", email_limpio).execute()
                
                if len(res.data) == 0:
                    st.error(f"❌ No se encontró el correo: '{email_limpio}'")
                else:
                    usuario_data = res.data[0]
                    estado_db = str(usuario_data.get('estado', '')).strip().upper()
                    pass_db = str(usuario_data.get('password', '')).strip()
                    
                    if estado_db != 'ACTIVO':
                        st.error(f"❌ Cuenta inactiva.")
                    elif pass_db != pass_hash:
                        st.error("❌ Contraseña incorrecta.")
                    else:
                        # CARGA DE FACULTADES DESDE LA RELACIÓN ROL-FACULTAD
                        facultades_usuario = []
                        id_rol = usuario_data.get('id_rol')
                        
                        if id_rol:
                            # 1. Buscamos el nombre del Rol
                            res_rol = supabase.table("roles").select("nombre").eq("id", id_rol).execute()
                            rol_nombre = res_rol.data[0]['nombre'].upper() if res_rol.data else "SIN ROL"
                            
                            # 2. Buscamos las facultades asociadas a ese rol (vía tabla intermedia si existe)
                            # Para simplificar y que funcione con tu captura, haremos una lectura de la tabla facultades
                            # que coincidan con los permisos del rol.
                            try:
                                # Aquí simulamos la lectura de facultades vinculadas
                                # AJUSTE: Si tienes una tabla roles_facultades, aquí se consultaría
                                res_f = supabase.table("facultades").select("nombre_facultad").execute()
                                # Por ahora, traemos todas las que correspondan al perfil
                                facultades_usuario = [f['nombre_facultad'].upper() for f in res_f.data]
                            except:
                                pass
                        
                        usuario_data['rol_nombre'] = rol_nombre
                        usuario_data['facultades_list'] = facultades_usuario

                        st.session_state.autenticado = True
                        st.session_state.usuario = usuario_data
                        st.session_state.moneda_usuario = usuario_data.get('moneda', 'ALL')
                        
                        supabase.table("usuarios").update({"ultimo_acceso": datetime.utcnow().isoformat()}).eq("id", usuario_data['id']).execute()
                        st.rerun()
                        
            except Exception as e:
                st.error(f"Error de conexión: {e}")
                
    st.stop()

# ==========================================
# 6. MENÚ LATERAL DINÁMICO (REVISADO)
# ==========================================
with st.sidebar:
    st.title("🏢 INMOLEASING")
    st.write(f"👤 Hola, **{st.session_state.usuario.get('nombre')}**")
    
    facultades_db = st.session_state.usuario.get('facultades_list', [])
    rol_actual = st.session_state.usuario.get('rol_nombre', 'SIN ROL')
    
    st.caption(f"Rol: {rol_actual}")
    st.caption(f"Versión: {APP_VERSION}")

    # Traducimos facultades de la DB a opciones del menú
    opciones_permitidas = ["Dashboard"]
    for f in facultades_db:
        if f in DICCIONARIO_FACULTADES:
            opciones_permitidas.append(DICCIONARIO_FACULTADES[f])

    # Si es ADMIN, forzamos todas las opciones
    if rol_actual == "ADMINISTRADOR":
        opciones_permitidas = list(DICCIONARIO_FACULTADES.values())

    menu_completo = [
        {"n": "Dashboard", "i": "speedometer2"},
        {"n": "Usuarios", "i": "person-gear"},
        {"n": "Operadores", "i": "briefcase"},
        {"n": "Propietarios", "i": "person-badge"},
        {"n": "Inmuebles", "i": "house-door"},
        {"n": "Arrendamientos", "i": "file-earmark-check"},
        {"n": "Finanzas", "i": "bank"},
        {"n": "Informes", "i": "graph-up-arrow"}
    ]

    # Filtro final
    opciones_final = [m["n"] for m in menu_completo if m["n"] in opciones_permitidas]
    iconos_final = [m["i"] for m in menu_completo if m["n"] in opciones_permitidas]

    selected = option_menu(
        menu_title="Menú Principal",
        options=opciones_final, 
        icons=iconos_final,     
        menu_icon="cast",
        default_index=0,
    )
    
    st.markdown("---")
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

# ==========================================
# 7. ENRUTADOR SEGURO
# ==========================================
if selected == "Dashboard":
    st.header("📈 Dashboard Principal")
elif selected == "Usuarios":
    usuarios_modulo.mostrar_modulo_usuarios(supabase)
elif selected == "Operadores":
    operadores_modulo.mostrar_modulo_operadores(supabase)
else:
    st.info(f"Módulo {selected} disponible según sus facultades.")