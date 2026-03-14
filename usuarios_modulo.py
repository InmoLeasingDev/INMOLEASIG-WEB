import streamlit as st
import pandas as pd
import re
from fpdf import FPDF

# ==========================================
# 1. FUNCIÓN PDF: ALINEACIÓN MATEMÁTICA
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
    
    cw = [55, 85, 50] # Anchos: Nombre, Email, Rol
    headers = ["NOMBRE", "EMAIL", "ROL"]
    for i, h_text in enumerate(headers):
        pdf.cell(cw[i], 10, h_text, border=1, fill=True, align="C")
    pdf.ln()
    
    pdf.set_font("Arial", "", 9)
    for _, row in df.iterrows():
        rol_texto = diccionario_roles.get(row['id_rol'], "SIN ROL")
        textos = [str(row['nombre']), str(row['email']), str(rol_texto)]
        
        # --- CÁLCULO DE ALTURA REAL ---
        # Dividimos el texto en líneas según el ancho de columna
        lineas_col = []
        for i, txt in enumerate(textos):
            # Multi_cell divide internamente; calculamos cuántas líneas saldrán
            # Dividimos por (ancho - margen) para ser conservadores
            n = len(pdf.multi_cell(cw[i], 7, txt, split_only=True))
            lineas_col.append(n)
        
        max_lineas = max(lineas_col)
        h_fila = 7 * max_lineas # Altura total de la fila sincronizada
        
        # --- DIBUJO DE CELDAS SINCRONIZADAS ---
        x_actual, y_actual = pdf.get_x(), pdf.get_y()
        
        # Si la fila no cabe en la página, saltamos
        if y_actual + h_fila > 270:
            pdf.add_page()
            y_actual = pdf.get_y()

        for i, txt in enumerate(textos):
            # Dibujamos el RECUADRO vacío con la altura máxima
            pdf.rect(x_actual, y_actual, cw[i], h_fila)
            # Escribimos el TEXTO dentro (sin borde, para no duplicar)
            pdf.multi_cell(cw[i], 7, txt, border=0, align='L')
            # Movemos a la derecha para la siguiente celda
            x_actual += cw[i]
            pdf.set_xy(x_actual, y_actual)
            
        pdf.ln(h_fila) # Salto de línea real al final de la fila
        
    return pdf.output(dest='S').encode('latin-1')

def es_correo_valido(correo):
    patron = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(patron, correo) is not None

