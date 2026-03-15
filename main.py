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

APP_VERSION = "v1.6.2" # Matriz de Facultades y Permisos Dinámicos

# ==========================================
# 1.5 MATRIZ DE FACULTADES (PERMISOS POR ROL)
# ==========================================
# Aquí definimos exactamente qué opciones del menú puede ver cada rol.
# Los nombres aquí DEBEN coincidir con los nombres que creaste en la tabla 'roles' de Supabase.
MAPA_FACULTADES = {
    "ADMINISTRADOR": [
        "Dashboard", "Usuarios", "Operadores", "Propietarios", 
        "Inmuebles", "Arrendamientos", "Finanzas", "Informes"
    ],
    "LECTOR": [
        "Dashboard", "Propietarios", "Inmuebles", "Informes"
    ],
    "SECRETARIA": [
        "Dashboard", "Operadores", "Propietarios", "Inmuebles", "Arrendamientos", "Informes"
    ]
}

# Modulos que SIEMPRE se muestran, sin importar el rol (por si acaso el rol falla)
FACULTADES_POR_DEFECTO = ["Dashboard"]

# ==========================================
# 1.6 AJUSTES VISUALES (CSS MODIFICADO)
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
                
                res = supabase.table("usuarios").select("*").eq("email", email_limpio).execute()
                
                if len(res.data) == 0:
                    st.error(f"❌ No se encontró el correo: '{email_limpio}'")
                else:
                    usuario_data = res.data[0]
                    estado_db = str(usuario_data.get('estado', '')).strip().upper()
                    pass_db = str(usuario_data.get('password', '')).strip()
                    
                    if estado_db != 'ACTIVO':
                        st.error(f"❌ Cuenta encontrada, pero su estado es: '{estado_db}'")
                    elif pass_db != pass_hash:
                        st.error("❌ La contraseña no coincide.")
                    else:
                        # Buscamos la Facultad/Rol real usando el id_rol
                        id_rol = usuario_data.get('id_rol')
                        rol_nombre = "SIN ROL"
                        
                        if id_rol:
                            try:
                                res_rol = supabase.table("roles").select("nombre").eq("id", id_rol).execute()
                                if len(res_rol.data) > 0:
                                    rol_nombre = str(res_rol.data[0]['nombre']).strip().upper()
                            except Exception as e:
                                print(f"Error buscando el rol: {e}")
                        
                        usuario_data['rol_nombre'] = rol_nombre

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
# 6. MENÚ LATERAL Y NAVEGACIÓN DINÁMICA
# ==========================================
def mostrar_proximamente(modulo):
    st.warning(f"### 🚧 Módulo en Desarrollo")
    st.write(f"Muy pronto tendrás aquí toda la **gestión de {modulo.lower()}**.")

with st.sidebar:
    st.title("🏢 INMOLEASING")
    st.write(f"👤 Hola, **{st.session_state.usuario.get('nombre', 'Usuario')}**")
    st.caption(f"Región/Moneda: **{st.session_state.get('moneda_usuario', 'ALL')}**")
    
    rol_usuario = st.session_state.usuario.get('rol_nombre', 'SIN ROL')
    st.caption(f"Facultad/Rol: **{rol_usuario}**")
    st.caption(f"Versión: {APP_VERSION}")

    # Consultamos la Matriz de Facultades para ver qué opciones tiene permitidas este rol
    modulos_permitidos = MAPA_FACULTADES.get(rol_usuario, FACULTADES_POR_DEFECTO)

    # Definimos la estructura base total
    menu_completo = [
        {"nombre": "Dashboard", "icono": "speedometer2"},
        {"nombre": "Usuarios", "icono": "person-gear"},
        {"nombre": "Operadores", "icono": "briefcase"},
        {"nombre": "Propietarios", "icono": "person-badge"},
        {"nombre": "Inmuebles", "icono": "house-door"},
        {"nombre": "Arrendamientos", "icono": "file-earmark-check"},
        {"nombre": "Finanzas", "icono": "bank"},
        {"nombre": "Informes", "icono": "graph-up-arrow"}
    ]

    # Filtramos: Solo agregamos al menú si el nombre del módulo está en la lista de permitidos
    menu_final_opciones = []
    menu_final_iconos = []

    for item in menu_completo:
        if item["nombre"] in modulos_permitidos:
            menu_final_opciones.append(item["nombre"])
            menu_final_iconos.append(item["icono"])

    selected = option_menu(
        menu_title="Menú Principal",
        options=menu_final_opciones, 
        icons=menu_final_iconos,     
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
# 7. ENRUTADOR DE MÓDULOS BLINDADO
# ==========================================
rol_usuario_enrutador = st.session_state.usuario.get('rol_nombre', 'SIN ROL')
modulos_permitidos_enrutador = MAPA_FACULTADES.get(rol_usuario_enrutador, FACULTADES_POR_DEFECTO)

# DOBLE CANDADO: Verificamos que lo que intentan abrir realmente esté en sus facultades
if selected in modulos_permitidos_enrutador:

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

else:
    # Si alguien burla el menú e intenta cargar un módulo por fuerza bruta:
    st.error(f"🚫 Acceso denegado. Tu rol de '{rol_usuario_enrutador}' no tiene facultades para ver el módulo: {selected}.")