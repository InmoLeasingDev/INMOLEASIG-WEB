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
    
    # --- MEJORA 4: CARGA DINÁMICA DE ROLES Y DESCRIPCIONES ---
    try:
        res_roles = supabase.table("roles").select("id, nombre_rol, descripcion").execute() #
        DICCIONARIO_ROLES = {rol['id']: rol['nombre_rol'] for rol in res_roles.data}
        DICCIONARIO_DESC = {rol['id']: rol['descripcion'] for rol in res_roles.data} # Para la lupa
    except Exception as e:
        st.error(f"Error al cargar roles: {e}")
        DICCIONARIO_ROLES, DICCIONARIO_DESC = {}, {}
        
    # --- CARGA Y ORDEN DE USUARIOS (MEJORA 1) ---
    res = supabase.table("usuarios").select("id, nombre, email, moneda, id_rol").execute()
    df_raw = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    
    if not df_raw.empty:
        # Ordenamos alfabéticamente de menor a mayor (A-Z) [Mejora 1]
        df_raw = df_raw.sort_values(by='nombre', ascending=True)

    tab1, tab2, tab3 = st.tabs(["📋 Directorio", "➕ Nuevo Usuario", "⚙️ Gestionar"])

    # --- TAB 1: DIRECTORIO CON BÚSQUEDA Y LUPA ---
    with tab1:
        if not df_raw.empty:
            # MEJORA 3: BUSCADOR
            busqueda = st.text_input("🔍 Buscar usuario por nombre...", "").upper()
            
            df_display = df_raw.copy()
            df_display['Rol'] = df_display['id_rol'].map(DICCIONARIO_ROLES)
            
            # Aplicar filtro de búsqueda
            if busqueda:
                df_display = df_display[df_display['nombre'].str.contains(busqueda)]
            
            st.dataframe(df_display[["nombre", "email", "moneda", "Rol"]], use_container_width=True)
            
            # MEJORA 4: AMPLIACIÓN DE INFORMACIÓN (LUPA)
            with st.expander("🧐 Detalle de Permisos por Usuario"):
                u_detalle = st.selectbox("Seleccione un usuario para ver sus permisos", df_display['nombre'].tolist())
                if u_detalle:
                    row_u = df_display[df_display['nombre'] == u_detalle].iloc[0]
                    desc_rol = DICCIONARIO_DESC.get(row_u['id_rol'], "Sin descripción disponible.")
                    st.info(f"**Rol:** {row_u['Rol']}\n\n**Permisos actuales:** {desc_rol}") #
            
            pdf_bytes = generar_pdf_usuarios(df_display, DICCIONARIO_ROLES)
            st.download_button("📄 Descargar Reporte PDF", pdf_bytes, "usuarios.pdf", "application/pdf")
        else:
            st.info("No hay usuarios registrados.")

    # --- TAB 2: REGISTRO (Se mantiene sólido) ---
    with tab2:
        st.subheader("Crear nueva cuenta")
        with st.form("form_registro"):
            c1, c2 = st.columns(2)
            with c1:
                n_nombre = st.text_input("Nombre Completo")
                n_email = st.text_input("Correo Electrónico")
            with c2:
                n_pass = st.text_input("Contraseña", type="password")
                n_moneda = st.selectbox("Moneda", ["COP", "USD", "EUR", "ALL"])
            
            opciones_rol = list(DICCIONARIO_ROLES.items()) 
            n_rol_sel = st.selectbox("Asignar Rol", options=opciones_rol, format_func=lambda x: x[1])

            if st.form_submit_button("🚀 Registrar"):
                if n_nombre and n_email:
                    supabase.table("usuarios").insert({
                        "nombre": n_nombre.strip().upper(),
                        "email": n_email.strip().lower(),
                        "password": n_pass,
                        "moneda": n_moneda,
                        "id_rol": n_rol_sel[0]
                    }).execute()
                    st.success("¡Usuario creado con éxito!")
                    st.rerun()

    # --- TAB 3: GESTIONAR (MEJORA 2: ORDEN Y DEFAULT) ---
    with tab3:
        if not df_raw.empty:
            st.subheader("Modificar o Eliminar")
            
            # MEJORA 2: El primero de la lista (ya ordenada A-Z) es el default
            lista_nombres = df_raw['nombre'].tolist()
            u_sel_nombre = st.selectbox("Seleccione usuario para editar", options=lista_nombres)
            
            datos_u = df_raw[df_raw['nombre'] == u_sel_nombre].iloc[0]
            
            with st.form("form_edicion"):
                ce1, ce2 = st.columns(2)
                with ce1:
                    edit_nom = st.text_input("Nombre", value=datos_u['nombre'])
                    edit_ema = st.text_input("Email", value=datos_u['email'])
                with ce2:
                    edit_mon = st.selectbox("Moneda", ["EUR", "COP", "ALL"], 
                                           index=["EUR", "COP", "ALL"].index(datos_u['moneda']))
                    # Encontrar el índice del rol actual para el selectbox
                    ids_posibles = list(DICCIONARIO_ROLES.keys())
                    idx_rol = ids_posibles.index(datos_u['id_rol']) if datos_u['id_rol'] in ids_posibles else 0
                    
                    edit_rol = st.selectbox("Rol", options=list(DICCIONARIO_ROLES.items()), 
                                           index=idx_rol,
                                           format_func=lambda x: x[1])
                
                if st.form_submit_button("💾 Guardar Cambios"):
                    supabase.table("usuarios").update({
                        "nombre": edit_nom.strip().upper(),
                        "email": edit_ema.strip().lower(),
                        "moneda": edit_mon,
                        "id_rol": edit_rol[0]
                    }).eq("id", datos_u['id']).execute()
                    st.success("¡Cambios aplicados!")
                    st.rerun()
            
            st.markdown("---")
            if st.button(f"🗑️ Eliminar a {u_sel_nombre}", type="primary"):
                supabase.table("usuarios").delete().eq("id", datos_u['id']).execute()
                st.rerun()