import streamlit as st
import pandas as pd
import re
from fpdf import FPDF

# ==========================================
# 0. FUNCIONES AUXILIARES Y LOGS
# ==========================================
def log_accion(supabase, usuario, accion, detalle):
    try:
        supabase.table("logs_actividad").insert({
            "usuario": usuario, 
            "accion": accion, 
            "detalle": detalle
        }).execute()
    except Exception as e:
        pass 

def es_correo_valido(correo):
    patron = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(patron, correo) is not None

LISTA_ICONOS = [
    '🏠', '🏢', '🏬', '🏗️', '🔑', '🚪', '🏘️', '🏭',
    '💰', '🏦', '🧾', '💲', '💳', '📈', '📉', '💸',
    '👥', '👤', '🤝', '👨‍💼', '👩‍💼', '👷', '🕵️', '🧑‍💻',
    '⚙️', '🛠️', '🔧', '🔒', '🔓', '🛡️', '✅', '❌', '🗑️', '✏️', '🔍',
    '🚰', '💡', '🔥', '⚡', '📊', '📑', '📄', '📅', '🚀', '🔔', '🌐', '📌'
]

# ==========================================
# 1. GENERADORES PDF (MÉTODO MILIMÉTRICO)
# ==========================================
def generar_pdf_usuarios(df, diccionario_roles):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "INMOLEASING - REPORTE DE USUARIOS", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(200, 220, 255)
    cw = [55, 70, 40, 25] # Ajustado para incluir Estado
    headers = ["NOMBRE", "EMAIL", "ROL", "ESTADO"]
    for i, h_text in enumerate(headers):
        pdf.cell(cw[i], 10, h_text, border=1, fill=True, align="C")
    pdf.ln()
    
    pdf.set_font("Arial", "", 9)
    for _, row in df.iterrows():
        rol_texto = diccionario_roles.get(row['id_rol'], "SIN ROL")
        estado_texto = str(row.get('estado', 'ACTIVO'))
        textos = [str(row['nombre']), str(row['email']), str(rol_texto), estado_texto]
        
        lineas_por_col = [len(pdf.multi_cell(cw[i], 7, txt, split_only=True)) for i, txt in enumerate(textos)]
        h_fila = 7 * max(lineas_por_col)
        
        x_ini, y_ini = pdf.get_x(), pdf.get_y()
        if y_ini + h_fila > 275:
            pdf.add_page()
            y_ini = pdf.get_y()

        x_actual = x_ini 
        for i, txt in enumerate(textos):
            pdf.set_xy(x_actual, y_ini)
            pdf.rect(x_actual, y_ini, cw[i], h_fila)
            pdf.multi_cell(cw[i], 7, txt, border=0, align='L')
            x_actual += cw[i] 
            
        pdf.set_xy(x_ini, y_ini + h_fila)
        
    return pdf.output(dest='S').encode('latin-1')

def generar_pdf_logs(df_logs):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "INMOLEASING - AUDITORIA DE SISTEMA", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 8)
    pdf.set_fill_color(220, 220, 220)
    cw = [25, 30, 30, 105] 
    headers = ["FECHA", "USUARIO", "ACCION", "DETALLE"]
    for i, h_text in enumerate(headers):
        pdf.cell(cw[i], 8, h_text, border=1, fill=True, align="C")
    pdf.ln()
    
    pdf.set_font("Arial", "", 7)
    for _, row in df_logs.iterrows():
        fecha_corta = str(row['fecha'])[:16] if pd.notnull(row['fecha']) else ""
        usr = str(row['usuario']) if pd.notnull(row['usuario']) else "SISTEMA"
        textos = [fecha_corta, usr, str(row['accion']), str(row['detalle'])]
        
        lineas_por_col = [len(pdf.multi_cell(cw[i], 5, txt, split_only=True)) for i, txt in enumerate(textos)]
        h_fila = 5 * max(lineas_por_col)
        
        x_ini, y_ini = pdf.get_x(), pdf.get_y()
        if y_ini + h_fila > 275:
            pdf.add_page()
            y_ini = pdf.get_y()

        x_actual = x_ini 
        for i, txt in enumerate(textos):
            pdf.set_xy(x_actual, y_ini)
            pdf.rect(x_actual, y_ini, cw[i], h_fila)
            pdf.multi_cell(cw[i], 5, txt, border=0, align='L')
            x_actual += cw[i] 
            
        pdf.set_xy(x_ini, y_ini + h_fila)
        
    return pdf.output(dest='S').encode('latin-1')


