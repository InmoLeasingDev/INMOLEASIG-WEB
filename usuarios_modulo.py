import streamlit as st
import pandas as pd
import re
from fpdf import FPDF

# ==========================================
# 1. FUNCIÓN PARA GENERAR EL REPORTE PDF (MEJORADA)
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
    
    col_width = [60, 80, 50] 
    pdf.cell(col_width[0], 10, "NOMBRE", border=1, fill=True)
    pdf.cell(col_width[1], 10, "EMAIL", border=1, fill=True)
    pdf.cell(col_width[2], 10, "ROL", border=1, fill=True)
    pdf.ln()
    
    pdf.set_font("Arial", "", 9)
    for _, row in df.iterrows():
        rol_texto = diccionario_roles.get(row['id_rol'], "SIN ROL")
        
        # Calculamos altura necesaria (estimación por líneas)
        # 1. Obtenemos cuántas líneas ocuparía el texto más largo
        lineas_nombre = pdf.get_string_width(str(row['nombre'])) / col_width[0]
        lineas_email = pdf.get_string_width(str(row['email'])) / col_width[1]
        max_lines = max(int(lineas_nombre) + 1, int(lineas_email) + 1, 1)
        h = 8 * max_lines # Altura de la fila
        
        # Guardamos posición inicial
        x_start = pdf.get_x()
        y_start = pdf.get_y()
        
        # Dibujamos las 3 celdas con la misma altura 'h'
        # Multi_cell con altura h/max_lines para que el texto se distribuya
        pdf.multi_cell(col_width[0], h/max_lines, str(row['nombre']), border=1)
        pdf.set_xy(x_start + col_width[0], y_start)
        
        pdf.multi_cell(col_width[1], h/max_lines, str(row['email']), border=1)
        pdf.set_xy(x_start + col_width[0] + col_width[1], y_start)
        
        pdf.multi_cell(col_width[2], h, str(rol_texto), border=1) # El rol suele ser corto
        
        # Movemos el cursor al final de la fila más alta
        pdf.set_y(y_start + h)
        
    return pdf.output(dest='S').encode('latin-1')

def es_correo_valido(correo):
    patron = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(patron, correo) is not None

