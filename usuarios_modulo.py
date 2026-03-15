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
    '🚰', '💡', '🔥', '⚡', '📊', '📑', '📄', '📅', '🚀', '🔔', '🌐', '📌', '📝'
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
    cw = [55, 70, 40, 25] 
    headers = ["NOMBRE", "EMAIL", "ROL", "ESTADO"]
    for i, h_text in enumerate(headers):
        pdf.cell(cw[i], 10, h_text, border=1, fill=True, align="C")
    pdf.ln()
    
    pdf.set_font("Arial", "", 9)
    for _, row in df.iterrows():
        rol_texto = diccionario_roles.get(row['id_rol'], "SIN ROL")
        estado_texto = str(row.get('estado', 'ACTIVO'))
        textos = [str(row['NOMBRE']), str(row['EMAIL']), str(rol_texto), estado_texto]
        
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

def generar_pdf_usuarios_detallado(df, diccionario_roles, diccionario_desc):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "INMOLEASING - USUARIOS Y FACULTADES", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(200, 220, 255)
    cw = [40, 35, 115] # Total 190mm
    headers = ["NOMBRE", "ROL", "FACULTADES ASIGNADAS"]
    for i, h_text in enumerate(headers):
        pdf.cell(cw[i], 8, h_text, border=1, fill=True, align="C")
    pdf.ln()
    
    pdf.set_font("Arial", "", 8)
    for _, row in df.iterrows():
        rol_texto = diccionario_roles.get(row['id_rol'], "SIN ROL")
        facs_raw = diccionario_desc.get(row['id_rol'], "")
        
        # Formateamos como lista para el PDF
        if facs_raw:
            lista_facs = sorted([f"- {f.strip()}" for f in facs_raw.split(",") if f.strip()])
            facs_texto = "\n".join(lista_facs)
        else:
            facs_texto = "Sin facultades"
            
        textos = [str(row['NOMBRE']), str(rol_texto), facs_texto]
        
        lineas_por_col = [len(pdf.multi_cell(cw[i], 5, txt, split_only=True)) for i, txt in enumerate(textos)]
        h_fila = 5 * max(lineas_por_col)
        
        x_ini, y_ini = pdf.get_x(), y_ini = pdf.get_y()
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

