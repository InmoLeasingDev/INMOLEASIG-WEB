import streamlit as st
import pandas as pd
import re
from fpdf import FPDF

# ==========================================
# 1. FUNCIÓN PDF (RESTAURADA A LA VERSIÓN QUE TE GUSTABA)
# ==========================================
def generar_pdf_usuarios(df, diccionario_roles):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "INMOLEASING - REPORTE DE USUARIOS", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(200, 220, 255)
    
    col_width = [60, 80, 50] 
    pdf.cell(col_width[0], 10, "NOMBRE", border=1, fill=True)
    pdf.cell(col_width[1], 10, "EMAIL", border=1, fill=True)
    pdf.cell(col_width[2], 10, "ROL", border=1, fill=True)
    pdf.ln()
    
    pdf.set_font("Arial", "", 9)
    for _, row in df.iterrows():
        rol_texto = diccionario_roles.get(row['id_rol'], "SIN ROL")
        x_start = pdf.get_x()
        y_start = pdf.get_y()
        
        pdf.multi_cell(col_width[0], 8, str(row['nombre']), border=1)
        alt_nombre = pdf.get_y()
        
        pdf.set_xy(x_start + col_width[0], y_start)
        pdf.multi_cell(col_width[1], 8, str(row['email']), border=1)
        alt_email = pdf.get_y()
        
        pdf.set_xy(x_start + col_width[0] + col_width[1], y_start)
        pdf.multi_cell(col_width[2], 8, str(rol_texto), border=1)
        alt_rol = pdf.get_y()
        
        pdf.set_y(max(alt_nombre, alt_email, alt_rol))
        
    return pdf.output(dest='S').encode('latin-1')

def es_correo_valido(correo):
    patron = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(patron, correo) is not None

# ==========================================
# 2. MÓDULO PRINCIPAL
# ==========================================
def mostrar_modulo_usuarios(supabase):
    st.header("👤 Gestión de Usuarios")
    
    try:
        res_roles = supabase.table("roles").select("*").execute()
        df_roles = pd.DataFrame(res_roles.data) if res_roles.data else pd.DataFrame()
        DICCIONARIO_ROLES = {rol['id']: rol['nombre_rol'] for rol in res_roles.data}
        DICCIONARIO_DESC = {rol['id']: rol['descripcion'] for rol in res_roles.data}
    except:
        df_roles, DICCIONARIO_ROLES, DICCIONARIO_DESC = pd.DataFrame(), {}, {}
        
    res_u = supabase.table("usuarios").select("*").execute()
    df_raw = pd.DataFrame(res_u.data) if res_u.data else pd.DataFrame()

    tab1, tab2, tab3, tab4 = st.tabs(["📋 Directorio", "➕ Nuevo Usuario", "⚙️ Gestionar", "🛡️ Roles"])

    with tab1:
        if not df_raw.empty:
            busqueda = st.text_input("🔍 Buscar usuario...", "").upper().strip()
            df_display = df_raw.copy().sort_values('nombre')
            df_display['Rol'] = df_display['id_rol'].map(DICCIONARIO_ROLES)
            if busqueda:
                df_display = df_display[df_display['nombre'].str.contains(busqueda)]
            
            st.dataframe(df_display[["nombre", "email", "moneda", "Rol"]], use_container_width=True, hide_index=True)
            
            pdf_bytes = generar_pdf_usuarios(df_display, DICCIONARIO_ROLES)
            st.download_button("📄 Descargar Reporte PDF", pdf_bytes, "usuarios.pdf", "application/pdf")

    with tab2:
        st.subheader("Registrar Colaborador")
        with st.form("form_registro_estable"):
            col1, col2 = st.columns(2)
            n_nom = col1.text_input("Nombre Completo")
            n_ema = col1.text_input("Correo")
            n_pas = col2.text_input("Password", type="password")
            n_mon = col2.selectbox("Moneda", ["COP", "USD", "EUR"])
            n_rol = st.selectbox("Rol", options=list(DICCIONARIO_ROLES.items()), format_func=lambda x: x[1])
            
            if st.form_submit_button("🚀 Registrar"):
                if n_nom and n_ema and n_pas:
                    if not es_correo_valido(n_ema):
                        st.error("⚠️ Correo inválido. Los datos se mantienen para corrección.")
                    else:
                        supabase.table("usuarios").insert({
                            "nombre": n_nom.upper(), "email": n_ema.lower(), 
                            "password": n_pas, "moneda": n_mon, "id_rol": n_rol[0]
                        }).execute()
                        st.success("✅ Usuario creado."); st.rerun()
                else:
                    st.warning("⚠️ Complete todos los campos.")

    with tab3:
        if not df_raw.empty:
            u_edit = st.selectbox("Usuario a gestionar:", df_raw['nombre'].tolist())
            u_data = df_raw[df_raw['nombre'] == u_edit].iloc[0]
            with st.form("form_edicion"):
                e_nom = st.text_input("Nombre", u_data['nombre'])
                e_ema = st.text_input("Email", u_data['email'])
                idx_rol = list(DICCIONARIO_ROLES.keys()).index(u_data['id_rol'])
                e_rol = st.selectbox("Rol", options=list(DICCIONARIO_ROLES.items()), index=idx_rol, format_func=lambda x: x[1])
                
                if st.form_submit_button("💾 Guardar"):
                    if es_correo_valido(e_ema):
                        supabase.table("usuarios").update({
                            "nombre": e_nom.upper(), "email": e_ema.lower(), "id_rol": e_rol[0]
                        }).eq("id", u_data['id']).execute()
                        st.success("Actualizado"); st.rerun()
                    else:
                        st.error("⚠️ Correo inválido.")
            
            if st.button(f"🗑️ Eliminar a {u_edit}", type="primary"):
                supabase.table("usuarios").delete().eq("id", u_data['id']).execute()
                st.rerun()

    with tab4:
        st.subheader("🛡️ Roles y Facultades")
        # RESTAURADOS LOS ICONOS DE PERMISOS
        permisos_iconos = [
            "👥 Gestión de Usuarios", "💰 Ver Balances", "🧾 Conciliación Bancaria",
            "🚰 Lectura de Suministros", "🏠 Módulo Inmuebles", "📈 Reportes Ocupación"
        ]
        
        c1, c2 = st.columns(2)
        with c1:
            with st.form("nuevo_rol"):
                nr_nom = st.text_input("Nombre del Rol")
                nr_per = st.multiselect("Facultades:", permisos_iconos)
                if st.form_submit_button("Añadir Rol"):
                    supabase.table("roles").insert({"nombre_rol": nr_nom.upper(), "descripcion": "\n".join(nr_per)}).execute()
                    st.rerun()
        
        with c2:
            if not df_roles.empty:
                r_sel = st.selectbox("Seleccione para editar:", df_roles['nombre_rol'].tolist())
                r_dat = df_roles[df_roles['nombre_rol'] == r_sel].iloc[0]
                act = [p.strip() for p in r_dat['descripcion'].split("\n")] if r_dat['descripcion'] else []
                
                with st.form("edit_rol"):
                    er_per = st.multiselect("Editar Facultades:", permisos_iconos, default=[p for p in act if p in permisos_iconos])
                    if st.form_submit_button("Actualizar"):
                        supabase.table("roles").update({"descripcion": "\n".join(er_per)}).eq("id", r_dat['id']).execute()
                        st.success("Permisos actualizados"); st.rerun()