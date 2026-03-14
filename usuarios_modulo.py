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
    
    # 1. Carga Dinámica de Roles y Descripciones
    try:
        res_roles = supabase.table("roles").select("id, nombre_rol, descripcion").execute()
        DICCIONARIO_ROLES = {rol['id']: rol['nombre_rol'] for rol in res_roles.data}
        DICCIONARIO_DESC = {rol['id']: rol['descripcion'] for rol in res_roles.data}
    except Exception as e:
        st.error(f"Error al cargar roles: {e}")
        DICCIONARIO_ROLES, DICCIONARIO_DESC = {}, {}
        
    # 2. Carga y Orden de Usuarios (A-Z)
    try:
        res = supabase.table("usuarios").select("id, nombre, email, moneda, id_rol").execute()
        df_raw = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if not df_raw.empty:
            df_raw = df_raw.sort_values(by='nombre', ascending=True)
    except Exception as e:
        st.error(f"Error al cargar usuarios: {e}")
        df_raw = pd.DataFrame()

    tab1, tab2, tab3 = st.tabs(["📋 Directorio", "➕ Nuevo Usuario", "⚙️ Gestionar"])

    # --- TAB 1: DIRECTORIO CON FOCO DINÁMICO 🛡️ ---
    with tab1:
        if not df_raw.empty:
            # Buscador
            col_b, _ = st.columns([2, 2])
            with col_b:
                busqueda = st.text_input("🔍 Buscar usuario por nombre...", "").upper().strip()
            
            df_display = df_raw.copy()
            df_display['Rol'] = df_display['id_rol'].map(DICCIONARIO_ROLES)
            
            if busqueda:
                df_display = df_display[df_display['nombre'].str.contains(busqueda)]
            
            # --- MEJORA 2: GRID CON SELECCIÓN (FOCO) ---
            # Mostramos el dataframe y capturamos la selección del usuario
            # Nota: Requiere Streamlit 1.35.0 o superior
            seleccion = st.dataframe(
                df_display[["nombre", "email", "moneda", "Rol"]],
                use_container_width=True,
                hide_index=True,
                selection_mode="single_row",
                on_select="rerun"
            )

            # Determinamos quién es el usuario con el "foco"
            usuario_foco_nombre = None
            if seleccion and len(seleccion.selection.rows) > 0:
                idx_seleccionado = seleccion.selection.rows[0]
                usuario_foco_nombre = df_display.iloc[idx_seleccionado]['nombre']

            # --- MEJORA 1: ICONO DE ESCUDO 🛡️ ---
            # El expander se abre automáticamente si hay alguien seleccionado en el grid
            with st.expander("🛡️ Detalle de Permisos y Rol", expanded=True if usuario_foco_nombre else False):
                nombres_lista = df_display['nombre'].tolist()
                
                if nombres_lista:
                    # Sincronizamos el selectbox con la selección del grid
                    idx_default = 0
                    if usuario_foco_nombre:
                        try:
                            idx_default = nombres_lista.index(usuario_foco_nombre)
                        except ValueError:
                            idx_default = 0
                    
                    u_detalle = st.selectbox("Usuario seleccionado:", nombres_lista, index=idx_default)
                    
                    if u_detalle:
                        row_u = df_display[df_display['nombre'] == u_detalle].iloc[0]
                        desc_rol = DICCIONARIO_DESC.get(row_u['id_rol'], "Sin descripción disponible.")
                        st.info(f"**Rol:** {row_u['Rol']}\n\n**Permisos:** {desc_rol}")
                else:
                    st.warning("No hay usuarios para mostrar.")
            
            pdf_bytes = generar_pdf_usuarios(df_display, DICCIONARIO_ROLES)
            st.download_button("📄 Descargar PDF", pdf_bytes, "usuarios.pdf", "application/pdf")
        else:
            st.info("No hay usuarios registrados.")

    # --- TAB 2: REGISTRO ---
    with tab2:
        st.subheader("Crear nueva cuenta")
        with st.form("form_registro"):
            c1, c2 = st.columns(2)
            with c1:
                n_nombre = st.text_input("Nombre Completo")
                n_email = st.text_input("Correo Electrónico")
            with c2:
                n_pass = st.text_input("Contraseña Temporal", type="password")
                n_moneda = st.selectbox("Moneda", ["COP", "USD", "EUR", "ALL"])
            
            opciones_rol = list(DICCIONARIO_ROLES.items()) 
            if opciones_rol:
                n_rol_sel = st.selectbox("Asignar Rol", options=opciones_rol, format_func=lambda x: x[1])
            
            if st.form_submit_button("🚀 Registrar"):
                if n_nombre and n_email and n_pass:
                    try:
                        supabase.table("usuarios").insert({
                            "nombre": n_nombre.strip().upper(),
                            "email": n_email.strip().lower(),
                            "password": n_pass,
                            "moneda": n_moneda,
                            "id_rol": n_rol_sel[0]
                        }).execute()
                        st.success("Usuario creado.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Faltan datos obligatorios.")

    # --- TAB 3: GESTIONAR ---
    with tab3:
        if not df_raw.empty:
            st.subheader("Modificar o Eliminar")
            lista_nombres = df_raw['nombre'].tolist()
            u_sel_nombre = st.selectbox("Usuario a gestionar", options=lista_nombres)
            
            datos_u = df_raw[df_raw['nombre'] == u_sel_nombre].iloc[0]
            
            with st.form("form_edicion"):
                ce1, ce2 = st.columns(2)
                with ce1:
                    edit_nom = st.text_input("Nombre", value=datos_u['nombre'])
                    edit_ema = st.text_input("Email", value=datos_u['email'])
                with ce2:
                    edit_mon = st.selectbox("Moneda", ["COP", "USD", "EUR", "ALL"], 
                                           index=["COP", "USD", "EUR", "ALL"].index(datos_u['moneda']))
                    ids_roles = list(DICCIONARIO_ROLES.keys())
                    idx_rol_act = ids_roles.index(datos_u['id_rol']) if datos_u['id_rol'] in ids_roles else 0
                    edit_rol = st.selectbox("Rol", options=list(DICCIONARIO_ROLES.items()), 
                                           index=idx_rol_act, format_func=lambda x: x[1])
                
                if st.form_submit_button("💾 Guardar Cambios"):
                    try:
                        supabase.table("usuarios").update({
                            "nombre": edit_nom.strip().upper(),
                            "email": edit_ema.strip().lower(),
                            "moneda": edit_mon,
                            "id_rol": edit_rol[0]
                        }).eq("id", datos_u['id']).execute()
                        st.success("Actualizado.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
            
            st.markdown("---")
            if st.button(f"🗑️ Eliminar a {u_sel_nombre}", type="primary"):
                supabase.table("usuarios").delete().eq("id", datos_u['id']).execute()
                st.rerun()