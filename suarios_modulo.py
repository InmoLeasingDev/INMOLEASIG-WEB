import streamlit as st
import pandas as pd

def mostrar_modulo_usuarios(supabase):
    st.header("👤 Gestión de Usuarios")
    
    tab1, tab2, tab3 = st.tabs(["📋 Directorio", "➕ Nuevo Usuario", "⚙️ Gestionar"])

    with tab1:
        # Aquí pegas el código del Directorio que vimos antes
        res = supabase.table("usuarios").select("nombre, email, moneda, roles(nombre_rol)").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['Rol'] = df['roles'].apply(lambda x: x['nombre_rol'] if x else "Sin Rol")
            st.dataframe(df[["nombre", "email", "moneda", "Rol"]], use_container_width=True)

    with tab2:
        # Aquí pegas el código del Formulario de Nuevo Usuario
        st.subheader("Crear nuevo acceso")
        # ... (el resto del código del formulario)