import streamlit as st
import pandas as pd
from fpdf import FPDF
import smtplib
from email.message import EmailMessage
import urllib.parse
import re
import time 
import zoneinfo
from datetime import datetime

# ==========================================
# 0. FUNCIONES AUXILIARES Y LOGS
# ==========================================

def log_accion(supabase, usuario, accion, detalle):
    try:
        # --- NUEVO: FILTRO INTELIGENTE DE USUARIO ---
        # Si 'usuario' es un diccionario (el paquete completo), sacamos solo el nombre
        if isinstance(usuario, dict):
            nombre_limpio = usuario.get("nombre", "Usuario Desconocido")
        else:
            # Si ya es un texto (como en el módulo usuarios), lo dejamos tal cual
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
    if pd.isna(texto): return ""
    return str(texto).encode('latin-1', 'ignore').decode('latin-1')

def es_correo_valido(correo):
    patron = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(patron, correo) is not None

# ==========================================
# 0.5 FUNCIÓN MOTOR DE CORREO (GMAIL SERVER)
# ==========================================
def enviar_reporte_correo(destinatario, pdf_bytes, nombre_archivo, tipo_reporte="Operadores"):
    try:
        remitente = st.secrets.get("EMAIL_USER", "")
        password = st.secrets.get("EMAIL_PASS", "") 

        if not remitente or not password:
            st.error("❌ Falla técnica: Faltan credenciales (EMAIL_USER / EMAIL_PASS) en los secretos.")
            return False

        msg = EmailMessage()
        msg['Subject'] = f'Reporte de {tipo_reporte} - InmoLeasing ERP'
        msg['From'] = remitente
        msg['To'] = destinatario
        
        cuerpo_mensaje = f"""
        Hola,
        
        Se ha generado un nuevo reporte del Directorio de {tipo_reporte} desde la plataforma InmoLeasing.
        Encontrarás el documento PDF adjunto a este correo.
        
        Saludos cordiales,
        El equipo de InmoLeasing.
        """
        msg.set_content(cuerpo_mensaje)

        msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename=nombre_archivo)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(remitente, password.replace(" ", "")) 
            smtp.send_message(msg)
            
        return True
    except Exception as e:
        st.error(f"Error crítico al enviar el correo: {e}")
        return False

