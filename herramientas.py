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

# =========================================
# 4. PANEL UNIVERSAL DE REPORTES
# =========================================
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
        # --- ENCABEZADO LIMPIO ---
        # Quitamos las columnas del título para dejarlo minimalista
        st.markdown(
            f"<div style='font-size: 16px; font-weight: bold; margin-bottom: 15px;'>"
            f"📊 Exportar y Compartir Listado de {modulo_origen}</div>", 
            unsafe_allow_html=True
        )
            
        # --- 1. FILA SUPERIOR (Formato, Descarga y Cerrar) ---
        # Agregamos una columna más para el botón Cerrar
        col_fmt, col_dl, col_cerrar, col_esp = st.columns([1.7, 1.5, 1.5, 5.3]) 
        
        formato = col_fmt.radio("Formato:", ["PDF", "Excel"], horizontal=True, key=f"radio_fmt_{modulo_origen}")
        
        # Generación de archivos
        if formato == "PDF":
            archivo_bytes = funcion_pdf(df_datos)
            ext, mime = "pdf", "application/pdf"
        else:
            archivo_bytes = generar_excel_bytes(df_datos, modulo_origen)
            ext, mime = "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        nombre_final = f"{nombre_base}.{ext}"
        
        # Botón Descargar alineado (Este se queda en 28px)
        col_dl.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        col_dl.download_button("⬇️ Descargar", data=archivo_bytes, file_name=nombre_final, mime=mime, key=f"btn_dl_{modulo_origen}", use_container_width=True)
        
        # Botón Cerrar idéntico (Le sumamos 5px al margen para bajarlo al nivel de Descargar)
        col_cerrar.markdown("<div style='margin-top: 33px;'></div>", unsafe_allow_html=True)
        if col_cerrar.button("❌ Cerrar", key=f"btn_close_{modulo_origen}", use_container_width=True):
            st.session_state[clave_estado_cerrar] = "NADA"
            st.rerun()
        
        st.markdown("---")    
        
        # --- 2. FILA INFERIOR: COMPARTIR ---
        st.write("📤 **Compartir a Operadores**")
        cols_env = st.columns(2)
        
        # Preparar listas de contactos
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
            
            # Lógica de WhatsApp mejorada
            if sel_wa != "-- Seleccione --":
                if st.button("Generar Link WA", use_container_width=True, key=f"btn_wa_{modulo_origen}"):
                    with st.spinner("Generando..."):
                        tel = re.sub(r'\D', '', sel_wa.split(" - ")[-1].strip())
                        try:
                            path = f"reporte_{modulo_origen.lower()}_{int(time.time())}.{ext}"
                            supabase.storage.from_("reportes").upload(path=path, file=archivo_bytes, file_options={"content-type": mime})
                            url = supabase.storage.from_("reportes").get_public_url(path)
                            msg = urllib.parse.quote(f"Hola, te comparto el reporte de {modulo_origen}: {url}")
                            # Botón verde estilo WhatsApp
                            st.markdown(f'''
                                <a href="https://wa.me/{tel}?text={msg}" target="_blank">
                                    <button style="width:100%;background-color:#25D366;color:white;border:none;padding:8px;border-radius:5px;cursor:pointer;">
                                        ✅ Abrir Chat de WhatsApp
                                    </button>
                                </a>
                            ''', unsafe_allow_html=True)
                            log_accion(supabase, usuario_actual, "ENVIO WA", f"{modulo_origen} a {sel_wa}")
                        except Exception as e: 
                            st.error(f"Error en WhatsApp: {e}")
            else: 
                st.button("Generar Link WA", disabled=True, use_container_width=True, key=f"btn_wa_dis_{modulo_origen}")

