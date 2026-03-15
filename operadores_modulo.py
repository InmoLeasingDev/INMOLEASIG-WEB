import streamlit as st
import pandas as pd
from fpdf import FPDF

# ==========================================
# 0. FUNCIONES AUXILIARES Y LOGS
# ==========================================
def log_accion(supabase, usuario, accion, detalle):
    try:
        supabase.table("logs_actividad").insert({
            "usuario": usuario, 
            "accion": accion, 
            "detalle": detalle
        }).execute()
    except Exception:
        pass 

def limpiar_texto_pdf(texto):
    if pd.isna(texto): return ""
    return str(texto).encode('latin-1', 'ignore').decode('latin-1')

# ==========================================
# 1. GENERADOR DE PDF BÁSICO (Ajustado para campos grandes)
# ==========================================
def generar_pdf_operadores(df):
    pdf = FPDF(orientation="L") # Horizontal para dar espacio a la Dirección
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "INMOLEASING - DIRECTORIO DE OPERADORES", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(200, 220, 255)
    cw = [60, 30, 80, 50, 20, 25] # Anchos calculados
    headers = ["OPERADOR", "CIF / NIT", "DIRECCION", "CORREO", "MONEDA", "ESTADO"]
    
    for i, h_text in enumerate(headers):
        pdf.cell(cw[i], 8, h_text, border=1, fill=True, align="C")
    pdf.ln()
    
    pdf.set_font("Arial", "", 8)
    for _, row in df.iterrows():
        textos_raw = [
            str(row['NOMBRE']), 
            str(row['IDENTIFICACION']), 
            str(row.get('DIRECCION', '')), 
            str(row.get('CORREO', '')),
            str(row['MONEDA']),
            str(row['ESTADO'])
        ]
        textos = [limpiar_texto_pdf(t) for t in textos_raw]
        
        # Cálculo dinámico de altura para textos largos
        lineas = [len(pdf.multi_cell(cw[i], 5, txt, split_only=True)) for i, txt in enumerate(textos)]
        h_fila = 5 * max(lineas)
        
        x_ini, y_ini = pdf.get_x(), pdf.get_y()
        if y_ini + h_fila > 190: # Límite hoja horizontal
            pdf.add_page()
            y_ini = pdf.get_y()

        x_actual = x_ini 
        for i, txt in enumerate(textos):
            pdf.set_xy(x_actual, y_ini)
            pdf.rect(x_actual, y_ini, cw[i], h_fila)
            pdf.multi_cell(cw[i], 5, txt, border=0, align='L')
            x_actual += cw[i] 
            
        pdf.set_xy(x_ini, y_ini + h_fila)
        
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 2. MÓDULO PRINCIPAL CRUD
# ==========================================
def mostrar_modulo_operadores(supabase):
    st.header("🏢 Gestión de Operadores Inmobiliarios")
    st.markdown("Administra las empresas o personas físicas que gestionan y facturan los alquileres.")
    
    usuario_actual = st.session_state.get("usuario_actual", "ADMINISTRADOR")
    moneda_sesion = st.session_state.get("moneda_usuario", "ALL")
    
    # --- Carga de Datos ---
    try:
        res = supabase.table("operadores").select("*").execute()
        df_raw = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Error cargando operadores: {e}")
        df_raw = pd.DataFrame()

    # Filtro Silencioso Multinacional
    if not df_raw.empty and moneda_sesion != "ALL":
        df_raw = df_raw[df_raw['moneda'] == moneda_sesion]

    tab1, tab2, tab3 = st.tabs(["📋 Directorio", "➕ Nuevo Operador", "⚙️ Gestionar Fichas"])

    # --- TAB 1: DIRECTORIO ---
    with tab1:
        if not df_raw.empty:
            busqueda = st.text_input("🔍 Buscar operador...", "").upper().strip()
            df_display = df_raw.copy().sort_values('nombre')
            
            df_display.rename(columns={
                'nombre': 'NOMBRE', 'identificacion': 'IDENTIFICACION', 
                'direccion': 'DIRECCION', 'correo': 'CORREO', 
                'moneda': 'MONEDA', 'estado': 'ESTADO'
            }, inplace=True)
            
            if busqueda:
                df_display = df_display[df_display['NOMBRE'].str.contains(busqueda) | df_display['IDENTIFICACION'].str.contains(busqueda)]
            
            st.dataframe(
                df_display[["NOMBRE", "IDENTIFICACION", "DIRECCION", "MONEDA", "ESTADO"]], 
                use_container_width=True, hide_index=True
            )
            
            st.markdown("---")
            c_pdf, c_mail, c_wpp = st.columns([2, 1, 1])
            with c_pdf:
                st.download_button("📄 Exportar Directorio (PDF)", generar_pdf_operadores(df_display), "operadores.pdf", "application/pdf")
        else:
            st.info("No hay operadores registrados en tu región.")

    # --- TAB 2: NUEVO OPERADOR ---
    with tab2:
        with st.form("form_nuevo_operador"):
            st.subheader("Alta de Operador")
            c1, c2 = st.columns(2)
            n_nom = c1.text_input("Nombre o Razón Social *").strip()
            n_ide = c2.text_input("CIF / NIT *").strip()
            
            c3, c4 = st.columns(2)
            n_tel = c3.text_input("Teléfono").strip()
            n_cor = c4.text_input("Correo Electrónico").strip()
            
            n_dir = st.text_input("Dirección Fiscal / Sede").strip()
            n_mon = st.selectbox("Moneda de Operación", ["EUR", "COP"], help="EUR para España, COP para Colombia.")
            
            if st.form_submit_button("✅ Registrar Operador"):
                if not n_nom or not n_ide:
                    st.error("⚠️ El Nombre y el CIF/NIT son obligatorios.")
                else:
                    datos = {
                        "nombre": n_nom.upper(),
                        "identificacion": n_ide.upper(),
                        "telefono": n_tel,
                        "correo": n_cor.lower(),
                        "direccion": n_dir.upper(),
                        "moneda": n_mon,
                        "estado": "ACTIVO"
                    }
                    supabase.table("operadores").insert(datos).execute()
                    log_accion(supabase, usuario_actual, "CREAR OPERADOR", f"Registrado: {n_nom.upper()}")
                    st.success("Operador registrado con éxito.")
                    st.rerun()

    # --- TAB 3: GESTIONAR ---
    with tab3:
        if not df_raw.empty:
            o_edit = st.selectbox("Seleccione un operador para editar:", df_raw.sort_values('nombre')['nombre'].tolist())
            o_data = df_raw[df_raw['nombre'] == o_edit].iloc[0]
            estado_actual = o_data.get('estado', 'ACTIVO')
            
            if estado_actual == 'INACTIVO':
                st.error(f"⚠️ El operador {o_edit} está INACTIVO.")
            else:
                st.success(f"✅ El operador {o_edit} está ACTIVO.")
                
            with st.form("form_editar_operador"):
                c1, c2 = st.columns(2)
                e_nom = c1.text_input("Nombre o Razón Social", o_data['nombre']).strip()
                e_ide = c2.text_input("CIF / NIT", o_data['identificacion']).strip()
                
                c3, c4 = st.columns(2)
                e_tel = c3.text_input("Teléfono", o_data.get('telefono', '')).strip()
                e_cor = c4.text_input("Correo", o_data.get('correo', '')).strip()
                
                e_dir = st.text_input("Dirección", o_data.get('direccion', '')).strip()
                idx_mon = 0 if o_data['moneda'] == "EUR" else 1
                e_mon = st.selectbox("Moneda", ["EUR", "COP"], index=idx_mon)
                
                if st.form_submit_button("💾 Actualizar Ficha"):
                    if not e_nom or not e_ide:
                        st.error("⚠️ El Nombre y el CIF/NIT son obligatorios.")
                    else:
                        datos_upd = {
                            "nombre": e_nom.upper(), "identificacion": e_ide.upper(),
                            "telefono": e_tel, "correo": e_cor.lower(),
                            "direccion": e_dir.upper(), "moneda": e_mon
                        }
                        supabase.table("operadores").update(datos_upd).eq("id", int(o_data['id'])).execute()
                        log_accion(supabase, usuario_actual, "EDITAR OPERADOR", f"Actualizado: {e_nom.upper()}")
                        st.success("Cambios guardados.")
                        st.rerun()

            # --- ZONA DE BORRADO LÓGICO ---
            st.markdown("---")
            if "confirmar_borrado_op" not in st.session_state:
                st.session_state.confirmar_borrado_op = None

            if estado_actual == 'ACTIVO':
                if st.button("🚫 Dar de Baja (Pasar a Inactivo)", type="primary"):
                    st.session_state.confirmar_borrado_op = o_data['id']
                    st.rerun()
            else:
                if st.button("♻️ Reactivar Operador"):
                    supabase.table("operadores").update({"estado": "ACTIVO"}).eq("id", int(o_data['id'])).execute()
                    log_accion(supabase, usuario_actual, "REACTIVAR OPERADOR", o_edit)
                    st.rerun()

            if st.session_state.confirmar_borrado_op == o_data['id']:
                st.warning(f"⚠️ ¿Seguro que deseas pasar a Inactivo a {o_edit}? No podrás asignarlo a nuevas unidades.")
                c_si, c_no = st.columns(2)
                if c_si.button("✅ Sí, Confirmar"):
                    supabase.table("operadores").update({"estado": "INACTIVO"}).eq("id", int(o_data['id'])).execute()
                    log_accion(supabase, usuario_actual, "INACTIVAR OPERADOR", o_edit)
                    st.session_state.confirmar_borrado_op = None
                    st.rerun()
                if c_no.button("❌ Cancelar"):
                    st.session_state.confirmar_borrado_op = None
                    st.rerun()