import streamlit as st
import pandas as pd
from fpdf import FPDF

# ==========================================
# 1. FUNCIÓN PARA GENERAR EL REPORTE PDF
# ==========================================
def generar_pdf_usuarios(df, diccionario_roles):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "INMOLEASING - REPORTE DE USUARIOS", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(60, 10, "NOMBRE", border=1, fill=True)
    pdf.cell(70, 10, "EMAIL", border=1, fill=True)
    pdf.cell(50, 10, "ROL", border=1, fill=True)
    pdf.ln()
    pdf.set_font("Arial", "", 9)
    for _, row in df.iterrows():
        rol_texto = diccionario_roles.get(row['id_rol'], "SIN ROL")
        pdf.cell(60, 10, str(row['nombre']), border=1)
        pdf.cell(70, 10, str(row['email']), border=1)
        pdf.cell(50, 10, str(rol_texto), border=1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 2. MÓDULO PRINCIPAL DE USUARIOS
# ==========================================
def mostrar_modulo_usuarios(supabase):
    st.header("👤 Gestión de Usuarios")
    
    # 1. Carga Dinámica de Roles y Descripciones (para el expander)
    try:
        # Traemos también la descripción del rol
        res_roles = supabase.table("roles").select("id, nombre_rol, descripcion").execute()
        DICCIONARIO_ROLES = {rol['id']: rol['nombre_rol'] for rol in res_roles.data}
        DICCIONARIO_DESC = {rol['id']: rol['descripcion'] for rol in res_roles.data}
    except Exception as e:
        st.error(f"Error al cargar roles: {e}")
        DICCIONARIO_ROLES, DICCIONARIO_DESC = {}, {}
        
    # 2. Carga y Orden de Usuarios (A-Z) [Mejora 1]
    res = supabase.table("usuarios").select("id, nombre, email, moneda, id_rol").execute()
    df_raw = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    
    if not df_raw.empty:
        # Ordenamos alfabéticamente de menor a mayor (A-Z)
        df_raw = df_raw.sort_values(by='nombre', ascending=True)

    tab1, tab2, tab3 = st.tabs(["📋 Directorio", "➕ Nuevo Usuario", "⚙️ Gestionar"])

    # --- TAB 1: DIRECTORIO CON BÚSQUEDA Y EXPANSIÓN 👤 ---
    with tab1:
        if not df_raw.empty:
            # MEJORA 3: BUSCADOR
            # Nota: Usamos st.session_state para mantener la búsqueda si se refresca la página
            if 'busqueda_usuarios' not in st.session_state:
                st.session_state['busqueda_usuarios'] = ""
                
            col_b, col_empty = st.columns([2, 2])
            with col_b:
                busqueda = st.text_input("Buscar usuario por nombre...", key='input_busqueda').upper().strip()
            
            df_display = df_raw.copy()
            df_display['Rol'] = df_display['id_rol'].map(DICCIONARIO_ROLES)
            
            # Aplicar filtro de búsqueda si hay texto
            if busqueda:
                df_display = df_display[df_display['nombre'].str.contains(busqueda)]
            
            st.dataframe(df_display[["nombre", "email", "moneda", "Rol"]], use_container_width=True)
            
            # MEJORA 4: AMPLIACIÓN DE INFORMACIÓN (LUPA) 👤
            # Usamos el icono👤 para que encaje con tu menú lateral
            with st.expander("👤 Ver Detalle de Permisos por Usuario", expanded=False):
                # Usamos los nombres ya ordenados alfabéticamente
                nombres_ordenados = df_display['nombre'].tolist()
                
                # Para el selectbox del expander, si no hay resultados, mostramos un mensaje claro
                if nombres_ordenados:
                    u_detalle = st.selectbox("Seleccione un usuario para ver sus permisos detallados", nombres_ordenados)
                    
                    if u_detalle:
                        row_u = df_display[df_display['nombre'] == u_detalle].iloc[0]
                        desc_rol = DICCIONARIO_DESC.get(row_u['id_rol'], "Sin descripción disponible.")
                        st.info(f"**Rol Asignado:** {row_u['Rol']}\n\n**Descripción detallada de permisos en el sistema:** {desc_rol}")
                else:
                    st.warning("No hay usuarios para mostrar el detalle (aplique otro filtro de búsqueda).")
            
            # Botón de descarga PDF
            pdf_bytes = generar_pdf_usuarios(df_display, DICCIONARIO_ROLES)
            st.download_button("📄 Descargar Reporte PDF", pdf_bytes, "reporte_usuarios.pdf", "application/pdf")
        else:
            st.info("No hay usuarios registrados aún.")

    # --- TAB 2: REGISTRO CON VALIDACIÓN ---
    with tab2:
        st.subheader("Crear nueva cuenta")
        # Formulario estándar, mantiene los datos si hay error
        with st.form("form_registro"):
            c1, c2 = st.columns(2)
            with c1:
                n_nombre = st.text_input("Nombre Completo")
                n_email = st.text_input("Correo Electrónico")
            with c2:
                n_pass = st.text_input("Contraseña Temporal", type="password")
                n_moneda = st.selectbox("Moneda Base", ["COP", "USD", "EUR", "ALL"])
            
            opciones_rol = list(DICCIONARIO_ROLES.items()) 
            if opciones_rol:
                n_rol_sel = st.selectbox("Asignar Rol", options=opciones_rol, format_func=lambda x: x[1])
            else:
                st.warning("No hay roles configurados en la base de datos.")
                n_rol_sel = None

            if st.form_submit_button("🚀 Registrar Usuario"):
                if not n_rol_sel:
                    st.error("No se puede registrar usuarios sin roles disponibles.")
                else:
                    # Limpieza de datos
                    nombre_final = n_nombre.strip().upper()
                    email_final = n_email.strip().lower()

                    # Validaciones básicas
                    if not n_nombre or not n_email or not n_pass:
                        st.error("⚠️ Nombre, Email y Contraseña son obligatorios.")
                    elif "@" not in email_final or "." not in email_final:
                        st.error("❌ El correo electrónico no tiene un formato válido.")
                    elif len(n_pass) < 4:
                        st.error("❌ La contraseña debe tener al menos 4 caracteres.")
                    else:
                        try:
                            supabase.table("usuarios").insert({
                                "nombre": nombre_final,
                                "email": email_final,
                                "password": n_pass,
                                "moneda": n_moneda,
                                "id_rol": n_rol_sel[0] # Guardamos el ID numérico
                            }).execute()
                            st.success(f"✅ Usuario {nombre_final} creado correctamente.")
                            st.rerun() # Solo reinicia si tuvo éxito
                        except Exception as e:
                            st.error(f"Error al guardar en base de datos: {e}")

    # --- TAB 3: GESTIONAR (CRUD COMPLETO: EDITAR Y ELIMINAR) ---
    with tab3:
        if not df_raw.empty:
            st.subheader("Modificar o Eliminar Cuenta")
            
            # MEJORA 2: Selección directa, sin el "----"
            # La lista ya está ordenada A-Z por la carga inicial
            lista_nombres_az = df_raw['nombre'].tolist()
            u_sel_nombre = st.selectbox("Seleccione el usuario a gestionar", options=lista_nombres_az)
            
            # Obtener datos actuales del usuario elegido
            datos_u = df_raw[df_raw['nombre'] == u_sel_nombre].iloc[0]
            
            # Formulario de edición
            st.markdown("---")
            with st.form("form_edicion"):
                ce1, ce2 = st.columns(2)
                with ce1:
                    edit_nom = st.text_input("Nombre Completo", value=datos_u['nombre'])
                    edit_ema = st.text_input("Correo Electrónico", value=datos_u['email'])
                with ce2:
                    # Pre-seleccionar la moneda actual
                    edit_mon = st.selectbox("Moneda Base", ["COP", "USD", "EUR", "ALL"], 
                                           index=["COP", "USD", "EUR", "ALL"].index(datos_u['moneda']))
                    
                    # Pre-seleccionar el rol actual
                    ids_posibles_roles = list(DICCIONARIO_ROLES.keys())
                    try:
                        idx_rol_actual = ids_posibles_roles.index(datos_u['id_rol'])
                    except ValueError:
                        idx_rol_actual = 0
                    
                    edit_rol = st.selectbox("Cambiar Rol", options=list(DICCIONARIO_ROLES.items()), 
                                           index=idx_rol_actual,
                                           format_func=lambda x: x[1])
                
                if st.form_submit_button("💾 Guardar Cambios"):
                    # Validaciones básicas
                    nombre_edit = edit_nom.strip().upper()
                    email_edit = edit_ema.strip().lower()
                    
                    if not nombre_edit or not email_edit:
                        st.error("Nombre y Email son obligatorios.")
                    elif "@" not in email_edit or "." not in email_edit:
                        st.error("Formato de correo inválido.")
                    else:
                        try:
                            supabase.table("usuarios").update({
                                "nombre": nombre_edit,
                                "email": email_edit,
                                "moneda": edit_mon,
                                "id_rol": edit_rol[0]
                            }).eq("id", datos_u['id']).execute()
                            st.success("✅ Cambios guardados correctamente.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al actualizar: {e}")
            
            st.markdown("### Zona de Peligro")
            if st.button(f"🗑️ Eliminar permanentemente a {u_sel_nombre}", type="primary"):
                try:
                    supabase.table("usuarios").delete().eq("id", datos_u['id']).execute()
                    st.success("Usuario eliminado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo eliminar el usuario: {e}")
        else:
            st.info("No hay usuarios registrados aún.")