# ==========================================
# 2. MÓDULO PRINCIPAL
# ==========================================
def mostrar_modulo_usuarios(supabase):
    st.header("👤 Gestión de Usuarios")
    
    # --- CARGA DE DATOS ---
    try:
        res_roles = supabase.table("roles").select("*").execute()
        df_roles = pd.DataFrame(res_roles.data) if res_roles.data else pd.DataFrame()
        DICCIONARIO_ROLES = {rol['id']: rol['nombre_rol'] for rol in res_roles.data}
        DICCIONARIO_DESC = {rol['id']: rol['descripcion'] for rol in res_roles.data}
    except:
        df_roles, DICCIONARIO_ROLES, DICCIONARIO_DESC = pd.DataFrame(), {}, {}
        
    res_u = supabase.table("usuarios").select("*").execute()
    df_raw = pd.DataFrame(res_u.data) if res_u.data else pd.DataFrame()

    # Reemplazamos la selección en tabla (que fallaba) por Tabs estables
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Directorio", "➕ Nuevo Usuario", "⚙️ Gestionar", "🛡️ Roles"])

    # --- TAB 1: DIRECTORIO (ESTABLE) ---
    with tab1:
        if not df_raw.empty:
            busqueda = st.text_input("🔍 Buscar...", "").upper().strip()
            df_display = df_raw.copy().sort_values('nombre')
            df_display['Rol'] = df_display['id_rol'].map(DICCIONARIO_ROLES)
            if busqueda:
                df_display = df_display[df_display['nombre'].str.contains(busqueda)]
            
            st.dataframe(df_display[["nombre", "email", "moneda", "Rol"]], use_container_width=True, hide_index=True)
            
            pdf_bytes = generar_pdf_usuarios(df_display, DICCIONARIO_ROLES)
            st.download_button("📄 Descargar PDF Corregido", pdf_bytes, "usuarios.pdf", "application/pdf")

    # --- TAB 2: NUEVO USUARIO (RESTAURADO) ---
    with tab2:
        st.subheader("Registrar Nuevo Miembro")
        with st.form("form_registro", clear_on_submit=True):
            c1, c2 = st.columns(2)
            n_nom = c1.text_input("Nombre Completo")
            n_ema = c1.text_input("Correo Electrónico")
            n_pas = c2.text_input("Contraseña", type="password")
            n_mon = c2.selectbox("Moneda", ["COP", "USD", "EUR"])
            n_rol = st.selectbox("Asignar Rol", options=list(DICCIONARIO_ROLES.items()), format_func=lambda x: x[1])
            
            if st.form_submit_button("✅ Guardar Usuario"):
                if n_nom and n_ema and n_pas:
                    if es_correo_valido(n_ema):
                        supabase.table("usuarios").insert({
                            "nombre": n_nom.upper(), "email": n_ema.lower(), 
                            "password": n_pas, "moneda": n_mon, "id_rol": n_rol[0]
                        }).execute()
                        st.success("¡Usuario creado!"); st.rerun()
                    else:
                        st.error("Email inválido.")
                else:
                    st.warning("Completa todos los campos.")

    # --- TAB 3: GESTIONAR (RESTAURADO) ---
    with tab3:
        if not df_raw.empty:
            u_sel = st.selectbox("Seleccione usuario para editar:", df_raw['nombre'].tolist())
            u_data = df_raw[df_raw['nombre'] == u_sel].iloc[0]
            
            with st.form("form_edit"):
                e_nom = st.text_input("Nombre", u_data['nombre'])
                e_ema = st.text_input("Email", u_data['email'])
                e_rol = st.selectbox("Rol", options=list(DICCIONARIO_ROLES.items()), 
                                    index=list(DICCIONARIO_ROLES.keys()).index(u_data['id_rol']),
                                    format_func=lambda x: x[1])
                
                if st.form_submit_button("💾 Actualizar"):
                    supabase.table("usuarios").update({
                        "nombre": e_nom.upper(), "email": e_ema.lower(), "id_rol": e_rol[0]
                    }).eq("id", u_data['id']).execute()
                    st.success("Cambios guardados"); st.rerun()
            
            if st.button(f"🗑️ Eliminar a {u_sel}", type="primary"):
                supabase.table("usuarios").delete().eq("id", u_data['id']).execute()
                st.rerun()

    # --- TAB 4: ROLES Y PERMISOS (🛡️ EL ESCUDO) ---
    with tab4:
        st.subheader("🛡️ Control de Acceso")
        permisos_disponibles = [
            "LECTURA_CONTADORES", "CONCILIACION_BANCARIA", "VER_BALANCES", 
            "GESTION_USUARIOS", "MODULO_PROPIETARIOS", "VER_UNIDADES_DISPONIBLES"
        ]
        
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.write("**Nuevo Rol**")
            with st.form("n_rol"):
                nr_nom = st.text_input("Nombre del Rol")
                nr_per = st.multiselect("Permisos:", permisos_disponibles)
                if st.form_submit_button("Añadir"):
                    desc = ", ".join(nr_per)
                    supabase.table("roles").insert({"nombre_rol": nr_nom.upper(), "descripcion": desc}).execute()
                    st.rerun()
        
        with col_r2:
            if not df_roles.empty:
                r_sel = st.selectbox("Editar Rol:", df_roles['nombre_rol'].tolist())
                r_dat = df_roles[df_roles['nombre_rol'] == r_sel].iloc[0]
                actuales = [p.strip() for p in r_dat['descripcion'].split(",")] if r_dat['descripcion'] else []
                
                with st.form("e_rol"):
                    er_per = st.multiselect("Modificar Permisos:", permisos_disponibles, default=[p for p in actuales if p in permisos_disponibles])
                    if st.form_submit_button("Actualizar Rol"):
                        supabase.table("roles").update({"descripcion": ", ".join(er_per)}).eq("id", r_dat['id']).execute()
                        st.success("Permisos actualizados"); st.rerun()