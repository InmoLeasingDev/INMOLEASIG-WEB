import streamlit as st
import pandas as pd
import re
from fpdf import FPDF

# ==========================================
# 0. FUNCIONES AUXILIARES Y LOGS
# ==========================================
def log_accion(supabase, accion, detalle):
    try:
        supabase.table("logs_actividad").insert({"accion": accion, "detalle": detalle}).execute()
    except Exception as e:
        pass # Si falla el log, no rompemos la app

def es_correo_valido(correo):
    patron = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(patron, correo) is not None

# ==========================================
# 1. FUNCIÓN PDF: VERSIÓN PERFECTA
# ==========================================
def generar_pdf_usuarios(df, diccionario_roles):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "INMOLEASING - REPORTE DE USUARIOS", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(200, 220, 255)
    cw = [55, 85, 50] 
    headers = ["NOMBRE", "EMAIL", "ROL"]
    for i, h_text in enumerate(headers):
        pdf.cell(cw[i], 10, h_text, border=1, fill=True, align="C")
    pdf.ln()
    
    pdf.set_font("Arial", "", 9)
    for _, row in df.iterrows():
        rol_texto = diccionario_roles.get(row['id_rol'], "SIN ROL")
        textos = [str(row['nombre']), str(row['email']), str(rol_texto)]
        
        lineas_por_col = []
        for i, txt in enumerate(textos):
            n = len(pdf.multi_cell(cw[i], 7, txt, split_only=True))
            lineas_por_col.append(n)
        
        max_l = max(lineas_por_col)
        h_fila = 7 * max_l 
        
        x_ini = pdf.get_x()
        y_ini = pdf.get_y()
        
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

