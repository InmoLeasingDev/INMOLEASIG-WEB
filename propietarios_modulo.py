import streamlit as st
import pandas as pd
import re
import time
import urllib.parse
from fpdf import FPDF
import smtplib
from email.message import EmailMessage
import zoneinfo
from datetime import datetime

# ==========================================
# 1. FUNCIONES AUXILIARES Y CORREO
# ==========================================
def log_accion(supabase, usuario, accion, detalle):
    try:
        # --- FILTRO INTELIGENTE DE USUARIO ---
        # Si 'usuario' es un diccionario (el paquete completo), sacamos solo el nombre
        if isinstance(usuario, dict):
            nombre_limpio = usuario.get("nombre", "Usuario Desconocido")
        else:
            # Si ya es un texto, lo dejamos tal cual
            nombre_limpio = str(usuario)
        # --------------------------------------------

        # 1. Calculamos la hora exacta de Madrid
        zona_madrid = zoneinfo.ZoneInfo("Europe/Madrid")
        hora_exacta = datetime.now(zona_madrid).strftime("%Y-%m-%d %H:%M:%S")
        
        # 2. Insertamos en tu base de datos con el nombre ya limpio
        supabase.table("logs_actividad").insert({
            "usuario": nombre_limpio, 
            "accion": accion, 
            "detalle": detalle,
            "fecha": hora_exacta
        }).execute()
    except Exception as e:
        print(f"Error al registrar log: {e}")

def limpiar_texto_pdf(texto):
    return str(texto).encode('latin-1', 'ignore').decode('latin-1') if pd.notna(texto) else ""

def enviar_reporte_correo(destinatario, pdf_bytes, nombre_archivo, tipo_reporte="Propietarios"):
    try:
        remitente = st.secrets.get("EMAIL_USER", "")
        password = st.secrets.get("EMAIL_PASS", "") 
        msg = EmailMessage()
        msg['Subject'] = f'Reporte de {tipo_reporte} - InmoLeasing ERP'
        msg['From'] = remitente
        msg['To'] = destinatario
        msg.set_content(f"Hola,\n\nSe adjunta el reporte de {tipo_reporte} generado desde InmoLeasing.\n\nSaludos.")
        msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename=nombre_archivo)
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(remitente, password.replace(" ", "")) 
            smtp.send_message(msg)
        return True
    except Exception as e:
        st.error(f"❌ Error al enviar el correo: {e}"); return False

