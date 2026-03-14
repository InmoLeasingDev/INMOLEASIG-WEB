import streamlit as st
import pandas as pd

def mostrar_modulo_usuarios(supabase):
    st.header("👤 Gestión de Usuarios")
    
    # 1. CARGA DE DATOS (Centralizada para que todas las pestañas la usen)
    try:
        # Traemos también el ID para poder editar/borrar
        res = supabase.table("usuarios").select("id, nombre, email, moneda, roles(nombre_rol), password").execute()
        df_raw = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        
        if not df_raw.empty:
            # Limpiamos el nombre del rol que viene anidado
            df_raw['Rol'] = df_raw['roles'].apply(lambda x: x['nombre_rol'] if x else "Sin Rol")
            df_display = df_raw[["id", "nombre", "email", "moneda", "Rol"]]
        else:
            df_display = pd.DataFrame(columns=["id", "nombre", "email", "moneda", "Rol"])
    except Exception as e:
        st.error(f"Error al cargar usuarios: {e}")
        df_raw = pd.DataFrame()

    tab1, tab2, tab3 = st.tabs(["📋 Directorio", "➕ Nuevo Usuario", "⚙️ Gestionar"])

    # --- TAB 1: DIRECTORIO Y REPORTES ---
    with tab1:
        col_title, col_btn = st.columns([3, 1])
        with col_title:
            st.subheader("Directorio de Usuarios")
        with col_btn:
            # Botón para descargar reporte en CSV (Abrible en Excel)
            csv = df_display.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar Reporte",
                data=csv,
                file_name='directorio_usuarios.csv',
                mime='text/csv',
            )

        st.dataframe(df_display.drop(columns=["id"]), use_container_width=True)
        st.caption(f"Total de usuarios registrados: {len(df_display)}")

    # --- TAB 2: NUEVO USUARIO (CREATE) ---
    with tab2:
        st.subheader("Crear nuevo acceso")
        with st.form("form_registro", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nuevo_nombre = st.text_input("Nombre Completo")
                nuevo_email = st.text_input("Correo Electrónico")
            with col2:
                nuevo_pass = st.text_input("Contraseña", type="password")
                nuevo_moneda = st.selectbox("Moneda", ["COP", "USD", "ALL"])
            
            # Nota: Aquí asumo que tienes IDs de roles 1, 2, 3... 
            # Lo ideal sería cargar los roles de la base de datos
            nuevo_rol_id = st.number_input("ID de Rol (1: Admin, 2: Agente)", min_value=1, value=2)

            if st.form_submit_button("🚀 Registrar Usuario"):
                if nuevo_nombre and nuevo_email and nuevo_pass:
                    datos = {
                        "nombre": nuevo_nombre,
                        "email": nuevo_email,
                        "password": nuevo_pass,
                        "moneda": nuevo_moneda,
                        "role_id": nuevo_rol_id # Verifica que este nombre de columna sea correcto
                    }
                    try:
                        supabase.table("usuarios").insert(datos).execute()
                        st.success(f"Usuario {nuevo_nombre} creado correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al insertar: {e}")
                else:
                    st.warning("Por favor rellena los campos obligatorios.")

    # --- TAB 3: GESTIONAR (UPDATE / DELETE) ---
    with tab3:
        st.subheader("Modificar o Eliminar")
        if not df_raw.empty:
            usuario_sel = st.selectbox("Seleccione un usuario para editar", 
                                      options=df_raw['nombre'].tolist(),
                                      index=None,
                                      placeholder="Busca un nombre...")
            
            if usuario_sel:
                datos_actuales = df_raw[df_raw['nombre'] == usuario_sel].iloc[0]
                
                with st.expander(f"Editando a: {usuario_sel}", expanded=True):
                    edit_nombre = st.text_input("Nombre", value=datos_actuales['nombre'])
                    edit_email = st.text_input("Email", value=datos_actuales['email'])
                    edit_moneda = st.selectbox("Moneda", ["COP", "USD", "ALL"], 
                                             index=["COP", "USD", "ALL"].index(datos_actuales['moneda']))
                    
                    col_edit, col_del = st.columns(2)
                    
                    with col_edit:
                        if st.button("💾 Guardar Cambios"):
                            try:
                                supabase.table("usuarios").update({
                                    "nombre": edit_nombre,
                                    "email": edit_email,
                                    "moneda": edit_moneda
                                }).eq("id", datos_actuales['id']).execute()
                                st.success("Actualizado con éxito")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                                
                    with col_del:
                        if st.button("🗑️ Eliminar Usuario", type="primary"):
                            try:
                                supabase.table("usuarios").delete().eq("id", datos_actuales['id']).execute()
                                st.warning("Usuario eliminado")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
        else:
            st.info("No hay usuarios para gestionar.")