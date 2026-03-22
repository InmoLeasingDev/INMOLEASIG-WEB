import zoneinfo
from datetime import datetime
import smtplib
from email.message import EmailMessage
import streamlit as st
import io
import pandas as pd
import time
import urllib.parse
import re

# ==========================================
# 1. LOG DE ACTIVIDAD
# ==========================================
def log_accion(supabase, usuario, accion, detalle):
    try:
        if isinstance(usuario, dict):
            nombre_limpio = usuario.get("nombre", "Usuario Desconocido")
        else:
            nombre_limpio = str(usuario)

        zona_madrid = zoneinfo.ZoneInfo("Europe/Madrid")
        hora_exacta = datetime.now(zona_madrid).strftime("%Y-%m-%d %H:%M:%S")
        
        supabase.table("logs_actividad").insert({
            "usuario": nombre_limpio, 
            "accion": accion, 
            "detalle": detalle,
            "fecha": hora_exacta
        }).execute()
    except Exception as e:
        print(f"Error al registrar log: {e}")
    
# ==========================================
# 2. MOTOR DE CORREO (GMAIL)
# ==========================================
def enviar_reporte_correo(destinatario, archivo_bytes, nombre_archivo, tipo_reporte="Documento", tipo_archivo="pdf"):
    """
    Envía cualquier tipo de archivo (PDF o Excel) por correo electrónico.
    """
    try:
        remitente = st.secrets.get("EMAIL_USER", "")
        password = st.secrets.get("EMAIL_PASS", "") 

        if not remitente or not password:
            st.error("❌ Faltan credenciales en los secretos de Streamlit.")
            return False

        msg = EmailMessage()
        msg['Subject'] = f'Reporte de {tipo_reporte} - InmoLeasing ERP'
        msg['From'] = remitente
        msg['To'] = destinatario
        
        cuerpo_mensaje = f"""
        Hola,
        
        Se ha generado un nuevo reporte de {tipo_reporte} desde la plataforma InmoLeasing.
        Encontrarás el documento adjunto a este correo.
        
        Saludos cordiales,
        El equipo de InmoLeasing.
        """
        msg.set_content(cuerpo_mensaje)

        # Definir el tipo de adjunto dependiendo si es PDF o Excel
        main_type = 'application'
        sub_type = 'pdf' if tipo_archivo == 'pdf' else 'vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        msg.add_attachment(archivo_bytes, maintype=main_type, subtype=sub_type, filename=nombre_archivo)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(remitente, password.replace(" ", "")) 
            smtp.send_message(msg)
            
        return True
    except Exception as e:
        st.error(f"Error crítico al enviar el correo: {e}")
        return False

