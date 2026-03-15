import streamlit as st
import pandas as pd
import re
from fpdf import FPDF

# ==========================================
# 1. FUNCIÓN PDF: VERSIÓN PERFECTA (RESTAURADA Y BLINDADA)
# ==========================================
def generar_pdf_usuarios(df, diccionario_roles):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "INMOLEASING - REPORTE DE USUARIOS", ln=True, align="C")
    pdf.ln(5)
    
    # Encabezados
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
        
        # --- CÁLCULO DE ALTURA MÁXIMA ---
        lineas_por_col = []
        for i, txt in enumerate(textos):
            n = len(pdf.multi_cell(cw[i], 7, txt, split_only=True))
            lineas_por_col.append(n)
        
        max_l = max(lineas_por_col)
        h_fila = 7 * max_l 
        
        # --- DIBUJO DE FILA (POR CAPAS Y COORDENADAS MANUALES) ---
        x_ini = pdf.get_x()
        y_ini = pdf.get_y()
        
        # Control de salto de página preventivo
        if y_ini + h_fila > 275:
            pdf.add_page()
            y_ini = pdf.get_y()

        x_actual = x_ini # Llevamos el control manual del eje X
        
        for i, txt in enumerate(textos):
            # 1. Forzamos el cursor a la posición exacta de esta celda
            pdf.set_xy(x_actual, y_ini)
            
            # 2. Dibujamos el marco exterior con la altura máxima
            pdf.rect(x_actual, y_ini, cw[i], h_fila)
            
            # 3. Escribimos el texto (border=0 para no duplicar líneas)
            pdf.multi_cell(cw[i], 7, txt, border=0, align='L')
            
            # 4. Sumamos el ancho de la columna actual para la SIGUIENTE celda
            x_actual += cw[i] 
            
        # Al terminar la fila completa, forzamos el cursor justo debajo para la siguiente fila
        pdf.set_xy(x_ini, y_ini + h_fila)
        
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
    except:
        df_roles, DICCIONARIO_ROLES = pd.DataFrame(), {}
        
    res_u = supabase.table("usuarios").select("*").execute()
    df_raw = pd.DataFrame(res_u.data) if res_u.data else pd.DataFrame()

    tab1, tab2, tab3, tab4 = st.tabs(["📋 Directorio", "➕ Nuevo Usuario", "⚙️ Gestionar", "🛡️ Roles"])

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

    # --- TAB 2: REGISTRO (SIN PÉRDIDA DE DATOS) ---
    with tab2:
        st.subheader("Registrar Colaborador")
        with st.form("form_registro_estable"):
            col1, col2 = st.columns(2)
            n_nom = col1.text_input("Nombre Completo")
            n_ema = col1.text_input("Correo Institucional")
            n_pas = col2.text_input("Password", type="password")
            n_mon = col2.selectbox("Moneda Base", ["COP", "USD", "EUR"])
            n_rol = st.selectbox("Rol Asignado", options=list(DICCIONARIO_ROLES.items()), format_func=lambda x: x[1])
            
            if st.form_submit_button("✅ Crear Usuario"):
                if n_nom and n_ema and n_pas:
                    if not es_correo_valido(n_ema):
                        st.error("❌ El formato del correo es inválido. Los datos se mantienen para corrección.")
                    else:
                        supabase.table("usuarios").insert({
                            "nombre": n_nom.upper(), "email": n_ema.lower(), 
                            "password": n_pas, "moneda": n_mon, "id_rol": n_rol[0]
                        }).execute()
                        st.success(f"¡Usuario {n_nom.upper()} creado!"); st.rerun()
                else:
                    st.warning("⚠️ Todos los campos son obligatorios.")

    # --- TAB 3: GESTIONAR ---
    with tab3:
        if not df_raw.empty:
            u_edit = st.selectbox("Seleccione para editar/eliminar:", df_raw['nombre'].tolist())
            u_data = df_raw[df_raw['nombre'] == u_edit].iloc[0]
            with st.form("form_edicion"):
                e_nom = st.text_input("Nombre", u_data['nombre'])
                e_ema = st.text_input("Email", u_data['email'])
                index_rol = list(DICCIONARIO_ROLES.keys()).index(u_data['id_rol'])
                e_rol = st.selectbox("Cambiar Rol", options=list(DICCIONARIO_ROLES.items()), index=index_rol, format_func=lambda x: x[1])
                if st.form_submit_button("💾 Guardar Cambios"):
                    if es_correo_valido(e_ema):
                        supabase.table("usuarios").update({
                            "nombre": e_nom.upper(), "email": e_ema.lower(), "id_rol": e_rol[0]
                        }).eq("id", u_data['id']).execute()
                        st.success("Cambios aplicados."); st.rerun()
                    else:
                        st.error("❌ Correo inválido.")
            if st.button(f"🗑️ Eliminar a {u_edit}", type="primary"):
                supabase.table("usuarios").delete().eq("id", u_data['id']).execute()
                st.rerun()

    # --- TAB 4: ROLES Y PERMISOS (CON ICONOS) ---
    with tab4:
        st.subheader("🛡️ Matriz de Permisos")
        llaves_iconos = [
            "👥 MODULO_USUARIOS", "🤝 MODULO_PROPIETARIOS", "🏠 MODULO_INMUEBLES", 
            "🏦 MODULO_BANCOS", "🚰 LECTURA_SUMINISTROS", "💰 VER_BALANCES", "🧾 CONCILIACION_BANCARIA"
        ]
        c1, c2 = st.columns(2)
        with c1:
            with st.form("n_rol_form"):
                nr_nom = st.text_input("Nombre del nuevo Rol")
                nr_llaves = st.multiselect("Asignar Facultades:", llaves_iconos)
                if st.form_submit_button("Crear Perfil"):
                    if nr_nom:
                        supabase.table("roles").insert({"nombre_rol": nr_nom.upper(), "descripcion": ", ".join(nr_llaves)}).execute()
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
                        st.success("Permisos actualizados."); st.rerun()