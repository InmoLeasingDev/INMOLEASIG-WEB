import streamlit as st
import pandas as pd
import re
from fpdf import FPDF

# ==========================================
# 1. FUNCIÓN PDF CON FILAS SINCRONIZADAS (ELIMINA EL DESCUADRE)
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
    
    cw = [55, 85, 50] # Anchos de columna
    headers = ["NOMBRE", "EMAIL", "ROL"]
    for i, h_text in enumerate(headers):
        pdf.cell(cw[i], 10, h_text, border=1, fill=True, align="C")
    pdf.ln()
    
    pdf.set_font("Arial", "", 9)
    for _, row in df.iterrows():
        rol_texto = diccionario_roles.get(row['id_rol'], "SIN ROL")
        textos = [str(row['nombre']), str(row['email']), str(rol_texto)]
        
        # --- PASO 1: Calcular altura máxima de la fila ---
        alturas = []
        for i, txt in enumerate(textos):
            # Calculamos cuántas líneas ocupará el texto en ese ancho
            n_lineas = pdf.get_string_width(txt) / (cw[i] - 2)
            alturas.append(int(n_lineas) + 1)
        
        max_l = max(alturas)
        h_fila = 6 * max_l # 6mm por línea de texto
        
        # --- PASO 2: Dibujar la fila sincronizada ---
        x_ini, y_ini = pdf.get_x(), pdf.get_y()
        
        # Dibujamos primero los bordes de la fila completa para que coincidan
        for i, w in enumerate(cw):
            # Dibujamos un rectángulo vacío que sirve de borde perfecto
            pdf.rect(pdf.get_x(), y_ini, w, h_fila)
            # Ponemos el texto dentro sin bordes individuales (ya dibujamos el rect)
            pdf.multi_cell(w, 6, textos[i], border=0, align='L')
            # Volvemos arriba para la siguiente columna
            pdf.set_xy(pdf.get_x() + w, y_ini)
            
        pdf.ln(h_fila) # Saltamos a la siguiente fila real
        
    return pdf.output(dest='S').encode('latin-1')

def es_correo_valido(correo):
    patron = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(patron, correo) is not None

# ==========================================
# 2. MÓDULO PRINCIPAL DE USUARIOS
# ==========================================
def mostrar_modulo_usuarios(supabase):
    st.header("👤 Gestión de Usuarios")
    
    # Carga de datos base
    try:
        res_roles = supabase.table("roles").select("*").execute()
        df_roles = pd.DataFrame(res_roles.data) if res_roles.data else pd.DataFrame()
        DICCIONARIO_ROLES = {rol['id']: rol['nombre_rol'] for rol in res_roles.data}
        DICCIONARIO_DESC = {rol['id']: rol['descripcion'] for rol in res_roles.data}
    except:
        df_roles, DICCIONARIO_ROLES, DICCIONARIO_DESC = pd.DataFrame(), {}, {}
        
    res_u = supabase.table("usuarios").select("*").execute()
    df_raw = pd.DataFrame(res_u.data) if res_u.data else pd.DataFrame()

    tab1, tab2, tab3, tab4 = st.tabs(["📋 Directorio", "➕ Nuevo Usuario", "⚙️ Gestionar", "🛡️ Roles y Permisos"])

    # --- TAB 1: DIRECTORIO ---
    with tab1:
        if not df_raw.empty:
            busqueda = st.text_input("🔍 Buscar por nombre...", "").upper().strip()
            df_display = df_raw.copy().sort_values('nombre')
            df_display['Rol'] = df_display['id_rol'].map(DICCIONARIO_ROLES)
            if busqueda:
                df_display = df_display[df_display['nombre'].str.contains(busqueda)]
            
            st.dataframe(df_display[["nombre", "email", "moneda", "Rol"]], use_container_width=True, hide_index=True)
            
            # --- SECCIÓN DE PERMISOS ---
            st.markdown("---")
            st.subheader("🛡️ Consulta de Facultades")
            u_sel = st.selectbox("Seleccione un usuario para ver qué puede hacer:", ["-- Seleccione --"] + df_display['nombre'].tolist())
            if u_sel != "-- Seleccione --":
                row_u = df_display[df_display['nombre'] == u_sel].iloc[0]
                st.info(f"**Permisos asignados a {u_sel}:**\n\n{DICCIONARIO_DESC.get(row_u['id_rol'], 'No tiene permisos definidos.')}")
            
            pdf_bytes = generar_pdf_usuarios(df_display, DICCIONARIO_ROLES)
            st.download_button("📄 Exportar Reporte PDF", pdf_bytes, "reporte_usuarios.pdf", "application/pdf")

    # --- TAB 4: ROLES (EL "CEREBRO" DE LOS PERMISOS) ---
    with tab4:
        st.subheader("🛡️ Configuración de Roles")
        st.write("Aquí defines qué 'llaves' tiene cada grupo de usuarios.")
        
        # Definimos las "llaves" del sistema
        permisos_maestros = [
            "MODULO_USUARIOS", "MODULO_PROPIETARIOS", "MODULO_INMUEBLES", 
            "MODULO_BANCOS", "LECTURA_CONTADORES", "VER_BALANCES", "CONCILIACION_BANCARIA"
        ]
        
        col_izq, col_der = st.columns(2)
        
        with col_izq:
            st.write("**Crear Nuevo Rol**")
            with st.form("nuevo_rol_form"):
                n_rol = st.text_input("Nombre (Ej: CONTADOR)")
                n_perm = st.multiselect("Asignar Permisos:", permisos_maestros)
                if st.form_submit_button("Crear Perfil"):
                    if n_rol:
                        desc_p = ", ".join(n_perm)
                        supabase.table("roles").insert({"nombre_rol": n_rol.upper(), "descripcion": desc_p}).execute()
                        st.success("Rol creado con éxito"); st.rerun()

        with col_der:
            st.write("**Modificar Permisos**")
            if not df_roles.empty:
                r_edit = st.selectbox("Seleccionar Rol para editar:", df_roles['nombre_rol'].tolist())
                r_id = df_roles[df_roles['nombre_rol'] == r_edit]['id'].values[0]
                
                # Convertimos el texto de la DB en lista para el multiselect
                desc_actual = df_roles[df_roles['nombre_rol'] == r_edit]['descripcion'].values[0]
                lista_actual = [p.strip() for p in desc_actual.split(",")] if desc_actual else []
                
                with st.form("edit_rol_form"):
                    e_perm = st.multiselect("Actualizar Permisos:", permisos_maestros, default=[p for p in lista_actual if p in permisos_maestros])
                    if st.form_submit_button("Guardar Cambios"):
                        nueva_desc = ", ".join(e_perm)
                        supabase.table("roles").update({"descripcion": nueva_desc}).eq("id", r_id).execute()
                        st.success("Permisos actualizados"); st.rerun()