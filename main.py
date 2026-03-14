import streamlit as st
from streamlit_option_menu import option_menu

# Configuración de la página
st.set_page_config(page_title="INMOLEASING WEB", layout="wide")

# Función para mostrar el mensaje de "En construcción"
def mostrar_proximamente(modulo):
    st.warning(f"### 🚧 Módulo en Desarrollo")
    st.write(f"Muy pronto tendrás aquí toda la **gestión de {modulo.lower()}**.")
    st.info("Estamos trabajando para integrar las bases de datos y funciones de este apartado.")

# 1. MENÚ LATERAL
with st.sidebar:
    st.title("🏢 INMOLEASING")
    selected = option_menu(
        menu_title="Menú Principal",
        options=["Usuarios", "Propietarios", "Inmuebles", "Arrendamientos", "Bancos", "Informes"],
        icons=["person-gear", "person-badge", "house-door", "file-earmark-check", "bank", "graph-up-arrow"],
        menu_icon="cast",
        default_index=0,
    )

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