# ===========================================
# GESTOR UNIVERSAL DE GALERÍAS (MODO PRO v2)
# ===========================================
def panel_gestor_galeria(supabase, usuario_actual, tabla_db, bucket_storage, id_registro, nombre_registro, fotos_actuales, clave_estado_cerrar, prefijo_ruta="img"):
    """
    Renderiza un panel estandarizado para ver, subir y eliminar fotos de cualquier tabla de la base de datos.
    Permite el borrado individual o masivo.
    """
    import time # Asegurarnos de que time esté disponible localmente
    
    st.markdown("---")
    st.markdown(f"**📸 Galería de Marketing: {nombre_registro}**")
    
    with st.form(key=f"form_galeria_{tabla_db}_{id_registro}"):
        # --- 1. MOSTRAR FOTOS ACTUALES Y CONTROLES DE BORRADO INDIVIDUAL ---
        st.write("**Fotos Registradas (Seleccione para BORRAR):**")
        fotos_lista = fotos_actuales if isinstance(fotos_actuales, list) else []
        borrar_indices = [] # Guardaremos los índices que el usuario quiera borrar

        if len(fotos_lista) > 0:
            # Usamos columnas fijas para la vista de cuadrícula
            cols_fotos = st.columns(4) 
            for i, url_foto in enumerate(fotos_lista):
                with cols_fotos[i % 4]:
                    st.image(url_foto, width=150)
                    # Control Individual: Checkbox único para esta foto
                    key_borrar = f"chk_borrar_{tabla_db}_{id_registro}_{i}"
                    if st.checkbox(f"Borrar", key=key_borrar):
                        borrar_indices.append(i) # Marcada para borrar
        else:
            st.info("No hay fotos registradas para este elemento.")
        
        st.markdown("---")
        
        # --- 2. SUBIR NUEVAS FOTOS ---
        nuevas_fotos = st.file_uploader("Subir nuevas imágenes (Max 5MB)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)
        
        st.markdown("---")
        
        # --- 3. BOTONERA MINIMALISTA (ORDEN TÁCTICO: Guardar | Borrar | Cerrar) ---
        # Ajustamos los anchos de columna para el nuevo texto más corto
        col_b1, col_b2, col_b3, col_esp = st.columns([1.6, 1.4, 1.0, 6.0])
        
        btn_guardar = col_b1.form_submit_button("💾 Guardar Cambios")
        btn_borrar_fotos = False
        if len(fotos_lista) > 0:
            btn_borrar_fotos = col_b2.form_submit_button("🗑️ Borrar Galería")
        btn_cerrar = col_b3.form_submit_button("❌ Cerrar")
        
        # --- 4. LÓGICA DE BOTONES ---
        if btn_cerrar:
            st.session_state[clave_estado_cerrar] = "NADA"
            st.rerun()
            
        elif btn_borrar_fotos:
            supabase.table(tabla_db).update({"fotos": []}).eq("id", int(id_registro)).execute()
            try:
                log_accion(supabase, usuario_actual, f"VACIAR GALERÍA {tabla_db.upper()}", nombre_registro)
            except: pass
            st.success("✅ Galería vaciada COMPLETAMENTE con éxito.")
            time.sleep(1)
            st.rerun()
            
        elif btn_guardar:
            # A) Procesar Borrado Individual
            fotos_filtradas = [foto for idx, foto in enumerate(fotos_lista) if idx not in borrar_indices]
            
            # B) Procesar Nuevas Subidas
            urls_nuevas = []
            hubo_error = False
            
            if nuevas_fotos:
                with st.spinner("Subiendo fotos nuevas..."):
                    for foto in nuevas_fotos:
                        try:
                            ext = foto.name.split('.')[-1].lower()
                            tipo_mime = f"image/{ext.replace('jpg', 'jpeg')}"
                            ruta_foto = f"{prefijo_ruta}_{id_registro}_{int(time.time())}_{foto.name}"
                            
                            supabase.storage.from_(bucket_storage).upload(
                                path=ruta_foto, 
                                file=foto.getvalue(), 
                                file_options={"content-type": tipo_mime}
                            )
                            url_publica = supabase.storage.from_(bucket_storage).get_public_url(ruta_foto)
                            urls_nuevas.append(url_publica)
                        except Exception as e:
                            hubo_error = True
                            st.error(f"Error subiendo {foto.name}: {e}")
            
            # C) Guardar el resultado final si no hay errores
            if not hubo_error:
                fotos_finales = fotos_filtradas + urls_nuevas
                
                # Candado para prevenir errores al guardar array vacío
                array_db = fotos_finales if len(fotos_finales) > 0 else '{}'
                
                supabase.table(tabla_db).update({"fotos": array_db}).eq("id", int(id_registro)).execute()
                
                try:
                    log_accion(supabase, usuario_actual, f"GUARDAR CAMBIOS GALERÍA {tabla_db.upper()}", nombre_registro)
                except: pass
                
                st.success("✅ Cambios en la galería guardados con éxito.")
                st.session_state[clave_estado_cerrar] = "NADA"
                time.sleep(1)
                st.rerun()