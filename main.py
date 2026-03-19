import time
import streamlit as st
from streamlit_option_menu import option_menu
from supabase import create_client
import hashlib
from datetime import datetime
import propietarios_modulo 


# ==========================================
# FUNCIONES DE INTERFAZ Y SONIDO
# ==========================================
def emitir_beep_alerta():
    # Usamos time.time() para que Streamlit crea que es un código nuevo cada vez y SIEMPRE suene
    marca_tiempo = time.time() 
    beep_js = f"""
    <script>
        // Ejecución única: {marca_tiempo}
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        osc.type = 'triangle'; 
        osc.frequency.setValueAtTime(400, audioCtx.currentTime); 
        osc.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.2); 
    </script>
    """
    st.components.v1.html(beep_js, height=0)

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y VERSIÓN
# ==========================================
st.set_page_config(page_title="INMOLEASING WEB", layout="wide", page_icon="🏢")
APP_VERSION = "v5.0 GOLD" # Simetría absoluta en menú y foto perfecta

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

# ================================================
# 1.6 AJUSTES VISUALES CSS (PIXEL PERFECT EXTREMO)
# ===============================================
st.markdown("""
    <style>
        /* 1. Limpieza total de cabecera lateral */
        [data-testid="stSidebarHeader"] { padding: 0rem !important; margin: 0rem !important; height: 0px !important; min-height: 0px !important; }
        
        /* 2. Menú lateral: subimos el contenido */
        [data-testid="stSidebarUserContent"] { padding-top: 1rem !important; margin-top: -0.5rem !important; }
        
        /* 3. Panel principal: respiro superior */
        .block-container { padding-top: 3rem !important; }
        
        /* 4. Acompañar la subida de la línea acercando el botón Cerrar Sesión */
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
                # Sanitización de inputs
                email_limpio = email_input.lower()
                pass_hash = encriptar_password(pass_input)
                
                res = supabase.table("usuarios").select("*").eq("email", email_limpio).execute()
                
                if len(res.data) == 0:
                    st.error(f"❌ El correo '{email_limpio}' no existe.")
                else:
                    u_data = res.data[0]
                    estado = str(u_data.get('estado', '')).upper()
                    
                    if estado != 'ACTIVO':
                        st.error("❌ Usuario inactivo. Contacte al administrador.")
                        
                    elif u_data.get('password') != pass_hash:
                        st.error("❌ Contraseña incorrecta.")
                        
                    else:
                        id_rol = u_data.get('id_rol')
                        rol_nombre = "SIN ROL"
                        facs_texto = ""
                        
                        if id_rol:
                            res_r = supabase.table("roles").select("*").eq("id", id_rol).execute()
                            if res_r.data:
                                r_data = res_r.data[0]
                                facs_texto = str(r_data).upper()
                                rol_nombre = str(r_data.get('nombre_rol', r_data.get('nombre', 'ROL'))).upper()

                        u_data['rol_nombre'] = rol_nombre
                        u_data['facultades_texto'] = facs_texto
                        
                        st.session_state.autenticado = True
                        st.session_state.usuario = u_data
                        st.session_state.moneda_usuario = u_data.get('moneda', 'ALL')
                        
                        supabase.table("usuarios").update({"ultimo_acceso": datetime.utcnow().isoformat()}).eq("id", u_data['id']).execute()
                        st.rerun()
                        
            except Exception as e:
                st.error(f"Error de conexión: {e}")
                
    st.stop()

# ==========================================
# 6. MENÚ LATERAL (SIDEBAR)
# ==========================================
with st.sidebar:
    st.title("🏢 INMOLEASING")
    st.caption(f"Versión: {APP_VERSION}")
    
    st.write(f"👤 Hola, **{st.session_state.usuario.get('nombre')}**")
    st.caption(f"Región/Moneda: **{st.session_state.moneda_usuario}**")
    
    rol_actual = st.session_state.usuario.get('rol_nombre', 'SIN ROL')
    texto_facs = st.session_state.usuario.get('facultades_texto', '')
    
    st.caption(f"Perfil: **{rol_actual}**")
    
    # Línea superior (manteniendo la simetría base)
    st.markdown("<hr style='margin-top: 0; margin-bottom: 0;'>", unsafe_allow_html=True)

    st.session_state.opciones_permitidas = ["Inicio"]
    
    for item, fac in DICCIONARIO_MENU_FACULTADES.items():
        if fac in texto_facs or "ADMINISTRADOR" in rol_actual:
            st.session_state.opciones_permitidas.append(item)

    opciones = ["Inicio", "Dashboard", "Usuarios", "Operadores", "Propietarios", "Inmuebles", "Arrendamientos", "Finanzas", "Informes"]
    iconos = ["house", "speedometer2", "person-gear", "briefcase", "person-badge", "house-door", "file-earmark-check", "bank", "graph-up-arrow"]

    # Menú sin paddings internos extraños
    selected = option_menu(
        menu_title=None, 
        options=opciones, 
        icons=iconos, 
        menu_icon="cast", 
        default_index=0,
        styles={
            "container": {"padding": "0!important", "margin-top": "0!important", "margin-bottom": "0!important"}
        }
    )
    
    # LÍNEA INFERIOR REBELDE: Aumentamos la tracción a -45px y compensamos el espacio abajo con -20px
    st.markdown("<hr style='position: relative; top: -45px; margin-bottom: -20px;'>", unsafe_allow_html=True)
    
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

# ==========================================
# 7. ENRUTADOR PRINCIPAL
# ==========================================

if selected == "Inicio":
    st.title("🏢 INMOLEASING")
    st.markdown("**Bienvenido al Sistema Integral de Gestión Inmobiliaria.**")
    st.caption(f"Versión actual: {APP_VERSION}")
    
    st.write("") 
    
    # FOTO PERFECTA: Proporciones 1 - 2 - 1
    img_cols = st.columns([1, 2, 1]) 
    
    with img_cols[1]:
        try:
            st.image("portada.jpg", use_container_width=True)
        except:
            st.warning("Imagen 'portada.jpg' no encontrada.")
            
    st.write("") 
    st.info("👋 Selecciona una opción en el menú lateral para comenzar.")

elif selected not in st.session_state.opciones_permitidas:
    emitir_beep_alerta()
    st.error("### 🔒 Acceso Restringido")
    st.warning(f"Tu perfil (**{rol_actual}**) no tiene acceso a este módulo.")

else:
    # Bloques separados y con saltos de línea según estándar PEP 8
    
    if selected == "Dashboard":
        st.header("📈 Dashboard Principal")
        st.info("🚧 Módulo en construcción.")
        
    elif selected == "Usuarios":
        usuarios_modulo.mostrar_modulo_usuarios(supabase)
        
    elif selected == "Operadores":
        operadores_modulo.mostrar_modulo_operadores(supabase)
        
    elif selected == "Propietarios":  
        propietarios_modulo.mostrar_modulo_propietarios(supabase)    
        
    elif selected == "Inmuebles":
        st.header("🏠 Gestión de Inmuebles")
        st.info("🚧 Módulo en construcción.")
        
    elif selected == "Arrendamientos":
        st.header("📝 Arrendamientos")
        st.info("🚧 Módulo en construcción.")
        
    elif selected == "Finanzas":
        st.header("🏦 Finanzas y Contabilidad")
        st.info("🚧 Módulo en construcción.")
        
    elif selected == "Informes":
        st.header("📊 Informes de Gestión")
        st.info("🚧 Módulo en construcción.")