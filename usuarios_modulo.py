import streamlit as st
import pandas as pd
import re
from fpdf import FPDF

# ==========================================
# 1. FUNCIÓN PARA GENERAR EL REPORTE PDF (FIX DESBORDE)
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
    
    col_width = [60, 80, 50] # Anchos de columna
    pdf.cell(col_width[0], 10, "NOMBRE", border=1, fill=True)
    pdf.cell(col_width[1], 10, "EMAIL", border=1, fill=True)
    pdf.cell(col_width[2], 10, "ROL", border=1, fill=True)
    pdf.ln()
    
    pdf.set_font("Arial", "", 9)
    for _, row in df.iterrows():
        rol_texto = diccionario_roles.get(row['id_rol'], "SIN ROL")
        
        # Calculamos la altura necesaria para la fila basada en el texto más largo
        # Esto evita el solapamiento visto en la imagen image_c2df67.png
        x_start = pdf.get_x()
        y_start = pdf.get_y()
        
        # Multi_cell para permitir saltos de línea en nombres largos
        pdf.multi_cell(col_width[0], 8, str(row['nombre']), border=1)
        alt_nombre = pdf.get_y()
        
        pdf.set_xy(x_start + col_width[0], y_start)
        pdf.multi_cell(col_width[1], 8, str(row['email']), border=1)
        alt_email = pdf.get_y()
        
        pdf.set_xy(x_start + col_width[0] + col_width[1], y_start)
        pdf.multi_cell(col_width[2], 8, str(rol_texto), border=1)
        alt_rol = pdf.get_y()
        
        # Saltamos a la posición de la fila más alta para la siguiente iteración
        pdf.set_y(max(alt_nombre, alt_email, alt_rol))
        
    return pdf.output(dest='S').encode('latin-1')

def es_correo_valido(correo):
    patron = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(patron, correo) is not None

# ==========================================
# 2. MÓDULO PRINCIPAL DE USUARIOS
# ==========================================
def mostrar_modulo_usuarios(supabase):
    st.header("👤 Gestión de Usuarios")
    
    try:
        res_roles = supabase.table("roles").select("id, nombre_rol, descripcion").execute()
        DICCIONARIO_ROLES = {rol['id']: rol['nombre_rol'] for rol in res_roles.data}
        DICCIONARIO_DESC = {rol['id']: rol['descripcion'] for rol in res_roles.data}
    except Exception as e:
        st.error(f"Error al cargar roles: {e}")
        DICCIONARIO_ROLES, DICCIONARIO_DESC = {}, {}
        
    res = supabase.table("usuarios").select("id, nombre, email, moneda, id_rol").execute()
    df_raw = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    if not df_raw.empty:
        df_raw = df_raw.sort_values(by='nombre', ascending=True)

    tab1, tab2, tab3 = st.tabs(["📋 Directorio", "➕ Nuevo Usuario", "⚙️ Gestionar"])

    with tab1:
        if not df_raw.empty:
            col_b, _ = st.columns([2, 2])
            with col_b:
                busqueda = st.text_input("🔍 Buscar usuario...", "").upper().strip()
            
            df_display = df_raw.copy()
            df_display['Rol'] = df_display['id_rol'].map(DICCIONARIO_ROLES)
            
            if busqueda:
                df_display = df_display[df_display['nombre'].str.contains(busqueda)]
            
            st.dataframe(df_display[["nombre", "email", "moneda", "Rol"]], use_container_width=True, hide_index=True)

            with st.expander("🛡️ Detalle de Permisos y Rol", expanded=False):
                nombres_lista = ["-- Seleccione un usuario --"] + df_display['nombre'].tolist()
                u_detalle = st.selectbox("Consulte las facultades:", nombres_lista)
                if u_detalle != "-- Seleccione un usuario --":
                    row_u = df_display[df_display['nombre'] == u_detalle].iloc[0]
                    desc_rol = DICCIONARIO_DESC.get(row_u['id_rol'], "Sin descripción.")
                    st.info(f"**Rol:** {row_u['Rol']}\n\n**Facultades:** {desc_rol}")
            
            pdf_bytes = generar_pdf_usuarios(df_display, DICCIONARIO_ROLES)
            st.download_button("📄 Descargar Reporte PDF", pdf_bytes, "usuarios.pdf", "application/pdf")

    # --- TAB 2: REGISTRO (CON PERSISTENCIA Y VALIDACIÓN) ---
    with tab2:
        st.subheader("Crear nueva cuenta")
        # Quitamos clear_on_submit para que los datos no se borren si hay error
        with st.form("form_registro"):
            c1, c2 = st.columns(2)
            with c1:
                n_nombre = st.text_input("Nombre Completo")
                n_email = st.text_input("Correo Electrónico")
            with c2:
                n_pass = st.text_input("Contraseña Temporal", type="password")
                n_moneda = st.selectbox("Moneda", ["COP", "USD", "EUR", "ALL"])
            
            opciones_rol = list(DICCIONARIO_ROLES.items()) 
            n_rol_sel = st.selectbox("Asignar Rol", options=opciones_rol, format_func=lambda x: x[1])

            if st.form_submit_button("🚀 Registrar Usuario"):
                if n_nombre and n_email and n_pass:
                    if not es_correo_valido(n_email.strip()):
                        st.error("⚠️ Formato de correo inválido. Corrija para continuar.")
                    else:
                        try:
                            id_rol_final = int(n_rol_sel[0])
                            supabase.table("usuarios").insert({
                                "nombre": n_nombre.strip().upper(),
                                "email": n_email.strip().lower(),
                                "password": n_pass,
                                "moneda": n_moneda,
                                "id_rol": id_rol_final
                            }).execute()
                            st.success("✅ ¡Usuario registrado!")
                            st.rerun() # Aquí sí reiniciamos porque fue exitoso
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    st.warning("⚠️ Complete todos los campos.")

    with tab3:
        if not df_raw.empty:
            st.subheader("Modificar o Eliminar")
            u_sel_nombre = st.selectbox("Usuario a gestionar", options=df_raw['nombre'].tolist())
            datos_u = df_raw[df_raw['nombre'] == u_sel_nombre].iloc[0]
            
            with st.form("form_edicion"):
                ce1, ce2 = st.columns(2)
                with ce1:
                    edit_nom = st.text_input("Nombre", value=datos_u['nombre'])
                    edit_ema = st.text_input("Email", value=datos_u['email'])
                with ce2:
                    edit_mon = st.selectbox("Moneda", ["COP", "USD", "EUR", "ALL"], 
                                           index=["COP", "USD", "EUR", "ALL"].index(datos_u['moneda']))
                    edit_rol = st.selectbox("Rol", options=list(DICCIONARIO_ROLES.items()), 
                                           index=list(DICCIONARIO_ROLES.keys()).index(datos_u['id_rol']), 
                                           format_func=lambda x: x[1])
                
                if st.form_submit_button("💾 Guardar Cambios"):
                    if not es_correo_valido(edit_ema.strip()):
                        st.error("⚠️ Correo inválido.")
                    else:
                        supabase.table("usuarios").update({
                            "nombre": edit_nom.strip().upper(),
                            "email": edit_ema.strip().lower(),
                            "moneda": edit_mon,
                            "id_rol": int(edit_rol[0])
                        }).eq("id", datos_u['id']).execute()
                        st.success("Cambios aplicados.")
                        st.rerun()
            
            if st.button(f"🗑️ Eliminar a {u_sel_nombre}", type="primary"):
                supabase.table("usuarios").delete().eq("id", datos_u['id']).execute()
                st.rerun()