# ==========================================
# 2. MÓDULO PRINCIPAL
# ==========================================
def mostrar_modulo_usuarios(supabase):
    st.header("👤 Gestión de Usuarios")
    
    # --- Carga de Datos ---
    try:
        res_roles = supabase.table("roles").select("*").execute()
        df_roles = pd.DataFrame(res_roles.data) if res_roles.data else pd.DataFrame()
        DICCIONARIO_ROLES = {rol['id']: rol['nombre_rol'] for rol in res_roles.data}
        
        res_fac = supabase.table("facultades").select("*").execute()
        df_fac = pd.DataFrame(res_fac.data) if res_fac.data else pd.DataFrame()
        llaves_iconos = [f"{row['icono']} {row['nombre_facultad']}" for _, row in df_fac.iterrows()] if not df_fac.empty else []
    except:
        df_roles, df_fac, DICCIONARIO_ROLES, llaves_iconos = pd.DataFrame(), pd.DataFrame(), {}, []
        
    res_u = supabase.table("usuarios").select("*").execute()
    df_raw = pd.DataFrame(res_u.data) if res_u.data else pd.DataFrame()

    tab1, tab2, tab3, tab4 = st.tabs(["📋 Directorio", "➕ Nuevo Usuario", "⚙️ Gestionar", "🛡️ Roles y Facultades"])

    # --- TAB 1: DIRECTORIO ---
    with tab1:
        if not df_raw.empty:
            busqueda = st.text_input("🔍 Buscar usuario...", "").upper().strip()
            df_display = df_raw.copy().sort_values('nombre')
            df_display['Rol'] = df_display['id_rol'].map(DICCIONARIO_ROLES)
            if busqueda:
                df_display = df_display[df_display['nombre'].str.contains(busqueda)]
            
            st.dataframe(df_display[["nombre", "email", "moneda", "Rol"]], use_container_width=True, hide_index=True)
            
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
            n_mon = col2.selectbox("Moneda Base", ["EUR", "COP", "ALL"]) # Monedas ordenadas
            n_rol = st.selectbox("Rol Asignado", options=list(DICCIONARIO_ROLES.items()), format_func=lambda x: x[1])
            
            if st.form_submit_button("✅ Crear Usuario"):
                if n_nom and n_ema and n_pas:
                    if not es_correo_valido(n_ema):
                        st.error("❌ Formato de correo inválido.")
                    else:
                        supabase.table("usuarios").insert({
                            "nombre": n_nom.upper(), "email": n_ema.lower(), 
                            "password": n_pas, "moneda": n_mon, "id_rol": n_rol[0]
                        }).execute()
                        log_accion(supabase, "CREAR", f"Nuevo usuario registrado: {n_nom.upper()}")
                        st.success(f"¡Usuario {n_nom.upper()} creado!"); st.rerun()
                else:
                    st.warning("⚠️ Todos los campos son obligatorios.")

    # --- TAB 3: GESTIONAR (BÚSQUEDA Y CONFIRMACIÓN) ---
    with tab3:
        if not df_raw.empty:
            busqueda_edit = st.text_input("🔍 Buscar usuario a gestionar...", "").upper().strip()
            df_edit = df_raw.copy()
            if busqueda_edit:
                df_edit = df_edit[df_edit['nombre'].str.contains(busqueda_edit)]
            
            if not df_edit.empty:
                u_edit = st.selectbox("Seleccione un usuario:", df_edit['nombre'].tolist())
                u_data = df_edit[df_edit['nombre'] == u_edit].iloc[0]
                
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
                            log_accion(supabase, "EDITAR", f"Datos actualizados de: {e_nom.upper()}")
                            st.success("Cambios aplicados."); st.rerun()
                        else:
                            st.error("❌ Correo inválido.")
                
                # Zona de Peligro: Confirmación antes de eliminar
                st.markdown("---")
                st.markdown("**🚨 Zona de Peligro**")
                confirmar = st.checkbox(f"Confirmo que deseo eliminar permanentemente a {u_edit}")
                if confirmar:
                    if st.button("🗑️ Eliminar Usuario", type="primary"):
                        supabase.table("usuarios").delete().eq("id", u_data['id']).execute()
                        log_accion(supabase, "ELIMINAR", f"Usuario borrado: {u_data['nombre']}")
                        st.rerun()
            else:
                st.info("No se encontraron coincidencias.")

    # --- TAB 4: ROLES Y FACULTADES (SUB-NAVEGACIÓN) ---
    with tab4:
        seccion = st.radio("Gestionar:", ["Roles de Usuario", "Catálogo de Facultades"], horizontal=True)
        st.markdown("---")
        
        if seccion == "Roles de Usuario":
            c1, c2 = st.columns(2)
            with c1:
                with st.form("n_rol_form"):
                    nr_nom = st.text_input("Nombre del nuevo Rol")
                    nr_llaves = st.multiselect("Asignar Facultades:", llaves_iconos)
                    if st.form_submit_button("Crear Perfil"):
                        if nr_nom:
                            supabase.table("roles").insert({"nombre_rol": nr_nom.upper(), "descripcion": ", ".join(nr_llaves)}).execute()
                            log_accion(supabase, "ROL", f"Rol creado: {nr_nom.upper()}")
                            st.rerun()
            with c2:
                if not df_roles.empty:
                    r_edit = st.selectbox("Editar Facultades de:", df_roles['nombre_rol'].tolist())
                    r_row = df_roles[df_roles['nombre_rol'] == r_edit].iloc[0]
                    previas = [p.strip() for p in r_row['descripcion'].split(",")] if r_row['descripcion'] else []
                    with st.form("e_rol_form"):
                        er_llaves = st.multiselect("Modificar Facultades:", llaves_iconos, default=[p for p in previas if p in llaves_iconos])
                        if st.form_submit_button("Actualizar"):
                            supabase.table("roles").update({"descripcion": ", ".join(er_llaves)}).eq("id", r_row['id']).execute()
                            log_accion(supabase, "ROL", f"Facultades actualizadas para: {r_edit}")
                            st.success("Permisos actualizados."); st.rerun()
                            
        elif seccion == "Catálogo de Facultades":
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.write("**Nueva Facultad**")
                with st.form("form_facultad"):
                    f_ico = st.text_input("Icono (Emoji, ej: 🔑)")
                    f_nom = st.text_input("Nombre Técnico (Ej: REPORTE_PAGOS)")
                    if st.form_submit_button("Añadir Facultad"):
                        if f_nom:
                            supabase.table("facultades").insert({"icono": f_ico, "nombre_facultad": f_nom.upper()}).execute()
                            log_accion(supabase, "FACULTAD", f"Creada: {f_nom.upper()}")
                            st.rerun()
            with col_f2:
                st.write("**Facultades Existentes**")
                if not df_fac.empty:
                    st.dataframe(df_fac[['icono', 'nombre_facultad']], hide_index=True, use_container_width=True)
                    # Eliminación simple de facultades
                    f_del = st.selectbox("Eliminar Facultad:", df_fac['nombre_facultad'].tolist())
                    f_id = df_fac[df_fac['nombre_facultad'] == f_del]['id'].values[0]
                    if st.button("❌ Borrar", type="primary"):
                        supabase.table("facultades").delete().eq("id", f_id).execute()
                        log_accion(supabase, "FACULTAD", f"Eliminada: {f_del}")
                        st.rerun()