# ==========================================
# 1. GENERADOR DE PDF BÁSICO (Ajustado)
# ==========================================
def generar_pdf_operadores(df):
    pdf = FPDF(orientation="L") 
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "INMOLEASING - DIRECTORIO DE OPERADORES", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(200, 220, 255)
    cw = [60, 30, 80, 50, 20, 25] 
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
        
        lineas = [len(pdf.multi_cell(cw[i], 5, txt, split_only=True)) for i, txt in enumerate(textos)]
        h_fila = 5 * max(lineas)
        
        x_ini, y_ini = pdf.get_x(), pdf.get_y()
        if y_ini + h_fila > 190: 
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
    
    # --- CONTROL DE VERSIÓN DEL MÓDULO ---
    MOD_VERSION = "v1.1"
    st.caption(f"⚙️ Módulo Operadores {MOD_VERSION} | Administra las empresas o personas físicas.")
    
    usuario_actual = st.session_state.get("usuario_actual", 
                        st.session_state.get("nombre_usuario", 
                        st.session_state.get("usuario", "ADMINISTRADOR")))
                        
    moneda_sesion = st.session_state.get("moneda_usuario", "ALL")
    
    # --- Carga de Datos ---
    try:
        res = supabase.table("operadores").select("*").execute()
        df_raw = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Error cargando operadores: {e}")
        df_raw = pd.DataFrame()

    if not df_raw.empty and moneda_sesion != "ALL":
        df_raw = df_raw[df_raw['moneda'] == moneda_sesion]

    tab1, tab2, tab3 = st.tabs(["📋 Directorio", "➕ Nuevo Operador", "⚙️ Gestionar Fichas"])

    # --- TAB 1: DIRECTORIO E INFORMES ---
    with tab1:
        if not df_raw.empty:
            busqueda = st.text_input("🔍 Buscar operador...", "").upper().strip()
            df_display = df_raw.copy().sort_values('nombre')
            
            df_display.rename(columns={
                'nombre': 'NOMBRE', 'identificacion': 'IDENTIFICACION', 
                'direccion': 'DIRECCION', 'correo': 'CORREO', 'telefono': 'TELEFONO',
                'moneda': 'MONEDA', 'estado': 'ESTADO'
            }, inplace=True)
            
            if busqueda:
                df_display = df_display[df_display['NOMBRE'].str.contains(busqueda) | df_display['IDENTIFICACION'].str.contains(busqueda)]
            
            st.dataframe(
                df_display[["NOMBRE", "IDENTIFICACION", "DIRECCION", "CORREO", "TELEFONO", "MONEDA", "ESTADO"]], 
                use_container_width=True, hide_index=True
            )
            
            st.markdown("---")
            st.markdown("### 📄 Exportar y Compartir Reportes")
            
            pdf_bytes = generar_pdf_operadores(df_display)
            st.download_button("📄 Descargar Reporte en PDF", pdf_bytes, "directorio_operadores.pdf", "application/pdf")
            
            # ==========================================
            # SECCIÓN COMPARTIR A OPERADORES
            # ==========================================
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("#### 📤 Compartir Reporte a Operadores")
            st.write("Selecciona el medio y el operador destinatario:")
            
            cols_envio = st.columns(2)
            
            lista_correos = []
            lista_telefonos = []
            df_activos = df_raw[df_raw['estado'] == 'ACTIVO'] if 'estado' in df_raw.columns else df_raw
            
            for _, row in df_activos.iterrows():
                if pd.notna(row.get('correo')) and str(row['correo']).strip():
                    lista_correos.append(f"{row.get('nombre', 'Sin Nombre')} - {row['correo']}")
                if pd.notna(row.get('telefono')) and str(row['telefono']).strip():
                    lista_telefonos.append(f"{row.get('nombre', 'Sin Nombre')} - {row['telefono']}")
            
            with cols_envio[0]:
                st.info("📧 Envío por Email")
                if lista_correos:
                    operador_correo_sel = st.selectbox("Seleccionar Operador (Correo)", ["-- Seleccione --"] + lista_correos)
                    if st.button("Enviar PDF por Correo", use_container_width=True):
                        if operador_correo_sel != "-- Seleccione --":
                            correo_destinatario = operador_correo_sel.split(" - ")[-1].strip()
                            with st.spinner("Conectando con el servidor de Gmail..."):
                                exito = enviar_reporte_correo(correo_destinatario, pdf_bytes, "operadores_inmoleasing.pdf", "Operadores")
                                if exito:
                                    st.success(f"Reporte enviado a {correo_destinatario}")
                                    log_accion(supabase, usuario_actual, "ENVIO REPORTE", f"Reporte Operadores enviado a {correo_destinatario}")
                        else:
                            st.warning("Selecciona un operador de la lista.")
                else:
                    st.warning("No hay operadores registrados con correo electrónico.")

            with cols_envio[1]:
                st.success("💬 Envío por WhatsApp")
                if lista_telefonos:
                    operador_tel_sel = st.selectbox("Seleccionar Operador (WhatsApp)", ["-- Seleccione --"] + lista_telefonos)
                    mensaje_base = "Hola, te comparto el Directorio de Operadores actualizado de InmoLeasing."
                    
                    if operador_tel_sel != "-- Seleccione --":
                        if st.button("Generar Link y Abrir WhatsApp", use_container_width=True):
                            with st.spinner("Generando link seguro en la nube..."):
                                telefono_wa = operador_tel_sel.split(" - ")[-1].strip()
                                telefono_wa = re.sub(r'\D', '', telefono_wa) 
                                
                                try:
                                    timestamp_actual = int(time.time())
                                    ruta_nube = f"directorio_operadores_{timestamp_actual}.pdf"
                                    
                                    supabase.storage.from_("reportes").upload(
                                        path=ruta_nube,
                                        file=pdf_bytes,
                                        file_options={"content-type": "application/pdf"}
                                    )
                                    
                                    link_pdf = supabase.storage.from_("reportes").get_public_url(ruta_nube)
                                    
                                    mensaje_final = f"{mensaje_base} Puedes descargarlo de forma segura aquí: {link_pdf}"
                                    texto_codificado = urllib.parse.quote(mensaje_final)
                                    link_wa = f"https://wa.me/{telefono_wa}?text={texto_codificado}"
                                    
                                    boton_html = f"""
                                    <a href="{link_wa}" target="_blank" style="text-decoration: none;">
                                        <button style="width:100%; background-color:#25D366; color:white; border:none; padding:10px; border-radius:5px; cursor:pointer; font-weight:bold; font-size:16px; margin-top:10px;">
                                            Abrir chat de WhatsApp
                                        </button>
                                    </a>
                                    """
                                    st.markdown(boton_html, unsafe_allow_html=True)
                                    
                                    log_accion(supabase, usuario_actual, "ENVIO REPORTE", f"Enviado por WA a {operador_tel_sel}")
                                    st.success("¡Link generado! Haz clic en el botón verde de arriba.")
                                    
                                except Exception as e:
                                    st.error(f"Error al subir el archivo: {e}")
                                    st.info("⚠️ Asegúrate de que el bucket se llame exactamente 'reportes' y sea público.")
                    else:
                        st.button("Generar Link y Abrir WhatsApp", disabled=True, use_container_width=True)
                else:
                    st.warning("No hay operadores registrados con teléfono.")
                    
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
            n_tel = c3.text_input("Teléfono", placeholder="Ej: 34600000000 (Incluir código de país)").strip()
            n_cor = c4.text_input("Correo Electrónico", placeholder="ejemplo@operador.com").strip()
            
            n_dir = st.text_input("Dirección Fiscal / Sede").strip()
            n_mon = st.selectbox("Moneda de Operación", ["EUR", "COP"], help="EUR para España, COP para Colombia.")
            
            if st.form_submit_button("✅ Registrar Operador"):
                if not n_nom or not n_ide:
                    st.error("⚠️ El Nombre y el CIF/NIT son obligatorios.")
                elif n_cor and not es_correo_valido(n_cor):
                    st.error("❌ El formato del correo electrónico no es válido.")
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
                tel_actual = str(o_data.get('telefono', '')) if pd.notna(o_data.get('telefono')) else ''
                cor_actual = str(o_data.get('correo', '')) if pd.notna(o_data.get('correo')) else ''
                
                e_tel = c3.text_input("Teléfono (Incluir código país)", tel_actual).strip()
                e_cor = c4.text_input("Correo", cor_actual).strip()
                
                dir_actual = str(o_data.get('direccion', '')) if pd.notna(o_data.get('direccion')) else ''
                e_dir = st.text_input("Dirección", dir_actual).strip()
                
                idx_mon = 0 if o_data['moneda'] == "EUR" else 1
                e_mon = st.selectbox("Moneda", ["EUR", "COP"], index=idx_mon)
                
                if st.form_submit_button("💾 Actualizar Ficha"):
                    if not e_nom or not e_ide:
                        st.error("⚠️ El Nombre y el CIF/NIT son obligatorios.")
                    elif e_cor and not es_correo_valido(e_cor):
                        st.error("❌ El formato del correo electrónico no es válido.")
                    else:
                        datos_upd = {
                            "nombre": e_nom.upper(), 
                            "identificacion": e_ide.upper(),
                            "telefono": e_tel, 
                            "correo": e_cor.lower(),
                            "direccion": e_dir.upper(), 
                            "moneda": e_mon
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