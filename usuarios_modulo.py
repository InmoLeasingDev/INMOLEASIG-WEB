import streamlit as st
import pandas as pd
import re
import hashlib
from fpdf import FPDF

# ==========================================
# 0. FUNCIONES AUXILIARES Y LOGS
# ==========================================
def encriptar_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def log_accion(supabase, usuario, accion, detalle):
    try:
        supabase.table("logs_actividad").insert({
            "usuario": usuario, 
            "accion": accion, 
            "detalle": detalle
        }).execute()
    except Exception:
        pass 

def es_correo_valido(correo):
    patron = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(patron, correo) is not None

def limpiar_texto_pdf(texto):
    if pd.isna(texto):
        return ""
    return str(texto).encode('latin-1', 'ignore').decode('latin-1')

def ordenar_facultades_alfabeticamente(cadena_facultades):
    if not cadena_facultades:
        return []
    facs = [f.strip() for f in cadena_facultades.split(",") if f.strip()]
    return sorted(facs, key=lambda x: x.split(" ", 1)[-1] if " " in x else x)

def sincronizar_roles_facultad(supabase, df_roles, fac_vieja, fac_nueva=None):
    if df_roles.empty:
        return
        
    for _, row in df_roles.iterrows():
        desc_actual = row.get('descripcion', '')
        if desc_actual and fac_vieja in desc_actual:
            lista_facs = [f.strip() for f in desc_actual.split(",") if f.strip()]
            if fac_vieja in lista_facs:
                if fac_nueva:
                    idx = lista_facs.index(fac_vieja)
                    lista_facs[idx] = fac_nueva
                else:
                    lista_facs.remove(fac_vieja)
                
                nueva_desc = ", ".join(lista_facs)
                try:
                    supabase.table("roles").update({"descripcion": nueva_desc}).eq("id", int(row['id'])).execute()
                except Exception:
                    pass

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
    
    pdf.set_font("Arial", "B", 8)
    pdf.set_fill_color(200, 220, 255)
    cw = [45, 60, 20, 40, 25] 
    headers = ["NOMBRE", "EMAIL", "ROL", "ULTIMO ACCESO", "ESTADO"]
    for i, h_text in enumerate(headers):
        pdf.cell(cw[i], 10, h_text, border=1, fill=True, align="C")
    pdf.ln()
    
    pdf.set_font("Arial", "", 7)
    for _, row in df.iterrows():
        rol_texto = diccionario_roles.get(row['id_rol'], "SIN ROL")
        estado_texto = str(row.get('estado', 'ACTIVO'))
        
        textos_raw = [
            str(row['NOMBRE']), 
            str(row['EMAIL']), 
            str(rol_texto), 
            str(row.get('ULTIMO ACCESO', '')), 
            estado_texto
        ]
        textos = [limpiar_texto_pdf(t) for t in textos_raw]
        
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

def generar_pdf_usuarios_detallado(df, diccionario_roles, diccionario_desc):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "INMOLEASING - USUARIOS Y FACULTADES", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(200, 220, 255)
    cw = [40, 35, 115] 
    headers = ["NOMBRE", "ROL", "FACULTADES ASIGNADAS"]
    for i, h_text in enumerate(headers):
        pdf.cell(cw[i], 8, h_text, border=1, fill=True, align="C")
    pdf.ln()
    
    pdf.set_font("Arial", "", 8)
    for _, row in df.iterrows():
        rol_texto = diccionario_roles.get(row['id_rol'], "SIN ROL")
        facs_raw = diccionario_desc.get(row['id_rol'], "")
        
        if facs_raw:
            facs_ordenadas = ordenar_facultades_alfabeticamente(facs_raw)
            lista_facs = [f"- {f}" for f in facs_ordenadas]
            facs_texto = "\n".join(lista_facs)
        else:
            facs_texto = "Sin facultades"
            
        textos_raw = [str(row['NOMBRE']), str(rol_texto), facs_texto]
        textos = [limpiar_texto_pdf(t) for t in textos_raw]
        
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

