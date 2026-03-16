import streamlit as st
from streamlit_option_menu import option_menu
from supabase import create_client
import hashlib
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y VERSIÓN
# ==========================================
st.set_page_config(page_title="INMOLEASING WEB", layout="wide", page_icon="🏢")
APP_VERSION = "v3.9 PRO" # Versión Completa con simetría y botón ajustado

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
# 1.6 AJUSTES VISUALES CSS (EL CORAZÓN DEL DISEÑO)
# ==========================================
st.markdown("""
    <style>
        /* 1. LIMPIEZA DEL HEADER LATERAL */
        [data-testid="stSidebarHeader"] { padding: 0rem !important; margin: 0rem !important; height: 0px !important; min-height: 0px !important; }
        
        /* 2. MENÚ LATERAL ARRIBA */
        [data-testid="stSidebarUserContent"] { padding-top: 1rem !important; margin-top: -0.5rem !important; }
        
        /* 3. BLOQUE PRINCIPAL POSICIÓN */
        .block-container { padding-top: 3rem !important; }

        /* 4. AJUSTE DEL BOTÓN CERRAR SESIÓN: Lo subimos para que no quede en el fondo */
        .stButton button { margin-top: -1.5rem !important; }
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
# 5. LOGIN BLINDADO (RESTAURADO)
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
# 6. MENÚ LATERAL CON AJUSTES DE LÍNEAS
# ==========================================
with st.sidebar:
    st.title("🏢 INMOLEASING")
    st.caption(f"Versión: {APP_VERSION}")
    
    st.write(f"👤 Hola, **{st.session_state.usuario.get('nombre')}**")
    st.caption(f"Región/Moneda: **{st.session_state.moneda_usuario}**")
    
    rol_actual = st.session_state.usuario.get('rol_nombre', 'SIN ROL')
    texto_facultades = st.session_state.usuario.get('facultades_texto', '')
    st.caption(f"Perfil: **{rol_actual}**")
    
    # Línea superior pegada al perfil
    st.markdown("<hr style='margin-top: 0.2rem; margin-bottom: 0.5rem;'>", unsafe_allow_html=True)

    st.session_state.opciones_permitidas = []
    for menu_item, facultad_requerida in DICCIONARIO_MENU_FACULTADES.items():
        if facultad_requerida in texto_facultades or "ADMINISTRADOR" in rol_actual:
            st.session_state.opciones_permitidas.append(menu_item)

    # El botón Inicio siempre es visible para todos
    opciones_todas = ["Inicio", "Dashboard", "Usuarios", "Operadores", "Propietarios", "Inmuebles", "Arrendamientos", "Finanzas", "Informes"]
    iconos_todos = ["house", "speedometer2", "person-gear", "briefcase", "person-badge", "house-door", "file-earmark-check", "bank", "graph-up-arrow"]

    selected = option_menu(
        menu_title=None,
        options=opciones_todas, 
        icons=iconos_todos,     
        menu_icon="cast",
        default_index=0, 
    )
    
    # LÍNEA INFERIOR: Ajustada para simetría (-1.2rem)
    st.markdown("<hr style='margin-top: -1.2rem; margin-bottom: 1.5rem;'>", unsafe_allow_html=True)
    
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

# ==========================================
# 7. ENRUTADOR CON ICONOS Y SEGURIDAD (RESTAURADO)
# ==========================================

if selected == "Inicio":
    st.title("🏢 INMOLEASING")
    st.markdown(f"**Te damos la bienvenida al Sistema Integral de Gestión Inmobiliaria.**")
    st.caption(f"Versión actual: {APP_VERSION}")
    
    st.write("") 
    
    # Foto central con tamaño ajustado
    img_cols = st.columns([0.6, 1.2, 0.6]) 
    with img_cols[1]:
        try:
            st.image("portada.jpg", use_container_width=True)
        except:
            st.warning("No se encontró la imagen 'portada.jpg'.")
            
    st.write("") 
    st.info("👋 Por favor, selecciona una opción en el menú lateral para comenzar a operar.")

elif selected not in st.session_state.opciones_permitidas and selected != "Inicio":
    st.error(f"### 🔒 Acceso Restringido")
    st.warning(f"Tu perfil actual (**{rol_actual}**) no cuenta con las facultades necesarias para **{selected}**.")
    st.info("Contacta con el administrador para solicitar acceso.")

else:
    # CARGA DE MÓDULOS CON ICONOS RESTAURADOS
    if selected == "Dashboard":
        st.header("📈 Dashboard Principal")
        st.info("🚧 Módulo en construcción. Pronto estará disponible.")

    elif selected == "Usuarios":
        usuarios_modulo.mostrar_modulo_usuarios(supabase)

    elif selected == "Operadores":
        operadores_modulo.mostrar_modulo_operadores(supabase)

    elif selected == "Propietarios":
        st.header("🤝 Propietarios")
        st.info("🚧 Módulo en construcción. Pronto estará disponible.")

    elif selected == "Inmuebles":
        st.header("🏠 Gestión de Inmuebles")
        st.info("🚧 Módulo en construcción. Pronto estará disponible.")

    elif selected == "Arrendamientos":
        st.header("📝 Arrendamientos")
        st.info("🚧 Módulo en construcción. Pronto estará disponible.")

    elif selected == "Finanzas":
        st.header("🏦 Finanzas y Contabilidad")
        st.info("🚧 Módulo en construcción. Pronto estará disponible.")

    elif selected == "Informes":
        st.header("📊 Informes de Gestión")
        st.info("🚧 Módulo en construcción. Pronto estará disponible.")