# ==========================================
# 2. MÓDULO PRINCIPAL
# ==========================================
def mostrar_modulo_usuarios(supabase):
    st.header("👤 Gestión de Usuarios y Accesos")
    usuario_actual = st.session_state.get("usuario_actual", "ADMINISTRADOR")
    
    try:
        res_roles = supabase.table("roles").select("*").execute()
        df_roles = pd.DataFrame(res_roles.data) if res_roles.data else pd.DataFrame()
        DICCIONARIO_ROLES = {rol['id']: rol['nombre_rol'] for rol in res_roles.data}
        
        res_fac = supabase.table("facultades").select("*").execute()
        df_fac = pd.DataFrame(res_fac.data) if res_fac.data else pd.DataFrame()
        if not df_fac.empty:
            df_fac = df_fac.sort_values('nombre_facultad')
        llaves_iconos = [f"{row['icono']} {row['nombre_facultad']}" for _, row in df_fac.iterrows()] if not df_fac.empty else []
    except:
        df_roles, df_fac, DICCIONARIO_ROLES, llaves_iconos = pd.DataFrame(), pd.DataFrame(), {}, []
        
    res_u = supabase.table("usuarios").select("*").execute()
    df_raw = pd.DataFrame(res_u.data) if res_u.data else pd.DataFrame()
    # Asegurarnos de que exista la columna estado localmente si la tabla está recién actualizada
    if not df_raw.empty and 'estado' not in df_raw.columns:
        df_raw['estado'] = 'ACTIVO'

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Directorio", "➕ Nuevo Usuario", "⚙️ Gestionar", "🛡️ Facultades y Roles", "📜 Logs de Actividad"])

    # --- TAB 1: DIRECTORIO ---
    with tab1:
        if not df_raw.empty:
            busqueda = st.text_input("🔍 Buscar usuario...", "").upper().strip()
            df_display = df_raw.copy().sort_values('nombre')
            df_display['Rol'] = df_display['id_rol'].map(DICCIONARIO_ROLES)
            
            # Mostramos el estado
            df_display['estado'] = df_display['estado'].fillna('ACTIVO')
            
            if busqueda:
                df_display = df_display[df_display['nombre'].str.contains(busqueda)]
            
            st.dataframe(df_display[["nombre", "email", "moneda", "Rol", "estado"]], use_container_width=True, hide_index=True)
            pdf_bytes = generar_pdf_usuarios(df_display, DICCIONARIO_ROLES)
            st.download_button("📄 Exportar Reporte PDF", pdf_bytes, "usuarios_inmoleasing.pdf", "application/pdf")

    # --- TAB 2: REGISTRO ---
    with tab2:
        st.subheader("Registrar Colaborador")
        with st.form("form_registro_estable"):
            col1, col2 = st.columns(2)
            n_nom = col1.text_input("Nombre Completo")
            n_ema = col1.text_input("Correo Institucional")
            n_pas = col2.text_input("Password", type="password")
            n_mon = col2.selectbox("Moneda Base", ["EUR", "COP", "ALL"])
            n_rol = st.selectbox("Rol Asignado", options=list(DICCIONARIO_ROLES.items()), format_func=lambda x: x[1])
            
            if st.form_submit_button("✅ Crear Usuario"):
                if n_nom and n_ema and n_pas:
                    if not es_correo_valido(n_ema):
                        st.error("❌ Formato de correo inválido.")
                    else:
                        supabase.table("usuarios").insert({
                            "nombre": n_nom.upper(), "email": n_ema.lower(), 
                            "password": n_pas, "moneda": n_mon, "id_rol": n_rol[0],
                            "estado": "ACTIVO" # Por defecto activo
                        }).execute()
                        log_accion(supabase, usuario_actual, "CREAR USUARIO", f"Registrado: {n_nom.upper()} | Rol ID: {n_rol[0]}")
                        st.success(f"¡Usuario {n_nom.upper()} creado!"); st.rerun()
                else:
                    st.warning("⚠️ Todos los campos son obligatorios.")

    # --- TAB 3: GESTIONAR (CON SOFT DELETE) ---
    with tab3:
        if not df_raw.empty:
            nombres_ordenados = df_raw.sort_values('nombre')['nombre'].tolist()
            u_edit = st.selectbox("Seleccione un usuario a gestionar (Autocomplete habilitado):", nombres_ordenados)
            u_data = df_raw[df_raw['nombre'] == u_edit].iloc[0]
            estado_actual = u_data.get('estado', 'ACTIVO')
            
            if estado_actual == 'INACTIVO':
                st.error(f"⚠️ El usuario {u_edit} está INACTIVO y no tiene acceso al sistema.")
            else:
                st.success(f"✅ El usuario {u_edit} está ACTIVO.")
            
            with st.form("form_edicion"):
                e_nom = st.text_input("Nombre", u_data['nombre'])
                e_ema = st.text_input("Email", u_data['email'])
                index_rol = list(DICCIONARIO_ROLES.keys()).index(u_data['id_rol']) if u_data['id_rol'] in DICCIONARIO_ROLES else 0
                e_rol = st.selectbox("Cambiar Rol", options=list(DICCIONARIO_ROLES.items()), index=index_rol, format_func=lambda x: x[1])
                
                if st.form_submit_button("💾 Guardar Cambios"):
                    if es_correo_valido(e_ema):
                        supabase.table("usuarios").update({
                            "nombre": e_nom.upper(), "email": e_ema.lower(), "id_rol": e_rol[0]
                        }).eq("id", u_data['id']).execute()
                        log_accion(supabase, usuario_actual, "EDITAR USUARIO", f"Actualizado: {e_nom.upper()}")
                        st.success("Cambios aplicados."); st.rerun()
                    else:
                        st.error("❌ Correo inválido.")
            
            st.markdown("---")
            if "confirmar_borrado_user" not in st.session_state:
                st.session_state.confirmar_borrado_user = None

            # Botón dinámico según el estado
            if estado_actual == 'ACTIVO':
                if st.button("🚫 Desactivar Usuario (Soft Delete)", type="primary"):
                    st.session_state.confirmar_borrado_user = u_data['id']
                    st.rerun()
            else:
                if st.button("♻️ Reactivar Usuario"):
                    supabase.table("usuarios").update({"estado": "ACTIVO"}).eq("id", u_data['id']).execute()
                    log_accion(supabase, usuario_actual, "REACTIVAR USUARIO", f"Acceso restaurado a: {u_edit}")
                    st.rerun()

            if st.session_state.confirmar_borrado_user == u_data['id']:
                st.warning(f"⚠️ ¿Desactivar a {u_edit}? Perderá acceso al sistema inmediatamente.")
                c_si, c_no = st.columns(2)
                if c_si.button("✅ Sí, Desactivar"):
                    # BORRADO LÓGICO: Solo actualizamos el estado
                    supabase.table("usuarios").update({"estado": "INACTIVO"}).eq("id", u_data['id']).execute()
                    log_accion(supabase, usuario_actual, "INACTIVAR USUARIO", f"Acceso bloqueado a: {u_edit}")
                    st.session_state.confirmar_borrado_user = None
                    st.rerun()
                if c_no.button("❌ Cancelar operación"):
                    st.session_state.confirmar_borrado_user = None
                    st.rerun()

    # --- TAB 4: ROLES Y FACULTADES ---
    with tab4:
        seccion = st.radio("Seleccione el paso a configurar:", ["1. Catálogo de Facultades", "2. Roles de Usuario"], horizontal=True)
        st.markdown("---")
        
        if seccion == "1. Catálogo de Facultades":
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.markdown("### ✨ Crear Facultad")
                with st.form("form_facultad"):
                    f_ico = st.selectbox("Selecciona un Icono", LISTA_ICONOS) 
                    f_nom = st.text_input("Nombre Técnico (Ej: REPORTE_PAGOS)")
                    if st.form_submit_button("Añadir Facultad"):
                        if f_nom:
                            supabase.table("facultades").insert({"icono": f_ico, "nombre_facultad": f_nom.upper()}).execute()
                            log_accion(supabase, usuario_actual, "CREAR FACULTAD", f"Facultad registrada: {f_nom.upper()}")
                            st.rerun()
            with col_f2:
                st.markdown("### ⚙️ Gestión de Facultades")
                if not df_fac.empty:
                    f_edit_nom = st.selectbox("Seleccione Facultad:", df_fac['nombre_facultad'].tolist())
                    f_row = df_fac[df_fac['nombre_facultad'] == f_edit_nom].iloc[0]
                    
                    with st.form("edit_facultad"):
                        idx_icono = LISTA_ICONOS.index(f_row['icono']) if f_row['icono'] in LISTA_ICONOS else 0
                        ef_ico = st.selectbox("Cambiar Icono", LISTA_ICONOS, index=idx_icono)
                        ef_nom = st.text_input("Cambiar Nombre", f_row['nombre_facultad'])
                        
                        if st.form_submit_button("💾 Actualizar Facultad"):
                            supabase.table("facultades").update({"icono": ef_ico, "nombre_facultad": ef_nom.upper()}).eq("id", f_row['id']).execute()
                            log_accion(supabase, usuario_actual, "EDITAR FACULTAD", f"Facultad modificada: {ef_nom.upper()}")
                            st.rerun()
                            
                    if "confirmar_borrado_fac" not in st.session_state:
                        st.session_state.confirmar_borrado_fac = None
                        
                    if st.button("🗑️ Eliminar Facultad"):
                        st.session_state.confirmar_borrado_fac = f_row['id']
                        st.rerun()
                        
                    if st.session_state.confirmar_borrado_fac == f_row['id']:
                        st.warning(f"⚠️ ¿Eliminar facultad {f_edit_nom}?")
                        cf_si, cf_no = st.columns(2)
                        if cf_si.button("✅ Sí, borrar facultad"):
                            supabase.table("facultades").delete().eq("id", f_row['id']).execute()
                            log_accion(supabase, usuario_actual, "ELIMINAR FACULTAD", f"Facultad borrada: {f_edit_nom}")
                            st.session_state.confirmar_borrado_fac = None
                            st.rerun()
                        if cf_no.button("❌ Cancelar"):
                            st.session_state.confirmar_borrado_fac = None
                            st.rerun()

        elif seccion == "2. Roles de Usuario":
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("### ✨ Crear Rol")
                with st.form("n_rol_form"):
                    nr_nom = st.text_input("Nombre del nuevo Rol (Ej: AUDITOR)")
                    nr_llaves = st.multiselect("Asignar Facultades:", llaves_iconos)
                    if st.form_submit_button("Guardar Nuevo Rol"):
                        if nr_nom:
                            supabase.table("roles").insert({"nombre_rol": nr_nom.upper(), "descripcion": ", ".join(nr_llaves)}).execute()
                            log_accion(supabase, usuario_actual, "CREAR ROL", f"Rol registrado: {nr_nom.upper()}")
                            st.rerun()
            with c2:
                st.markdown("### ⚙️ Gestión de Roles")
                if not df_roles.empty:
                    roles_ordenados = df_roles.sort_values('nombre_rol')['nombre_rol'].tolist()
                    r_edit = st.selectbox("Seleccione Rol a editar:", roles_ordenados)
                    r_row = df_roles[df_roles['nombre_rol'] == r_edit].iloc[0]
                    previas = [p.strip() for p in r_row['descripcion'].split(",")] if r_row['descripcion'] else []
                    
                    with st.form("e_rol_form"):
                        er_llaves = st.multiselect("Modificar Facultades:", llaves_iconos, default=[p for p in previas if p in llaves_iconos])
                        if st.form_submit_button("Actualizar Rol"):
                            supabase.table("roles").update({"descripcion": ", ".join(er_llaves)}).eq("id", r_row['id']).execute()
                            log_accion(supabase, usuario_actual, "EDITAR ROL", f"Facultades actualizadas para el rol: {r_edit}")
                            st.success("Permisos actualizados."); st.rerun()

                    if "confirmar_borrado_rol" not in st.session_state:
                        st.session_state.confirmar_borrado_rol = None
                        
                    if st.button("🗑️ Eliminar este Rol"):
                        st.session_state.confirmar_borrado_rol = r_row['id']
                        st.rerun()
                        
                    if st.session_state.confirmar_borrado_rol == r_row['id']:
                        st.warning(f"⚠️ ¿Seguro que deseas eliminar el rol {r_edit}?")
                        c_si_rol, c_no_rol = st.columns(2)
                        if c_si_rol.button("✅ Sí, eliminar Rol"):
                            supabase.table("roles").delete().eq("id", r_row['id']).execute()
                            log_accion(supabase, usuario_actual, "ELIMINAR ROL", f"Rol borrado: {r_edit}")
                            st.session_state.confirmar_borrado_rol = None
                            st.rerun()
                        if c_no_rol.button("❌ Cancelar"):
                            st.session_state.confirmar_borrado_rol = None
                            st.rerun()

    # --- TAB 5: LOGS Y AUDITORÍA ---
    with tab5:
        st.subheader("📜 Auditoría y Registro de Actividades")
        
        try:
            res_logs = supabase.table("logs_actividad").select("*").order("fecha", desc=True).execute()
            df_logs = pd.DataFrame(res_logs.data) if res_logs.data else pd.DataFrame()
        except:
            df_logs = pd.DataFrame()

        if not df_logs.empty:
            df_logs['fecha'] = pd.to_datetime(df_logs['fecha']).dt.tz_localize(None)

            col_f1, col_f2, col_f3 = st.columns([1, 1, 1])
            
            with col_f1:
                fecha_rango = st.date_input("Rango de Fechas", value=[])
            with col_f2:
                usuarios_unicos = ["Todos"] + sorted(df_logs['usuario'].dropna().unique().tolist())
                usuario_filtro = st.selectbox("Filtrar por Usuario", usuarios_unicos)
            with col_f3:
                txt_filtro = st.text_input("Buscar texto libre:", "").upper()

            df_logs_filtrado = df_logs.copy()
            
            if len(fecha_rango) == 2:
                df_logs_filtrado = df_logs_filtrado[
                    (df_logs_filtrado['fecha'].dt.date >= fecha_rango[0]) & 
                    (df_logs_filtrado['fecha'].dt.date <= fecha_rango[1])
                ]
                
            if usuario_filtro != "Todos":
                df_logs_filtrado = df_logs_filtrado[df_logs_filtrado['usuario'] == usuario_filtro]
            
            if txt_filtro:
                mask_accion = df_logs_filtrado['accion'].str.contains(txt_filtro, case=False, na=False)
                mask_detalle = df_logs_filtrado['detalle'].str.contains(txt_filtro, case=False, na=False)
                df_logs_filtrado = df_logs_filtrado[mask_accion | mask_detalle]

            df_visual = df_logs_filtrado.copy()
            if not df_visual.empty:
                df_visual['fecha'] = df_visual['fecha'].dt.strftime('%Y-%m-%d %H:%M')
                st.dataframe(df_visual[['fecha', 'usuario', 'accion', 'detalle']], use_container_width=True, hide_index=True)

                pdf_logs_bytes = generar_pdf_logs(df_visual)
                st.download_button("📄 Descargar Auditoría PDF", pdf_logs_bytes, "auditoria.pdf", "application/pdf")
            else:
                st.info("No hay registros con esos filtros.")
        else:
            st.info("El registro de actividades está vacío.")