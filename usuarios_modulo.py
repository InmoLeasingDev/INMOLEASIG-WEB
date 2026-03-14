import streamlit as st
import pandas as pd
import re
from fpdf import FPDF

# ==========================================
# 1. FUNCIÓN PDF CON FILAS SINCRONIZADAS (RECARGADA)
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
        
        # --- CÁLCULO DE ALTURA DE FILA ---
        # Determinamos cuántas líneas ocupará el texto más largo
        lineas_por_col = []
        for i, txt in enumerate(textos):
            # Calculamos ancho de texto vs ancho de columna
            ancho_texto = pdf.get_string_width(txt)
            n_lineas = int(ancho_texto / (cw[i] - 2)) + 1
            lineas_por_col.append(n_lineas)
        
        max_l = max(lineas_por_col)
        h_celda = 6 # Altura de cada línea individual
        h_fila = h_celda * max_l # Altura total de la fila sincronizada
        
        # --- DIBUJADO DE CELDAS ---
        x, y = pdf.get_x(), pdf.get_y()
        
        # Celda Nombre
        pdf.multi_cell(cw[0], h_celda, textos[0], border=1)
        pdf.set_xy(x + cw[0], y)
        
        # Celda Email
        pdf.multi_cell(cw[1], h_celda, textos[1], border=1)
        pdf.set_xy(x + cw[0] + cw[1], y)
        
        # Celda Rol (Aquí forzamos que use toda la altura h_fila)
        pdf.multi_cell(cw[2], h_fila / max_l if max_l > 1 else h_fila, textos[2], border=1)
        
        # Reset al final de la fila
        pdf.set_y(y + h_fila)
        
    return pdf.output(dest='S').encode('latin-1')

def es_correo_valido(correo):
    patron = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(patron, correo) is not None

# ==========================================
# 2. MÓDULO PRINCIPAL DE USUARIOS
# ==========================================
def mostrar_modulo_usuarios(supabase):
    st.header("👤 Gestión de Usuarios")
    
    # Carga de datos
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
            busqueda = st.text_input("🔍 Buscar usuario...", "").upper().strip()
            df_display = df_raw.copy().sort_values('nombre')
            df_display['Rol'] = df_display['id_rol'].map(DICCIONARIO_ROLES)
            if busqueda:
                df_display = df_display[df_display['nombre'].str.contains(busqueda)]
            
            st.dataframe(df_display[["nombre", "email", "moneda", "Rol"]], use_container_width=True, hide_index=True)
            
            with st.expander("🛡️ Detalle de Permisos por Usuario", expanded=False):
                u_sel = st.selectbox("Consulte facultades:", ["-- Seleccione --"] + df_display['nombre'].tolist())
                if u_sel != "-- Seleccione --":
                    row_u = df_display[df_display['nombre'] == u_sel].iloc[0]
                    desc = DICCIONARIO_DESC.get(row_u['id_rol'], "Sin permisos.")
                    st.info(f"**Rol:** {row_u['Rol']}\n\n**Facultades:**\n{desc}")
            
            pdf_bytes = generar_pdf_usuarios(df_display, DICCIONARIO_ROLES)
            st.download_button("📄 Descargar Reporte PDF", pdf_bytes, "usuarios.pdf", "application/pdf")

    # --- TAB 2 Y 3: (REGISTRO Y EDICIÓN SE MANTIENEN IGUAL QUE TU ÚLTIMA VERSIÓN) ---
    # ... (Se omiten por brevedad para enfocar en Tab 4 y PDF)

    # --- TAB 4: ROLES Y PERMISOS GRANULARES ---
    with tab4:
        st.subheader("🛡️ Matriz de Acceso por Perfil")
        
        # LISTA DE ACCIONES QUE PROGRAMAREMOS EN EL FUTURO
        opciones_permisos = [
            "📋 Ver Directorio Usuarios",
            "💰 Ver Balances Mensuales",
            "🧾 Conciliación Bancaria",
            "🚰 Ingresar Lecturas de Suministros",
            "🏠 Crear/Editar Inmuebles",
            "📉 Ver Reportes de Ocupación",
            "⚙️ Configuración del Sistema"
        ]
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("**Crear Perfil Nuevo**")
            with st.form("form_nuevo_rol"):
                n_rol_nom = st.text_input("Nombre del Rol")
                n_rol_perm = st.multiselect("Permisos de este Rol:", opciones_permisos)
                if st.form_submit_button("Guardar"):
                    if n_rol_nom:
                        desc_formateada = "\n".join(n_rol_perm)
                        supabase.table("roles").insert({"nombre_rol": n_rol_nom.upper(), "descripcion": desc_formateada}).execute()
                        st.success("Rol creado"); st.rerun()

        with col_b:
            st.markdown("**Modificar Perfil Existente**")
            if not df_roles.empty:
                r_edit = st.selectbox("Seleccione Rol:", df_roles['nombre_rol'].tolist())
                r_actual = df_roles[df_roles['nombre_rol'] == r_edit].iloc[0]
                
                with st.form("form_edit_rol"):
                    # Detectamos permisos previos
                    previos = r_actual['descripcion'].split("\n") if r_actual['descripcion'] else []
                    previos = [p for p in previos if p in opciones_permisos] # Filtro de seguridad
                    
                    e_rol_perm = st.multiselect("Editar Permisos:", opciones_permisos, default=previos)
                    if st.form_submit_button("Actualizar"):
                        desc_upd = "\n".join(e_rol_perm)
                        supabase.table("roles").update({"descripcion": desc_upd}).eq("id", r_actual['id']).execute()
                        st.success("Actualizado"); st.rerun()
                
                if st.button(f"🗑️ Borrar Rol {r_edit}", type="primary"):
                    # Validamos si hay usuarios
                    users_count = df_raw[df_raw['id_rol'] == r_actual['id']].shape[0]
                    if users_count > 0:
                        st.error(f"No puedes borrarlo. {users_count} usuarios lo están usando.")
                    else:
                        supabase.table("roles").delete().eq("id", r_actual['id']).execute()
                        st.success("Borrado"); st.rerun()