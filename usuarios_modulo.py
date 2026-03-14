import streamlit as st
import pandas as pd
import re
from fpdf import FPDF

# ==========================================
# 1. FUNCIÓN PARA GENERAR EL REPORTE PDF (FIX ALINEACIÓN TOTAL)
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
    
    # Definimos anchos fijos
    cw = [55, 85, 50] 
    headers = ["NOMBRE", "EMAIL", "ROL"]
    for i, h_text in enumerate(headers):
        pdf.cell(cw[i], 10, h_text, border=1, fill=True, align="C")
    pdf.ln()
    
    pdf.set_font("Arial", "", 9)
    for _, row in df.iterrows():
        rol_texto = diccionario_roles.get(row['id_rol'], "SIN ROL")
        
        # --- LÓGICA DE ALTURA SINCRONIZADA ---
        # Calculamos cuántas líneas ocupa cada celda para hallar la altura máxima del bloque
        # Esto soluciona el error visual donde las celdas quedaban cortas
        textos = [str(row['nombre']), str(row['email']), str(rol_texto)]
        
        # Estimamos líneas por columna (ancho de letra promedio ~2mm)
        lineas = []
        for i, txt in enumerate(textos):
            l = pdf.get_string_width(txt) / cw[i]
            lineas.append(int(l) + 1)
        
        max_l = max(lineas)
        h_fila = 7 * max_l # Altura base de 7mm por línea
        
        # Dibujamos las celdas de la fila una por una manteniendo el Y
        x_start, y_start = pdf.get_x(), pdf.get_y()
        
        # Celda 1 (Nombre)
        pdf.multi_cell(cw[0], h_fila/max_l, textos[0], border=1)
        pdf.set_xy(x_start + cw[0], y_start)
        
        # Celda 2 (Email)
        pdf.multi_cell(cw[1], h_fila/max_l, textos[1], border=1)
        pdf.set_xy(x_start + cw[0] + cw[1], y_start)
        
        # Celda 3 (Rol)
        pdf.multi_cell(cw[2], h_fila/max_l, textos[2], border=1)
        
        # El cursor queda al final de la fila más alta automáticamente para la siguiente
    
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

    tab1, tab2, tab3, tab4 = st.tabs(["📋 Directorio", "➕ Nuevo Usuario", "⚙️ Gestionar", "🛡️ Roles y Permisos"])

    # --- TAB 1: DIRECTORIO ---
    with tab1:
        if not df_raw.empty:
            busqueda = st.text_input("🔍 Buscar por nombre...", "").upper().strip()
            df_display = df_raw.copy()
            df_display['Rol'] = df_display['id_rol'].map(DICCIONARIO_ROLES)
            if busqueda:
                df_display = df_display[df_display['nombre'].str.contains(busqueda)]
            
            st.dataframe(df_display[["nombre", "email", "moneda", "Rol"]], use_container_width=True, hide_index=True)
            
            with st.expander("👁️ Ver Permisos Detallados", expanded=False):
                u_sel = st.selectbox("Seleccione un usuario:", ["-- Seleccione --"] + df_display['nombre'].tolist())
                if u_sel != "-- Seleccione --":
                    row_u = df_display[df_display['nombre'] == u_sel].iloc[0]
                    st.info(f"**Facultades asignadas:**\n\n{DICCIONARIO_DESC.get(row_u['id_rol'], 'Sin permisos definidos.')}")
            
            pdf_bytes = generar_pdf_usuarios(df_display, DICCIONARIO_ROLES)
            st.download_button("📄 Exportar Reporte PDF", pdf_bytes, "usuarios_inmoleasing.pdf", "application/pdf")

    # --- TAB 2: REGISTRO (SIN BORRADO DE DATOS SI HAY ERROR) ---
    with tab2:
        st.subheader("Registrar Colaborador")
        with st.form("registro_persistente"):
            col1, col2 = st.columns(2)
            n_nom = col1.text_input("Nombre Completo")
            n_ema = col1.text_input("Correo")
            n_pas = col2.text_input("Password", type="password")
            n_mon = col2.selectbox("Moneda Base", ["COP", "USD", "EUR", "ALL"])
            n_rol = st.selectbox("Rol", options=list(DICCIONARIO_ROLES.items()), format_func=lambda x: x[1])
            
            if st.form_submit_button("✅ Crear Cuenta"):
                if n_nom and n_ema and n_pas:
                    if not es_correo_valido(n_ema):
                        st.error("⚠️ El correo no tiene un formato válido.")
                    else:
                        supabase.table("usuarios").insert({
                            "nombre": n_nom.upper(), "email": n_ema.lower(), 
                            "password": n_pas, "moneda": n_mon, "id_rol": n_rol[0]
                        }).execute()
                        st.success("Usuario creado."); st.rerun()
                else:
                    st.warning("Complete todos los campos.")

    # --- TAB 3: GESTIONAR (EDITAR / ELIMINAR) ---
    with tab3:
        if not df_raw.empty:
            u_edit = st.selectbox("Usuario a modificar:", df_raw['nombre'].tolist())
            u_data = df_raw[df_raw['nombre'] == u_edit].iloc[0]
            with st.form("edicion_u"):
                e_nom = st.text_input("Nombre", u_data['nombre'])
                e_ema = st.text_input("Email", u_data['email'])
                e_rol = st.selectbox("Cambiar Rol", options=list(DICCIONARIO_ROLES.items()), 
                                    index=list(DICCIONARIO_ROLES.keys()).index(u_data['id_rol']), 
                                    format_func=lambda x: x[1])
                if st.form_submit_button("💾 Guardar Cambios"):
                    supabase.table("usuarios").update({
                        "nombre": e_nom.upper(), "email": e_ema.lower(), "id_rol": e_rol[0]
                    }).eq("id", u_data['id']).execute()
                    st.success("Datos actualizados"); st.rerun()
            
            if st.button(f"🗑️ Eliminar permanentemente a {u_edit}", type="primary"):
                supabase.table("usuarios").delete().eq("id", u_data['id']).execute()
                st.rerun()

    # --- TAB 4: ROLES Y PERMISOS (GESTIÓN ESTRUCTURADA) ---
    with tab4:
        st.subheader("🛡️ Centro de Control de Permisos")
        
        # Acciones predefinidas para facilitar la gestión
        permisos_sugeridos = ["Ver Inmuebles", "Crear Arrendamientos", "Eliminar Registros", "Exportar PDF", "Ver Reportes Financieros", "Gestionar Bancos"]
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Crear Perfil de Acceso**")
            with st.form("nuevo_perfil", clear_on_submit=True):
                nr_nom = st.text_input("Nombre del Perfil (Ej: AUDITOR)")
                nr_perm = st.multiselect("Asignar Facultades:", permisos_sugeridos)
                if st.form_submit_button("➕ Crear Rol"):
                    if nr_nom:
                        desc_final = "\n".join([f"• {p}" for p in nr_perm])
                        supabase.table("roles").insert({"nombre_rol": nr_nom.upper(), "descripcion": desc_final}).execute()
                        st.success("Perfil creado"); st.rerun()
        
        with c2:
            st.markdown("**Editar/Eliminar Perfiles**")
            if not df_roles.empty:
                r_sel = st.selectbox("Seleccionar Perfil", df_roles['nombre_rol'].tolist())
                r_id = df_roles[df_roles['nombre_rol'] == r_sel]['id'].values[0]
                r_desc = df_roles[df_roles['nombre_rol'] == r_sel]['descripcion'].values[0]
                
                with st.form("edit_perfil"):
                    er_desc = st.text_area("Modificar Facultades (Lista):", value=r_desc, height=150)
                    if st.form_submit_button("💾 Actualizar Perfil"):
                        supabase.table("roles").update({"descripcion": er_desc}).eq("id", r_id).execute()
                        st.success("Permisos actualizados"); st.rerun()
                
                if st.button(f"🗑️ Eliminar Rol {r_sel}", type="primary", help="Solo se puede eliminar si no hay usuarios usándolo"):
                    usuarios_con_ese_rol = df_raw[df_raw['id_rol'] == r_id]
                    if not usuarios_con_ese_rol.empty:
                        st.error(f"⚠️ Error: Hay {len(usuarios_con_ese_rol)} usuarios con este rol. Cámbialos primero.")
                    else:
                        supabase.table("roles").delete().eq("id", r_id).execute()
                        st.success("Rol eliminado"); st.rerun()