# ==========================================
# 2. MÓDULO PRINCIPAL DE USUARIOS
# ==========================================
def mostrar_modulo_usuarios(supabase):
    st.header("👤 Gestión de Usuarios")
    
    # --- CARGA DE DATOS ---
    try:
        res_roles = supabase.table("roles").select("*").execute()
        df_roles = pd.DataFrame(res_roles.data) if res_roles.data else pd.DataFrame()
        DICCIONARIO_ROLES = {rol['id']: rol['nombre_rol'] for rol in res_roles.data}
        DICCIONARIO_DESC = {rol['id']: rol['descripcion'] for rol in res_roles.data}
    except Exception as e:
        st.error(f"Error al cargar roles: {e}")
        df_roles, DICCIONARIO_ROLES, DICCIONARIO_DESC = pd.DataFrame(), {}, {}
        
    res_u = supabase.table("usuarios").select("*").execute()
    df_raw = pd.DataFrame(res_u.data) if res_u.data else pd.DataFrame()
    if not df_raw.empty:
        df_raw = df_raw.sort_values(by='nombre', ascending=True)

    # TABS (4 pestañas ahora)
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Directorio", "➕ Nuevo Usuario", "⚙️ Gestionar", "🛡️ Roles y Permisos"])

    # --- TAB 1: DIRECTORIO ---
    with tab1:
        if not df_raw.empty:
            busqueda = st.text_input("🔍 Buscar usuario...", "").upper().strip()
            df_display = df_raw.copy()
            df_display['Rol'] = df_display['id_rol'].map(DICCIONARIO_ROLES)
            if busqueda:
                df_display = df_display[df_display['nombre'].str.contains(busqueda)]
            
            st.dataframe(df_display[["nombre", "email", "moneda", "Rol"]], use_container_width=True, hide_index=True)

            with st.expander("🛡️ Detalle de Permisos por Usuario", expanded=False):
                nombres_lista = ["-- Seleccione --"] + df_display['nombre'].tolist()
                u_detalle = st.selectbox("Consulte facultades:", nombres_lista)
                if u_detalle != "-- Seleccione --":
                    row_u = df_display[df_display['nombre'] == u_detalle].iloc[0]
                    desc = DICCIONARIO_DESC.get(row_u['id_rol'], "Sin descripción.")
                    st.info(f"**Rol:** {row_u['Rol']}\n\n**Facultades:**\n{desc}")
            
            pdf_bytes = generar_pdf_usuarios(df_display, DICCIONARIO_ROLES)
            st.download_button("📄 Descargar PDF", pdf_bytes, "usuarios.pdf", "application/pdf")

    # --- TAB 2: REGISTRO ---
    with tab2:
        st.subheader("Crear nueva cuenta")
        with st.form("form_registro"):
            c1, c2 = st.columns(2)
            n_nombre = c1.text_input("Nombre Completo")
            n_email = c1.text_input("Correo Electrónico")
            n_pass = c2.text_input("Contraseña Temporal", type="password")
            n_moneda = c2.selectbox("Moneda", ["COP", "USD", "EUR", "ALL"])
            n_rol_sel = st.selectbox("Asignar Rol", options=list(DICCIONARIO_ROLES.items()), format_func=lambda x: x[1])

            if st.form_submit_button("🚀 Registrar Usuario"):
                if n_nombre and n_email and n_pass:
                    if not es_correo_valido(n_email.strip()):
                        st.error("⚠️ Formato de correo inválido.")
                    else:
                        try:
                            supabase.table("usuarios").insert({
                                "nombre": n_nombre.strip().upper(),
                                "email": n_email.strip().lower(),
                                "password": n_pass,
                                "moneda": n_moneda,
                                "id_rol": int(n_rol_sel[0])
                            }).execute()
                            st.success("✅ ¡Registrado!"); st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    st.warning("⚠️ Complete todos los campos.")

    # --- TAB 3: GESTIONAR ---
    with tab3:
        if not df_raw.empty:
            u_sel = st.selectbox("Seleccione usuario para editar/eliminar", df_raw['nombre'].tolist())
            datos_u = df_raw[df_raw['nombre'] == u_sel].iloc[0]
            with st.form("form_edit"):
                e_nom = st.text_input("Nombre", value=datos_u['nombre'])
                e_ema = st.text_input("Email", value=datos_u['email'])
                e_rol = st.selectbox("Rol", options=list(DICCIONARIO_ROLES.items()), 
                                    index=list(DICCIONARIO_ROLES.keys()).index(datos_u['id_rol']), 
                                    format_func=lambda x: x[1])
                if st.form_submit_button("💾 Actualizar"):
                    supabase.table("usuarios").update({
                        "nombre": e_nom.upper(), "email": e_ema.lower(), "id_rol": int(e_rol[0])
                    }).eq("id", datos_u['id']).execute()
                    st.success("Actualizado"); st.rerun()
            if st.button(f"🗑️ Eliminar {u_sel}", type="primary"):
                supabase.table("usuarios").delete().eq("id", datos_u['id']).execute()
                st.rerun()

    # --- TAB 4: ROLES Y PERMISOS (NUEVO) ---
    with tab4:
        st.subheader("🛡️ Configuración de Roles")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**➕ Crear Nuevo Rol**")
            with st.form("nuevo_rol_form", clear_on_submit=True):
                nr_nom = st.text_input("Nombre del Rol (Ej: AUDITOR)")
                nr_des = st.text_area("Descripción de Permisos (use viñetas)")
                if st.form_submit_button("Guardar Rol"):
                    if nr_nom:
                        supabase.table("roles").insert({"nombre_rol": nr_nom.upper(), "descripcion": nr_des}).execute()
                        st.success("Rol creado exitosamente."); st.rerun()

        with col2:
            st.markdown("**⚙️ Gestionar Roles Existentes**")
            if not df_roles.empty:
                r_sel = st.selectbox("Seleccione Rol", df_roles['nombre_rol'].tolist())
                r_data = df_roles[df_roles['nombre_rol'] == r_sel].iloc[0]
                
                with st.form("edit_rol_form"):
                    er_des = st.text_area("Editar Permisos", value=r_data['descripcion'])
                    if st.form_submit_button("Actualizar Descripción"):
                        supabase.table("roles").update({"descripcion": er_des}).eq("id", r_data['id']).execute()
                        st.success("Permisos actualizados."); st.rerun()
                
                # BOTÓN DE ELIMINAR ROL CON SEGURIDAD
                if st.button(f"🗑️ Eliminar Rol: {r_sel}", type="primary"):
                    # Verificar si hay usuarios usándolo
                    usuarios_con_rol = df_raw[df_raw['id_rol'] == r_data['id']]
                    if not usuarios_con_rol.empty:
                        st.error(f"No se puede eliminar: {len(usuarios_con_rol)} usuarios tienen este rol asignado.")
                    else:
                        supabase.table("roles").delete().eq("id", r_data['id']).execute()
                        st.success("Rol eliminado."); st.rerun()