# ==========================================
# 2. MOTORES PDF (Básico y Detallado)
# ==========================================
def generar_pdf_propietarios(df, detallado=False):
    pdf = FPDF(orientation="L" if detallado else "P") # Horizontal si es detallado
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    titulo = "INMOLEASING - PROPIETARIOS (DETALLADO)" if detallado else "INMOLEASING - PROPIETARIOS (BASICO)"
    pdf.cell(0, 10, titulo, ln=True, align="C"); pdf.ln(5)
    
    pdf.set_font("Arial", "B", 8)
    pdf.set_fill_color(200, 220, 255)
    
    if detallado:
        cw = [50, 25, 30, 45, 20, 45, 60]
        headers = ["NOMBRE", "ID", "MOVIL", "CORREO", "MONEDA", "BANCO", "CUENTA"]
    else:
        cw = [60, 30, 40, 60]
        headers = ["NOMBRE", "ID", "MOVIL", "CORREO"]
        
    for i, h in enumerate(headers): 
        pdf.cell(cw[i], 10, h, 1, 0, "C", True)
    pdf.ln()
    
    pdf.set_font("Arial", "", 7)
    for _, row in df.iterrows():
        if detallado:
            textos = [row['nombre'], row['identificacion'], row['movil'], row['correo'], row['moneda'], row['banco'], row['cuenta_banco']]
        else:
            textos = [row['nombre'], row['identificacion'], row['movil'], row['correo']]
            
        textos = [limpiar_texto_pdf(t) for t in textos]
        h_fila = 5 * max([len(pdf.multi_cell(cw[i], 5, txt, split_only=True)) for i, txt in enumerate(textos)])
        if pdf.get_y() + h_fila > (190 if detallado else 270): pdf.add_page()
        
        x, y = pdf.get_x(), pdf.get_y()
        for i, txt in enumerate(textos):
            pdf.set_xy(x, y); pdf.rect(x, y, cw[i], h_fila)
            pdf.multi_cell(cw[i], 5, txt, align='L'); x += cw[i]
        pdf.set_xy(10, y + h_fila)
        
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 3. MÓDULO PRINCIPAL CRUD
# ==========================================
def mostrar_modulo_propietarios(supabase):
    st.header("🔑 Gestión de Propietarios")
    st.caption("Administración de dueños e inversores de la cadena InmoLeasing")

    # --- Sesión y Filtros Silenciosos ---
    var_sesion = st.session_state.get("usuario_actual", st.session_state.get("usuario", "ADMINISTRADOR"))
    usuario_actual = var_sesion.get("nombre", "ADMINISTRADOR") if isinstance(var_sesion, dict) else str(var_sesion)
    moneda_sesion = st.session_state.get("moneda_usuario", "ALL")

    # --- Carga de Datos ---
    try:
        res_prop = supabase.table("propietarios").select("*").eq("estado", "ACTIVO").execute()
        df_prop = pd.DataFrame(res_prop.data) if res_prop.data else pd.DataFrame()
        
        res_ops = supabase.table("operadores").select("nombre, correo, telefono, estado").eq("estado", "ACTIVO").execute()
        df_ops = pd.DataFrame(res_ops.data) if res_ops.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        df_prop, df_ops = pd.DataFrame(), pd.DataFrame()

    # Filtro automático por moneda
    if not df_prop.empty and moneda_sesion != "ALL":
        df_prop = df_prop[df_prop['moneda'] == moneda_sesion]

    tab1, tab2, tab3 = st.tabs(["📋 Directorio", "➕ Nuevo Propietario", "⚙️ Gestionar"])

    # ==========================================
    # TAB 1: DIRECTORIO Y REPORTES
    # ==========================================
    with tab1:
        if not df_prop.empty:
            busqueda = st.text_input("🔍 Buscar por nombre o ID...").upper().strip()
            df_display = df_prop.sort_values('nombre')
            
            if busqueda:
                mask = df_display['nombre'].str.contains(busqueda) | df_display['identificacion'].str.contains(busqueda)
                df_display = df_display[mask]
                
            st.dataframe(df_display[['nombre', 'tipo_id', 'identificacion', 'movil', 'correo', 'moneda']], use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("### 📄 Exportar y Compartir")
            pdf_b = generar_pdf_propietarios(df_display, detallado=False)
            pdf_d = generar_pdf_propietarios(df_display, detallado=True)
            
            c1, c2 = st.columns(2)
            c1.download_button("📄 Descargar PDF Básico", pdf_b, "propietarios_basico.pdf")
            c2.download_button("📊 Descargar PDF Detallado", pdf_d, "propietarios_detallado.pdf")

            st.markdown("#### 📤 Compartir a Operadores")
            tipo_r = st.radio("Selecciona el reporte:", ["Básico", "Detallado"], horizontal=True)
            pdf_sel = pdf_b if tipo_r == "Básico" else pdf_d
            
            col_e = st.columns(2)
            with col_e[0]:
                lista_c = [f"{r['nombre']} - {r['correo']}" for _, r in df_ops.iterrows() if r['correo']]
                op_c = st.selectbox("📧 Enviar por Correo a:", ["-- Seleccione --"] + lista_c)
                if st.button("Enviar Email", use_container_width=True):
                    if op_c != "-- Seleccione --":
                        dest = op_c.split(" - ")[-1]
                        if enviar_reporte_correo(dest, pdf_sel, "propietarios.pdf"):
                            st.success("✅ Enviado"); log_accion(supabase, usuario_actual, "ENVIO REPORTE", f"Propietarios a {dest}")

            with col_e[1]:
                lista_t = [f"{r['nombre']} - {r['telefono']}" for _, r in df_ops.iterrows() if r['telefono']]
                op_t = st.selectbox("💬 Compartir por WhatsApp a:", ["-- Seleccione --"] + lista_t)
                if st.button("Generar Link WhatsApp", use_container_width=True):
                    if op_t != "-- Seleccione --":
                        with st.spinner("Subiendo a la nube..."):
                            tel = re.sub(r'\D', '', op_t.split(" - ")[-1])
                            ruta = f"prop_{int(time.time())}.pdf"
                            try:
                                supabase.storage.from_("reportes").upload(path=ruta, file=pdf_sel, file_options={"content-type":"application/pdf"})
                                url = supabase.storage.from_("reportes").get_public_url(ruta)
                                msg_wa = urllib.parse.quote(f"Hola, te comparto el reporte de Propietarios InmoLeasing: {url}")
                                st.markdown(f'<a href="https://wa.me/{tel}?text={msg_wa}" target="_blank"><button style="width:100%;background-color:#25D366;color:white;border:none;padding:10px;border-radius:5px;">Abrir Chat</button></a>', unsafe_allow_html=True)
                                log_accion(supabase, usuario_actual, "ENVIO WA", f"Propietarios a {op_t}")
                            except Exception as e: st.error(f"❌ Error: {e}")
        else:
            st.info("ℹ️ No hay propietarios registrados o activos en tu región.")

    # ==========================================
    # TAB 2: NUEVO PROPIETARIO
    # ==========================================
    with tab2:
        with st.form("form_nuevo_prop"):
            st.subheader("Datos Personales")
            c1, c2, c3 = st.columns([2, 1, 1])
            n_nom = c1.text_input("Nombre Completo / Razón Social *")
            n_tid = c2.selectbox("Tipo ID *", ["CC", "NIT", "DNI", "NIE", "CIF", "OTRO"])
            n_id = c3.text_input("Número de Identificación *")
            
            c4, c5 = st.columns(2)
            n_mov = c4.text_input("Móvil Principal")
            n_cor = c5.text_input("Correo Principal")
            
            st.subheader("Datos Financieros")
            c6, c7, c8 = st.columns([1, 2, 2])
            n_mon = c6.selectbox("Moneda *", ["EUR", "COP"])
            n_ban = c7.text_input("Banco")
            n_tcu = c8.selectbox("Tipo de Cuenta", ["IBAN", "AHORROS", "CORRIENTE", "NEQUI", "DAVIPLATA"])
            n_cba = st.text_input("Número de Cuenta / IBAN")
            
            st.markdown("*Campos obligatorios marcados con asterisco (*)*")
            if st.form_submit_button("💾 Guardar Propietario"):
                if n_nom and n_id:
                    datos_insert = {
                        "nombre": n_nom.strip().upper(),
                        "tipo_id": n_tid,
                        "identificacion": n_id.strip().upper(),
                        "movil": n_mov.strip(),
                        "correo": n_cor.strip().lower(),
                        "moneda": n_mon,
                        "banco": n_ban.strip().upper(),
                        "tipo_cuenta": n_tcu,
                        "cuenta_banco": n_cba.strip().upper(),
                        "estado": "ACTIVO"
                    }
                    supabase.table("propietarios").insert(datos_insert).execute()
                    log_accion(supabase, usuario_actual, "CREAR PROPIETARIO", n_nom.strip().upper())
                    st.success("✅ Propietario registrado con éxito.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("⚠️ Debes llenar los campos obligatorios.")

    # ==========================================
    # TAB 3: GESTIONAR
    # ==========================================
    with tab3:
        if not df_prop.empty:
            prop_sel = st.selectbox("🔍 Selecciona un propietario para editar:", df_prop['nombre'].tolist())
            datos_p = df_prop[df_prop['nombre'] == prop_sel].iloc[0]
            
            with st.form("form_editar_prop"):
                st.subheader("Editar Información")
                e_nom = st.text_input("Nombre", datos_p['nombre'])
                e_mov = st.text_input("Móvil", str(datos_p.get('movil', '')))
                e_cor = st.text_input("Correo", str(datos_p.get('correo', '')))
                
                st.subheader("Finanzas")
                e_ban = st.text_input("Banco", str(datos_p.get('banco', '')))
                e_cba = st.text_input("Cuenta Banco", str(datos_p.get('cuenta_banco', '')))
                
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.form_submit_button("📝 Actualizar Datos"):
                    datos_upd = {
                        "nombre": e_nom.strip().upper(),
                        "movil": e_mov.strip(),
                        "correo": e_cor.strip().lower(),
                        "banco": e_ban.strip().upper(),
                        "cuenta_banco": e_cba.strip().upper()
                    }
                    supabase.table("propietarios").update(datos_upd).eq("id", int(datos_p['id'])).execute()
                    log_accion(supabase, usuario_actual, "EDITAR PROPIETARIO", e_nom.strip().upper())
                    st.success("✅ Actualizado correctamente.")
                    time.sleep(1)
                    st.rerun()
                    
            st.markdown("---")
            st.subheader("🚨 Zona de Peligro")
            if st.button("🗑️ Dar de Baja (Eliminar)"):
                supabase.table("propietarios").update({"estado": "INACTIVO"}).eq("id", int(datos_p['id'])).execute()
                log_accion(supabase, usuario_actual, "ELIMINAR PROPIETARIO", datos_p['nombre'])
                st.success("✅ Propietario dado de baja.")
                time.sleep(1)
                st.rerun()