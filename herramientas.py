import zoneinfo
from datetime import datetime
import smtplib
from email.message import EmailMessage
import streamlit as st
import io
import pandas as pd

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