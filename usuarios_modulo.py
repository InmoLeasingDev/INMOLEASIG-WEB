import streamlit as st
import pandas as pd
from fpdf import FPDF

def mostrar_modulo_usuarios(supabase):
    st.header("👤 Gestión de Usuarios")
    
    # --- CARGA DINÁMICA DE ROLES ---
    try:
        res_roles = supabase.table("roles").select("id, nombre_rol").execute()
        DICCIONARIO_ROLES = {rol['id']: rol['nombre_rol'] for rol in res_roles.data}
    except Exception as e:
        st.error(f"Error al cargar roles: {e}")
        DICCIONARIO_ROLES = {}
        
    # --- CARGA DE DATOS DE USUARIOS ---
    res = supabase.table("usuarios").select("id, nombre, email, moneda, id_rol").execute()
    df_raw = pd.DataFrame(res.data) if res.data else pd.DataFrame()

    tab1, tab2, tab3 = st.tabs(["📋 Directorio", "➕ Nuevo Usuario", "⚙️ Gestionar"])

    # --- TAB 1 y TAB 2 (Se mantienen igual que antes) ---
    with tab1:
        if not df_raw.empty:
            df_ver = df_raw.copy()
            df_ver['Rol'] = df_ver['id_rol'].map(DICCIONARIO_ROLES)
            st.dataframe(df_ver[["nombre", "email", "moneda", "Rol"]], use_container_width=True)
            pdf_bytes = generar_pdf_usuarios(df_raw, DICCIONARIO_ROLES)
            st.download_button("📄 Descargar Reporte PDF", pdf_bytes, "reporte_usuarios.pdf", "application/pdf")

    with tab2:
        st.subheader("Crear nueva cuenta")
        with st.form("form_registro"):
            col1, col2 = st.columns(2)
            with col1:
                n_nombre = st.text_input("Nombre Completo")
                n_email = st.text_input("Correo Electrónico")
            with col2:
                n_pass = st.text_input("Contraseña Temporal", type="password")
                n_moneda = st.selectbox("Moneda", ["COP", "USD", "EUR", "ALL"])
            
            opciones_rol = list(DICCIONARIO_ROLES.items()) 
            n_rol_sel = st.selectbox("Asignar Rol", options=opciones_rol, format_func=lambda x: x[1])

            if st.form_submit_button("🚀 Registrar Usuario"):
                if n_nombre and n_email:
                    try:
                        supabase.table("usuarios").insert({
                            "nombre": n_nombre.strip().upper(),
                            "email": n_email.strip().lower(),
                            "password": n_pass,
                            "moneda": n_moneda,
                            "id_rol": n_rol_sel[0]
                        }).execute()
                        st.success("¡Usuario creado!")
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

    # --- TAB 3: GESTIONAR (CRUD COMPLETO: EDITAR Y ELIMINAR) ---
    with tab3:
        if not df_raw.empty:
            st.subheader("Modificar o Eliminar Usuario")
            
            # 1. Seleccionar Usuario
            user_nombres = df_raw['nombre'].tolist()
            u_seleccionado = st.selectbox("Seleccione el usuario a gestionar", ["---"] + user_nombres)
            
            if u_seleccionado != "---":
                # Obtener datos actuales del usuario elegido
                datos_u = df_raw[df_raw['nombre'] == u_seleccionado].iloc[0]
                u_id = datos_u['id']
                
                # 2. Formulario de Edición
                st.markdown("---")
                st.info(f"Editando a: **{u_seleccionado}**")
                
                with st.form("form_edicion"):
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        edit_nom = st.text_input("Nombre Completo", value=datos_u['nombre'])
                        edit_ema = st.text_input("Correo Electrónico", value=datos_u['email'])
                    with col_e2:
                        edit_mon = st.selectbox("Moneda", ["COP", "USD", "EUR", "ALL"], 
                                               index=["COP", "USD", "EUR", "ALL"].index(datos_u['moneda']))
                        
                        # Buscamos el índice actual del rol para el selectbox
                        lista_ids_roles = list(DICCIONARIO_ROLES.keys())
                        try:
                            indice_rol = lista_ids_roles.index(datos_u['id_rol'])
                        except:
                            indice_rol = 0
                            
                        edit_rol = st.selectbox("Cambiar Rol", 
                                               options=list(DICCIONARIO_ROLES.items()), 
                                               index=indice_rol,
                                               format_func=lambda x: x[1])

                    c1, c2 = st.columns(2)
                    with c1:
                        btn_update = st.form_submit_button("💾 Guardar Cambios", use_container_width=True)
                    with c2:
                        # El botón de eliminar lo ponemos fuera del form de edición por seguridad
                        pass
                
                # 3. Lógica de Actualización
                if btn_update:
                    try:
                        supabase.table("usuarios").update({
                            "nombre": edit_nom.strip().upper(),
                            "email": edit_ema.strip().lower(),
                            "moneda": edit_mon,
                            "id_rol": edit_rol[0]
                        }).eq("id", u_id).execute()
                        st.success("✅ ¡Datos actualizados!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al actualizar: {e}")
                
                # 4. Botón de Eliminar (Separado y con advertencia)
                st.markdown("### Zona de Peligro")
                if st.button(f"🗑️ Eliminar a {u_seleccionado} permanentemente", type="primary"):
                    try:
                        supabase.table("usuarios").delete().eq("id", u_id).execute()
                        st.success("Usuario eliminado.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"No se pudo eliminar: {e}")
        else:
            st.info("No hay usuarios para gestionar.")