def generar_pdf_roles(df_roles):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "INMOLEASING - MATRIZ DE ROLES", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(200, 220, 255)
    cw = [60, 130] # Total 190mm
    headers = ["ROL", "FACULTADES ASIGNADAS"]
    for i, h_text in enumerate(headers):
        pdf.cell(cw[i], 10, h_text, border=1, fill=True, align="C")
    pdf.ln()
    
    pdf.set_font("Arial", "", 9)
    for _, row in df_roles.iterrows():
        facs_raw = row['descripcion']
        if facs_raw:
            lista_facs = sorted([f"- {f.strip()}" for f in facs_raw.split(",") if f.strip()])
            facs_texto = "\n".join(lista_facs)
        else:
            facs_texto = "Sin facultades"
            
        textos = [str(row['nombre_rol']), facs_texto]
        
        lineas_por_col = [len(pdf.multi_cell(cw[i], 6, txt, split_only=True)) for i, txt in enumerate(textos)]
        h_fila = 6 * max(lineas_por_col)
        
        x_ini, y_ini = pdf.get_x(), pdf.get_y()
        if y_ini + h_fila > 275:
            pdf.add_page()
            y_ini = pdf.get_y()

        x_actual = x_ini 
        for i, txt in enumerate(textos):
            pdf.set_xy(x_actual, y_ini)
            pdf.rect(x_actual, y_ini, cw[i], h_fila)
            pdf.multi_cell(cw[i], 6, txt, border=0, align='L')
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
        DICCIONARIO_DESC = {rol['id']: rol['descripcion'] for rol in res_roles.data}
        
        res_fac = supabase.table("facultades").select("*").execute()
        df_fac = pd.DataFrame(res_fac.data) if res_fac.data else pd.DataFrame()
        if not df_fac.empty:
            df_fac = df_fac.sort_values('nombre_facultad')
        llaves_iconos = [f"{row['icono']} {row['nombre_facultad']}" for _, row in df_fac.iterrows()] if not df_fac.empty else []
    except:
        df_roles, df_fac, DICCIONARIO_ROLES, DICCIONARIO_DESC, llaves_iconos = pd.DataFrame(), pd.DataFrame(), {}, {}, []
        
    res_u = supabase.table("usuarios").select("*").execute()
    df_raw = pd.DataFrame(res_u.data) if res_u.data else pd.DataFrame()
    if not df_raw.empty and 'estado' not in df_raw.columns:
        df_raw['estado'] = 'ACTIVO'

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Directorio", "➕ Nuevo Usuario", "⚙️ Gestionar", "🛡️ Facultades y Roles", "📜 Logs de Actividad"])

    # --- TAB 1: DIRECTORIO ---
    with tab1:
        if not df_raw.empty:
            busqueda = st.text_input("🔍 Buscar usuario...", "").upper().strip()
            df_display = df_raw.copy().sort_values('nombre')
            
            df_display['ROL'] = df_display['id_rol'].map(DICCIONARIO_ROLES)
            df_display['ESTADO'] = df_display['estado'].fillna('ACTIVO')
            df_display.rename(columns={'nombre': 'NOMBRE', 'email': 'EMAIL', 'moneda': 'MONEDA'}, inplace=True)
            
            if busqueda:
                df_display = df_display[df_display['NOMBRE'].str.contains(busqueda)]
            
            st.dataframe(df_display[["NOMBRE", "EMAIL", "MONEDA", "ROL", "ESTADO"]], use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("### 🔍 Consultar Facultades por Usuario")
            u_consulta = st.selectbox("Selecciona un usuario para ver sus permisos:", ["-- Selecciona --"] + df_display['NOMBRE'].tolist())
            
            if u_consulta != "-- Selecciona --":
                rol_id_user = df_display[df_display['NOMBRE'] == u_consulta]['id_rol'].values[0]
                facultades_user = DICCIONARIO_DESC.get(rol_id_user, "")
                
                if facultades_user:
                    lista_facs = sorted([f"- {fac.strip()}" for fac in facultades_user.split(",") if fac.strip()])
                    facs_formateadas = "\n".join(lista_facs)
                    st.info(f"**Facultades asignadas al usuario {u_consulta}:**\n\n{facs_formateadas}")
                else:
                    st.warning(f"**{u_consulta}** no tiene facultades asignadas en su rol.")

            st.markdown("---")
            # NUEVO: Dos botones de descarga en columnas
            col_pdf1, col_pdf2 = st.columns(2)
            with col_pdf1:
                pdf_bytes = generar_pdf_usuarios(df_display, DICCIONARIO_ROLES)
                st.download_button("📄 Exportar Reporte Básico (PDF)", pdf_bytes, "usuarios_basico.pdf", "application/pdf", use_container_width=True)
            with col_pdf2:
                pdf_det_bytes = generar_pdf_usuarios_detallado(df_display, DICCIONARIO_ROLES, DICCIONARIO_DESC)
                st.download_button("📄 Exportar Reporte Detallado (PDF)", pdf_det_bytes, "usuarios_detallado.pdf", "application/pdf", use_container_width=True)

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
                            "password": n_pas, "moneda": n_mon, "id_rol": int(n_rol[0]),
                            "estado": "ACTIVO" 
                        }).execute()
                        log_accion(supabase, usuario_actual, "CREAR USUARIO", f"Registrado: {n_nom.upper()} | Rol ID: {n_rol[0]}")
                        st.success(f"¡Usuario {n_nom.upper()} creado!"); st.rerun()
                else:
                    st.warning("⚠️ Todos los campos son obligatorios.")

    # --- TAB 3: GESTIONAR ---
    with tab3:
        if not df_raw.empty:
            nombres_ordenados = df_raw.sort_values('nombre')['nombre'].tolist()
            u_edit = st.selectbox("Seleccione un usuario a gestionar:", nombres_ordenados)
            u_data = df_raw[df_raw['nombre'] == u_edit].iloc[0]
            estado_actual = u_data.get('estado', 'ACTIVO')
            
            if estado_actual == 'INACTIVO':
                st.error(f"⚠️ El usuario {u_edit} está INACTIVO.")
            else:
                st.success(f"✅ El usuario {u_edit} está ACTIVO.")
            
            with st.form("form_edicion"):
                e_nom = st.text_input("Nombre", u_data['nombre'])
                e_ema = st.text_input("Email", u_data['email'])
                
                # NUEVO: Tamaño del password reducido a media columna
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    e_pas = st.text_input("Nueva Contraseña", type="password", help="Déjalo en blanco si no deseas cambiar la contraseña actual.")
                
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    index_rol = list(DICCIONARIO_ROLES.keys()).index(u_data['id_rol']) if u_data['id_rol'] in DICCIONARIO_ROLES else 0
                    e_rol = st.selectbox("Cambiar Rol", options=list(DICCIONARIO_ROLES.items()), index=index_rol, format_func=lambda x: x[1])
                with col_m2:
                    monedas_disponibles = ["EUR", "COP", "ALL"]
                    moneda_user = str(u_data.get('moneda', 'ALL'))
                    idx_mon = monedas_disponibles.index(moneda_user) if moneda_user in monedas_disponibles else 2
                    e_mon = st.selectbox("Cambiar Moneda Base (Región)", monedas_disponibles, index=idx_mon)
                
                if st.form_submit_button("💾 Guardar Cambios"):
                    if es_correo_valido(e_ema):
                        datos_a_actualizar = {
                            "nombre": e_nom.upper(), 
                            "email": e_ema.lower(), 
                            "id_rol": int(e_rol[0]),
                            "moneda": e_mon  
                        }
                        if e_pas.strip() != "":
                            datos_a_actualizar["password"] = e_pas
                            
                        supabase.table("usuarios").update(datos_a_actualizar).eq("id", int(u_data['id'])).execute()
                        log_accion(supabase, usuario_actual, "EDITAR USUARIO", f"Actualizado: {e_nom.upper()} | Nueva Región: {e_mon}")
                        st.success("Cambios aplicados."); st.rerun()
                    else:
                        st.error("❌ Correo inválido.")
            
            st.markdown("---")
            if "confirmar_borrado_user" not in st.session_state:
                st.session_state.confirmar_borrado_user = None

            if estado_actual == 'ACTIVO':
                if st.button("🚫 Desactivar Usuario (Soft Delete)", type="primary"):
                    st.session_state.confirmar_borrado_user = u_data['id']
                    st.rerun()
            else:
                if st.button("♻️ Reactivar Usuario"):
                    supabase.table("usuarios").update({"estado": "ACTIVO"}).eq("id", int(u_data['id'])).execute()
                    log_accion(supabase, usuario_actual, "REACTIVAR USUARIO", f"Acceso restaurado a: {u_edit}")
                    st.rerun()

            if st.session_state.confirmar_borrado_user == u_data['id']:
                st.warning(f"⚠️ ¿Desactivar a {u_edit}?")
                c_si, c_no = st.columns(2)
                if c_si.button("✅ Sí, Desactivar"):
                    supabase.table("usuarios").update({"estado": "INACTIVO"}).eq("id", int(u_data['id'])).execute()
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
                # SE ELIMINÓ EL st.info() COMO SOLICITASTE
                with st.form("form_facultad"):
                    f_ico = st.selectbox("Selecciona un Icono", LISTA_ICONOS) 
                    f_nom = st.text_input("Nombre Técnico (Ej: MODULO_FINANZAS)")
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
                            supabase.table("facultades").update({"icono": ef_ico, "nombre_facultad": ef_nom.upper()}).eq("id", int(f_row['id'])).execute()
                            log_accion(supabase, usuario_actual, "EDITAR FACULTAD", f"Facultad modificada: {ef_nom.upper()}")
                            st.rerun()
                            
                    if "confirmar_borrado_fac" not in st.session_state:
                        st.session_