# ==========================================
# 3. MOTOR GENERADOR DE EXCEL
# ==========================================
def generar_excel_bytes(df, nombre_hoja="Reporte"):
    """
    Toma un DataFrame de Pandas y lo convierte mágicamente en un archivo Excel listo para descargar o enviar.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=nombre_hoja)
        
        # Ajustar el ancho de las columnas automáticamente para que se vea bonito
        worksheet = writer.sheets[nombre_hoja]
        for idx, col in enumerate(df.columns):
            series = df[col]
            max_len = max((
                series.astype(str).map(len).max(),
                len(str(series.name))
            )) + 2
            worksheet.set_column(idx, idx, max_len)
            
    return output.getvalue()

# ===========================================
# 4. PANEL UNIVERSAL DE REPORTES
# ===========================================

def panel_reportes_y_compartir(
    df_datos, 
    nombre_base, 
    modulo_origen, 
    funcion_pdf, 
    df_operadores, 
    supabase, 
    usuario_actual,
    clave_estado_cerrar="modo_unidad" 
):
    """
    Panel universal para exportar DataFrames a PDF/Excel y enviarlos por Email o WhatsApp.
    """
    with st.container(border=True):
        # --- ENCABEZADO CON BOTÓN DE CIERRE ---
        c_tit, c_cerrar = st.columns([9.3, 0.7]) 
        
        # 💡 EL ARMA SECRETA: Flexbox para forzar que el texto se centre verticalmente con el botón
        c_tit.markdown(
            f"<div style='display: flex; align-items: center; min-height: 42px; font-size: 16px;'>"
            f"<b>📊 Exportar y Compartir Listado de {modulo_origen}</b></div>", 
            unsafe_allow_html=True
        )
        
        # Le devolvemos use_container_width para que la X ocupe su columna 0.7 de forma elegante
        if c_cerrar.button("❌", key=f"btn_close_{modulo_origen}", help="Cerrar panel", use_container_width=True):
            st.session_state[clave_estado_cerrar] = "NADA"
            st.rerun()
        
        # --- 1. FILA SUPERIOR (Formato y Descarga) ---
        col1, col2, col3 = st.columns([1.7, 1.5, 6.8]) 
        
        formato = col1.radio("Formato Reporte:", ["PDF", "Excel"], horizontal=True, key=f"radio_fmt_{modulo_origen}")
        
        if formato == "PDF":
            archivo_bytes = funcion_pdf(df_datos)
            ext, mime = "pdf", "application/pdf"
        else:
            archivo_bytes = generar_excel_bytes(df_datos, modulo_origen)
            ext, mime = "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        nombre_final = f"{nombre_base}.{ext}"
        
        # Alineación vertical perfecta para el botón descargar
        col2.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        col2.download_button("⬇️ Descargar", data=archivo_bytes, file_name=nombre_final, mime=mime, key=f"btn_dl_{modulo_origen}", use_container_width=True)
        
        st.markdown("---")
        
        # --- 2. FILA INFERIOR: COMPARTIR ---
        st.write("📤 **Compartir a Operadores**")
        cols_env = st.columns(2)
        lista_correos = [f"{r['nombre']} - {r['correo']}" for _, r in df_operadores.iterrows() if pd.notna(r.get('correo')) and r['correo']]
        lista_telefonos = [f"{r['nombre']} - {r['telefono']}" for _, r in df_operadores.iterrows() if pd.notna(r.get('telefono')) and r['telefono']]
        
        with cols_env[0]:
            sel_em = st.selectbox("📧 Email:", ["-- Seleccione --"] + lista_correos, key=f"sel_em_{modulo_origen}")
            if st.button("Enviar por Correo", use_container_width=True, key=f"btn_em_{modulo_origen}"):
                if sel_em != "-- Seleccione --":
                    dest = sel_em.split(" - ")[-1].strip()
                    with st.spinner("Enviando..."):
                        if enviar_reporte_correo(dest, archivo_bytes, nombre_final, modulo_origen, ext):
                            st.success("¡Enviado!")
                            log_accion(supabase, usuario_actual, "ENVIO REPORTE", f"{modulo_origen} a {dest}")
                else: 
                    st.warning("Elige un operador.")
                    
        with cols_env[1]:
            sel_wa = st.selectbox("💬 WhatsApp:", ["-- Seleccione --"] + lista_telefonos, key=f"sel_wa_{modulo_origen}")
            if sel_wa != "-- Seleccione --":
                if st.button("Generar Link WA", use_container_width=True, key=f"btn_wa_{modulo_origen}"):
                    with st.spinner("Generando..."):
                        tel = re.sub(r'\D', '', sel_wa.split(" - ")[-1].strip())
                        try:
                            path = f"reporte_{modulo_origen.lower()}_{int(time.time())}.{ext}"
                            supabase.storage.from_("reportes").upload(path=path, file=archivo_bytes, file_options={"content-type": mime})
                            url = supabase.storage.from_("reportes").get_public_url(path)
                            msg = urllib.parse.quote(f"Hola, te comparto el reporte de {modulo_origen}: {url}")
                            st.markdown(f'<a href="https://wa.me/{tel}?text={msg}" target="_blank"><button style="width:100%;background-color:#25D366;color:white;border:none;padding:5px 10px;border-radius:5px;">Abrir WhatsApp</button></a>', unsafe_allow_html=True)
                            log_accion(supabase, usuario_actual, "ENVIO WA", f"{modulo_origen} a {sel_wa}")
                        except Exception as e: 
                            st.error(f"Error al subir a Supabase: {e}")
            else: 
                st.button("Generar Link WA", disabled=True, use_container_width=True, key=f"btn_wa_dis_{modulo_origen}")