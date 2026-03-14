import streamlit as st
import pandas as pd

def mostrar_modulo_usuarios(supabase):
    st.header("👤 Gestión de Usuarios")
    
    # 1. CARGA DE DATOS (Centralizada)
    try:
        # Traemos datos y el nombre del rol desde la tabla relacionada
        res = supabase.table("usuarios").select("id, nombre, email, moneda, id_rol, roles(nombre_rol)").execute()
        df_raw = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        
        if not df_raw.empty:
            # Extraemos el nombre del rol de la respuesta anidada de Supabase
            df_raw['Rol'] = df_raw['roles'].apply(lambda x: x['nombre_rol'] if x else "Sin Rol")
            df_display = df_raw[["nombre", "email", "moneda", "Rol"]]
        else:
            df_display = pd.DataFrame(columns=["nombre", "email", "moneda", "Rol"])
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        df_raw = pd.DataFrame()

    tab1, tab2, tab3 = st.tabs(["📋 Directorio", "➕ Nuevo Usuario", "⚙️ Gestionar"])

    # --- TAB 1: DIRECTORIO Y REPORTES ---
    with tab1:
        col_t, col_r = st.columns([3, 1])
        with col_t:
            st.subheader("Directorio del Sistema")
        with col_r:
            # Reporte rápido en CSV
            csv = df_display.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar Reporte", data=csv, file_name='usuarios.csv', mime='text/csv')

        st.dataframe(df_display, use_container_width=True)

    # --- TAB 2: NUEVO USUARIO (CREATE) ---
    with tab2:
    st.subheader("Crear nuevo acceso")
    with st.form("form_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            n_nombre = st.text_input("Nombre Completo")
            n_email = st.text_input("Correo Electrónico")
        with col2:
            n_pass = st.text_input("Contraseña", type="password")
            n_moneda = st.selectbox("Moneda", ["COP", "USD", "ALL", "EUR"])
        
        # Selector de Rol
        n_rol = st.selectbox("Asignar Rol", 
                           options=[("Administrador", 1), ("Agente", 2), ("Consultor", 3)], 
                           format_func=lambda x: x[0])

        if st.form_submit_button("🚀 Registrar Usuario"):
            # --- 🛡️ ZONA DE VALIDACIÓN Y RE-APRENDIZAJE ---
            
            # 1. Quitamos espacios y estandarizamos
            email_limpio = n_email.strip().lower()
            nombre_limpio = n_nombre.strip().upper()

            # 2. Lógica de validación (El "Filtro")
            if not nombre_limpio or not email_limpio or not n_pass:
                st.error("⚠️ Todos los campos son obligatorios.")
            
            elif "@" not in email_limpio or "." not in email_limpio:
                # Aquí validamos que el correo parezca un correo
                st.error(f"❌ '{email_limpio}' no es un correo válido. Debe contener @ y un punto.")
            
            elif len(n_pass) < 4:
                st.error("⚠️ La contraseña debe tener al menos 4 caracteres.")
                
            else:
                # --- ✅ TODO OK: ENVIAR A SUPABASE ---
                try:
                    datos = {
                        "nombre": nombre_limpio,
                        "email": email_limpio,
                        "password": n_pass,
                        "moneda": n_moneda,
                        "id_rol": n_rol[1] 
                    }
                    supabase.table("usuarios").insert(datos).execute()
                    st.success(f"✅ ¡Usuario {nombre_limpio} creado con éxito!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error de base de datos: {e}")
    # --- TAB 3: GESTIONAR (UPDATE / DELETE) ---
    with tab3:
        st.subheader("Modificar o Eliminar")
        if not df_raw.empty:
            user_sel = st.selectbox("Seleccione un usuario para gestionar", options=df_raw['nombre'].tolist(), index=None)
            
            if user_sel:
                u_curr = df_raw[df_raw['nombre'] == user_sel].iloc[0]
                
                with st.expander(f"Editar datos de {user_sel}", expanded=True):
                    e_nombre = st.text_input("Editar Nombre", value=u_curr['nombre'])
                    e_moneda = st.selectbox("Editar Moneda", ["COP", "USD", "EUR", "ALL"], index=["COP", "USD", "EUR", "ALL"].index(u_curr['moneda']))
                    
                    c_up, c_de = st.columns(2)
                    with c_up:
                        if st.button("💾 Actualizar Datos"):
                            supabase.table("usuarios").update({"nombre": e_nombre, "moneda": e_moneda}).eq("id", u_curr['id']).execute()
                            st.success("Actualizado correctamente")
                            st.rerun()
                    with c_de:
                        if st.button("🗑️ Eliminar permanentemente", type="primary"):
                            supabase.table("usuarios").delete().eq("id", u_curr['id']).execute()
                            st.warning("Usuario eliminado")
                            st.rerun()
        else:
            st.info("No hay usuarios registrados para gestionar.")