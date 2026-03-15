import streamlit as st
from streamlit_option_menu import option_menu
from supabase import create_client
import hashlib
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y VERSIÓN
# ==========================================
st.set_page_config(page_title="INMOLEASING WEB", layout="wide", page_icon="🏢")
APP_VERSION = "v2.2 PRO" # Menú siempre visible con bloqueos en pantalla

# ==========================================
# 1.5 DICCIONARIO: MENÚ LATERAL <-> FACULTAD DB
# ==========================================
DICCIONARIO_MENU_FACULTADES = {
    "Dashboard": "MODULO DASHBOARD",
    "Usuarios": "MODULO USUARIOS",
    "Operadores": "MODULO OPERADORES",
    "Propietarios": "MODULO PROPIETARIOS",
    "Inmuebles": "MODULO INMUEBLES",
    "Arrendamientos": "MODULO ARRENDAMIENTOS",
    "Finanzas": "MODULO FINANZAS",
    "Informes": "MODULO INFORMES"
}

# ==========================================
# 1.6 AJUSTES VISUALES CSS
# ==========================================
st.markdown("""
    <style>
        [data-testid="stSidebarHeader"] { padding: 0rem !important; margin: 0rem !important; height: 0px !important; }
        [data-testid="stSidebarUserContent"] { padding-top: 0rem !important; margin-top: -4.5rem !important; }
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
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = get_supabase_client()

# ==========================================
# 4. CONTROL DE SESIÓN
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# ==========================================
# 5. LOGIN BLINDADO
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
                        st.error("❌ La contraseña no coincide.")
                    else:
                        id_rol = usuario_data.get('id_rol')
                        texto_facultades_gigante = ""
                        nombre_del_rol = "SIN ROL"
                        
                        if id_rol:
                            res_rol = supabase.table("roles").select("*").eq("id", id_rol).execute()
                            if res_rol.data:
                                r_data = res_rol.data[0]
                                texto_facultades_gigante = str(r_data).upper()
                                nombre_del_rol = str(r_data.get('nombre_rol', r_data.get('nombre', 'ROL CONFIGURADO'))).upper()

                        usuario_data['rol_nombre'] = nombre_del_rol
                        usuario_data['facultades_texto'] = texto_facultades_gigante
                        
                        st.session_state.autenticado = True
                        st.session_state.usuario = usuario_data
                        st.session_state.moneda_usuario = usuario_data.get('moneda', 'ALL')
                        
                        supabase.table("usuarios").update({"ultimo_acceso": datetime.utcnow().isoformat()}).eq("id", usuario_data['id']).execute()
                        st.rerun()
                        
            except Exception as e:
                st.error(f"Error crítico de conexión: {e}")
                
    st.stop()

# ==========================================
# 6. MENÚ LATERAL SIEMPRE VISIBLE
# ==========================================
with st.sidebar:
    st.title("🏢 INMOLEASING")
    st.write(f"👤 Hola, **{st.session_state.usuario.get('nombre')}**")
    
    rol_actual = st.session_state.usuario.get('rol_nombre', 'SIN ROL')
    texto_facultades = st.session_state.usuario.get('facultades_texto', '')
    
    st.caption(f"Perfil: **{rol_actual}**")

    # Calculamos QUÉ módulos tiene permitidos (Pero no los ocultamos)
    st.session_state.opciones_permitidas = []
    for menu_item, facultad_requerida in DICCIONARIO_MENU_FACULTADES.items():
        if facultad_requerida in texto_facultades:
            st.session_state.opciones_permitidas.append(menu_item)

    if "ADMINISTRADOR" in texto_facultades or "ADMINISTRADOR" in rol_actual:
        st.session_state.opciones_permitidas = list(DICCIONARIO_MENU_FACULTADES.keys())

    if not st.session_state.opciones_permitidas:
        st.session_state.opciones_permitidas = ["Dashboard"]

    # Mostramos TODOS los botones siempre
    menu_map = {
        "Dashboard": "speedometer2", "Usuarios": "person-gear", "Operadores": "briefcase",
        "Propietarios": "person-badge", "Inmuebles": "house-door", "Arrendamientos": "file-earmark-check",
        "Finanzas": "bank", "Informes": "graph-up-arrow"
    }
    
    opciones_todas = list(menu_map.keys())
    iconos_todos = list(menu_map.values())

    selected = option_menu(
        menu_title="Menú Principal",
        options=opciones_todas, 
        icons=iconos_todos,     
        menu_icon="cast",
        default_index=0,
    )
    
    st.markdown("---")
    st.caption(f"Versión: {APP_VERSION}")
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

# ==========================================
# 7. ENRUTADOR CON CUSTODIO DE ACCESO
# ==========================================
# Si el usuario hace clic en algo que no está en su lista de permitidos, le ponemos el candado
if selected not in st.session_state.opciones_permitidas:
    st.error(f"### 🔒 Acceso Restringido")
    st.warning(f"Tu perfil actual (**{rol_actual}**) no cuenta con las facultades necesarias para visualizar o gestionar el módulo de **{selected}**.")
    st.info("Si consideras que esto es un error, por favor contacta con el administrador del sistema para que asigne esta facultad a tu rol.")
else:
    # Si sí tiene permiso, cargamos el módulo correspondiente
    if selected == "Dashboard":
        st.header("📈 Dashboard Principal")
        st.info("Aquí irán las gráficas y resúmenes de la operación.")

    elif selected == "Usuarios":
        usuarios_modulo.mostrar_modulo_usuarios(supabase)

    elif selected == "Operadores":
        operadores_modulo.mostrar_modulo_operadores(supabase)

    else:
        st.header(f"Módulo: {selected}")
        st.info("🚧 Módulo en construcción. Pronto estará disponible.")