def generar_pdf_roles(df_roles):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "INMOLEASING - MATRIZ DE ROLES", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(200, 220, 255)
    cw = [60, 130] 
    headers = ["ROL", "FACULTADES ASIGNADAS"]
    for i, h_text in enumerate(headers):
        pdf.cell(cw[i], 10, h_text, border=1, fill=True, align="C")
    pdf.ln()
    
    pdf.set_font("Arial", "", 9)
    for _, row in df_roles.iterrows():
        facs_raw = row['descripcion']
        
        if facs_raw:
            facs_ordenadas = ordenar_facultades_alfabeticamente(facs_raw)
            lista_facs = [f"- {f}" for f in facs_ordenadas]
            facs_texto = "\n".join(lista_facs)
        else:
            facs_texto = "Sin facultades"
            
        textos_raw = [str(row['nombre_rol']), facs_texto]
        textos = [limpiar_texto_pdf(t) for t in textos_raw]
        
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
        textos_raw = [fecha_corta, usr, str(row['accion']), str(row['detalle'])]
        textos = [limpiar_texto_pdf(t) for t in textos_raw]
        
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
    moneda_sesion = st.session_state.get("moneda_usuario", "ALL")
    
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
    except Exception:
        df_roles = pd.DataFrame()
        df_fac = pd.DataFrame()
        DICCIONARIO_ROLES = {}
        DICCIONARIO_DESC = {}
        llaves_iconos = []
        
    res_u = supabase.table("usuarios").select("*").execute()
    df_raw = pd.DataFrame(res_u.data) if res_u.data else pd.DataFrame()
    
    # --- FILTRO MULTINACIONAL PRO ---
    if not df_raw.empty:
        if moneda_sesion != "ALL":
            df_raw = df_raw[df_raw['moneda'] == moneda_sesion]

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Directorio", "➕ Nuevo Usuario", "⚙️ Gestionar", "🛡️ Facultades y Roles", "📜 Logs de Actividad"])

    # --- TAB 1: DIRECTORIO ---
    with tab1:
        if not df_raw.empty:
            busqueda = st.text_input("🔍 Buscar usuario...", "").upper().strip()
            df_display = df_raw.copy().sort_values('nombre')
            
            df_display['ROL'] = df_display['id_rol'].map(DICCIONARIO_ROLES)
            df_display['ESTADO'] = df_display['estado'].fillna('ACTIVO')
            
            # Formateamos el último acceso para la vista
            df_display['ultimo_acceso'] = pd.to_datetime(df_display['ultimo_acceso']).dt.strftime('%Y-%m-%d %H:%M')
            df_display['ultimo_acceso'] = df_display['ultimo_acceso'].fillna('Nunca')
            
            df_display.rename(columns={'nombre': 'NOMBRE', 'email': 'EMAIL', 'moneda': 'MONEDA', 'ultimo_acceso': 'ULTIMO ACCESO'}, inplace=True)
            
            if busqueda: 
                df_display = df_display[df_display['NOMBRE'].str.contains(busqueda)]
                
            st.dataframe(df_display[["NOMBRE", "EMAIL", "MONEDA", "ROL", "ULTIMO ACCESO", "ESTADO"]], use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("### 🔍 Consultar Facultades por Usuario")
            u_consulta = st.selectbox("Selecciona un usuario para ver sus permisos:", ["-- Selecciona --"] + df_display['NOMBRE'].tolist())
            
            if u_consulta != "-- Selecciona --":
                rol_id_user = df_display[df_display['NOMBRE'] == u_consulta]['id_rol'].values[0]
                facultades_user = DICCIONARIO_DESC.get(rol_id_user, "")
                
                if facultades_user:
                    facs_ordenadas = ordenar_facultades_alfabeticamente(facultades_user)
                    st.info(f"**Facultades de {u_consulta}:**\n\n" + "\n".join([f"- {f}" for f in facs_ordenadas]))
                else: 
                    st.warning(f"**{u_consulta}** no tiene facultades asignadas.")
                    
            st.markdown("---")
            c_pdf1, c_pdf2 = st.columns(2)
            with c_pdf1:
                pdf_bytes = generar_pdf_usuarios(df_display, DICCIONARIO_ROLES)
                st.download_button("📄 Reporte Básico", pdf_bytes, "usuarios_basico.pdf", use_container_width=True)
            with c_pdf2:
                pdf_det_bytes = generar_pdf_usuarios_detallado(df_display, DICCIONARIO_ROLES, DICCIONARIO_DESC)
                st.download_button("📄 Reporte Detallado", pdf_det_bytes, "usuarios_detallado.pdf", use_container_width=True)

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
                        st.error("❌ Correo inválido.")
                    else:
                        pass_hash = encriptar_password(n_pas)
                        supabase.table("usuarios").insert({
                            "nombre": n_nom.upper(), 
                            "email": n_ema.lower(), 
                            "password": pass_hash, 
                            "moneda": n_mon, 
                            "id_rol": int(n_rol[0]), 
                            "estado": "ACTIVO"
                        }).execute()
                        
                        log_accion(supabase, usuario_actual, "CREAR USUARIO", f"Registrado: {n_nom.upper()}")
                        st.success("Usuario creado!")
                        st.rerun()
                else: 
                    st.warning("⚠️ Todos los campos son obligatorios.")

    # --- TAB 3: GESTIONAR ---
    with tab3:
        if not df_raw.empty:
            u_edit = st.selectbox("Seleccione un usuario:", df_raw.sort_values('nombre')['nombre'].tolist())
            u_data = df_raw[df_raw['nombre'] == u_edit].iloc[0]
            
            with st.form("form_edicion"):
                c_e1, c_e2 = st.columns(2)
                e_nom = c_e1.text_input("Nombre", u_data['nombre'])
                e_ema = c_e2.text_input("Email", u_data['email'])
                
                c_p1, _ = st.columns(2)
                e_pas = c_p1.text_input("Nueva Contraseña", type="password", help="Dejar en blanco para mantener la actual.")
                
                c_m1, c_m2 = st.columns(2)
                
                idx_rol = list(DICCIONARIO_ROLES.keys()).index(u_data['id_rol']) if u_data['id_rol'] in DICCIONARIO_ROLES else 0
                e_rol = c_m1.selectbox("Cambiar Rol", options=list(DICCIONARIO_ROLES.items()), index=idx_rol, format_func=lambda x: x[1])
                
                idx_mon = ["EUR", "COP", "ALL"].index(u_data['moneda']) if u_data['moneda'] in ["EUR", "COP", "ALL"] else 2
                e_mon = c_m2.selectbox("Cambiar Moneda", ["EUR", "COP", "ALL"], index=idx_mon)
                
                if st.form_submit_button("💾 Guardar"):
                    if es_correo_valido(e_ema):
                        upd = {
                            "nombre": e_nom.upper(), 
                            "email": e_ema.lower(), 
                            "id_rol": int(e_rol[0]), 
                            "moneda": e_mon
                        }
                        if e_pas.strip(): 
                            upd["password"] = encriptar_password(e_pas)
                            
                        supabase.table("usuarios").update(upd).eq("id", int(u_data['id'])).execute()
                        log_accion(supabase, usuario_actual, "EDITAR USUARIO", f"Actualizado: {e_nom.upper()}")
                        st.success("Cambios aplicados!")
                        st.rerun()
                        
            st.markdown("---")
            if u_data.get('estado') == 'ACTIVO':
                if st.button("🚫 Desactivar Usuario", type="primary"):
                    supabase.table("usuarios").update({"estado": "INACTIVO"}).eq("id", int(u_data['id'])).execute()
                    log_accion(supabase, usuario_actual, "INACTIVAR USUARIO", f"Bloqueado: {u_edit}")
                    st.rerun()
            else:
                if st.button("♻️ Reactivar Usuario"):
                    supabase.table("usuarios").update({"estado": "ACTIVO"}).eq("id", int(u_data['id'])).execute()
                    log_accion(supabase, usuario_actual, "REACTIVAR USUARIO", f"Acceso restaurado: {u_edit}")
                    st.rerun()

    # --- TAB 4: ROLES Y FACULTADES ---
    with tab4:
        sec = st.radio("Gestionar:", ["1. Facultades", "2. Roles"], horizontal=True)
        
        if sec == "1. Facultades":
            c_f1, c_f2 = st.columns(2)
            with c_f1:
                with st.form("form_facultad"):
                    f_ico = st.selectbox("Icono", LISTA_ICONOS)
                    f_nom = st.text_input("Nombre Técnico")
                    if st.form_submit_button("Añadir"):
                        if f_nom:
                            supabase.table("facultades").insert({"icono": f_ico, "nombre_facultad": f_nom.upper()}).execute()
                            log_accion(supabase, usuario_actual, "CREAR FACULTAD", f_nom.upper())
                            st.rerun()
            with c_f2:
                if not df_fac.empty:
                    f_edit_nom = st.selectbox("Seleccione:", df_fac['nombre_facultad'].tolist())
                    f_row = df_fac[df_fac['nombre_facultad'] == f_edit_nom].iloc[0]
                    v_str = f"{f_row['icono']} {f_row['nombre_facultad']}"
                    
                    with st.form("edit_fac"):
                        idx_ico = LISTA_ICONOS.index(f_row['icono']) if f_row['icono'] in LISTA_ICONOS else 0
                        ef_ico = st.selectbox("Icono", LISTA_ICONOS, index=idx_ico)
                        ef_nom = st.text_input("Nombre", f_row['nombre_facultad'])
                        
                        if st.form_submit_button("Actualizar"):
                            n_str = f"{ef_ico} {ef_nom.upper()}"
                            supabase.table("facultades").update({"icono": ef_ico, "nombre_facultad": ef_nom.upper()}).eq("id", int(f_row['id'])).execute()
                            sincronizar_roles_facultad(supabase, df_roles, v_str, n_str)
                            st.rerun()
                            
                    if st.button("🗑️ Eliminar Facultad"):
                        supabase.table("facultades").delete().eq("id", int(f_row['id'])).execute()
                        sincronizar_roles_facultad(supabase, df_roles, v_str, None)
                        st.rerun()

        else:
            c1, c2 = st.columns(2)
            with c1:
                with st.form("n_rol_form"):
                    nr_nom = st.text_input("Nombre Rol")
                    nr_llaves = st.multiselect("Facultades:", llaves_iconos)
                    if st.form_submit_button("Crear Rol"):
                        if nr_nom:
                            supabase.table("roles").insert({"nombre_rol": nr_nom.upper(), "descripcion": ", ".join(nr_llaves)}).execute()
                            st.rerun()
            with c2:
                if not df_roles.empty:
                    r_edit = st.selectbox("Editar Rol:", df_roles.sort_values('nombre_rol')['nombre_rol'].tolist())
                    r_row = df_roles[df_roles['nombre_rol'] == r_edit].iloc[0]
                    
                    with st.form("e_rol_form"):
                        def_facs = [p.strip() for p in r_row['descripcion'].split(",")] if r_row['descripcion'] else []
                        er_llaves = st.multiselect("Facultades:", llaves_iconos, default=def_facs)
                        if st.form_submit_button("Actualizar"):
                            supabase.table("roles").update({"descripcion": ", ".join(er_llaves)}).eq("id", int(r_row['id'])).execute()
                            st.rerun()
                            
                    if st.button("🗑️ Eliminar Rol"):
                        supabase.table("roles").delete().eq("id", int(r_row['id'])).execute()
                        st.rerun()
                        
            st.markdown("---")
            st.download_button("Descargar Matriz de Roles", generar_pdf_roles(df_roles), "matriz_roles.pdf", use_container_width=True)

    # --- TAB 5: LOGS Y AUDITORÍA ---
    with tab5:
        try:
            res_l = supabase.table("logs_actividad").select("*").order("fecha", desc=True).execute()
            df_l = pd.DataFrame(res_l.data) if res_l.data else pd.DataFrame()
            
            if not df_l.empty:
                df_l['fecha'] = pd.to_datetime(df_l['fecha']).dt.tz_localize(None)
                
                c_f1, c_f2, c_f3 = st.columns(3)
                f_r = c_f1.date_input("Rango", [])
                u_f = c_f2.selectbox("Usuario", ["Todos"] + sorted(df_l['usuario'].unique().tolist()))
                t_f = c_f3.text_input("Buscar").upper()
                
                if len(f_r) == 2: 
                    df_l = df_l[(df_l['fecha'].dt.date >= f_r[0]) & (df_l['fecha'].dt.date <= f_r[1])]
                if u_f != "Todos": 
                    df_l = df_l[df_l['usuario'] == u_f]
                if t_f: 
                    df_l = df_l[df_l['accion'].str.contains(t_f) | df_l['detalle'].str.contains(t_f)]
                    
                df_visual = df_l[['fecha', 'usuario', 'accion', 'detalle']].copy()
                df_visual['fecha'] = df_visual['fecha'].dt.strftime('%Y-%m-%d %H:%M')
                
                st.dataframe(df_visual, use_container_width=True, hide_index=True)
                st.download_button("Descargar Auditoría", generar_pdf_logs(df_l), "auditoria.pdf")
        except Exception: 
            st.info("Sin registros.")