import streamlit as st
from supabase import create_client

# --- 1. CONFIGURACIÓN Y ESTÉTICA ---
st.set_page_config(page_title="Mi App", layout="wide")

# --- 2. FUNCIÓN PARA CONECTAR (Igual a tu imagen) ---
@st.cache_resource
def get_supabase_client():
    url = st.secrets["connections"]["supabase"]["url"]
    key = st.secrets["connections"]["supabase"]["key"]
    return create_client(url, key)

conn = get_supabase_client()

# --- 3. CONTROL DE ACCESO ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# --- 4. LÓGICA DE LOGIN ---
if not st.session_state.autenticado:
    st.title("Inicia sesión para continuar")
    
    email_input = st.text_input("Email")
    password_input = st.text_input("Password", type="password")
    
    if st.button("Conectar"):
        # Tu consulta original corregida con .execute()
        res = conn.table("usuarios").select("*").eq("email", email_input).eq("password", password_input).execute()
        
        if len(res.data) > 0:
            st.session_state.autenticado = True
            st.rerun() # Esto hace que desaparezca el login y aparezca el menú
        else:
            st.error("Datos incorrectos")

# --- 5. MENÚS Y CONTENIDO (Esto es lo que "no veías") ---
else:
    # Creamos la barra lateral para los menús
    with st.sidebar:
        st.header("Menú de Navegación")
        menu = st.radio("Ir a:", ["Dashboard", "Inventario", "Reportes"])
        
        st.divider()
        if st.button("Salir"):
            st.session_state.autenticado = False
            st.rerun()

    # Contenido según el menú seleccionado
    if menu == "Dashboard":
        st.title("📊 Panel Principal")
        st.write("Aquí verás tus métricas principales.")
        
    elif menu == "Inventario":
        st.title("📦 Gestión de Inventario")
        st.write("Aquí puedes ver tus productos en Supabase.")
        
    elif menu == "Reportes":
        st.title("📄 Reportes Mensuales")
        st.write("Generación de documentos PDF o Excel.")