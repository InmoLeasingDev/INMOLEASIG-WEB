import streamlit as st
import pandas as pd
import re
import hashlib
import os
import time
from fpdf import FPDF
import smtplib
from email.message import EmailMessage
import urllib.parse

def encriptar_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def log_accion(supabase, usuario, accion, detalle):
    try:
        supabase.table("logs_actividad").insert({"usuario": usuario, "accion": accion, "detalle": detalle}).execute()
    except: pass 

def es_correo_valido(correo):
    return re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", correo) is not None

def limpiar_texto_pdf(texto):
    return str(texto).encode('latin-1', 'ignore').decode('latin-1') if pd.notna(texto) else ""

def ordenar_facultades_alfabeticamente(cadena):
    if not cadena: return []
    facs = [f.strip() for f in cadena.split(",") if f.strip()]
    return sorted(facs, key=lambda x: x.split(" ", 1)[-1] if " " in x else x)

def sincronizar_roles_facultad(supabase, df_roles, fac_vieja, fac_nueva=None):
    if df_roles.empty: return
    for _, row in df_roles.iterrows():
        desc = row.get('descripcion', '')
        if desc and fac_vieja in desc:
            lista = [f.strip() for f in desc.split(",") if f.strip()]
            if fac_vieja in lista:
                if fac_nueva: lista[lista.index(fac_vieja)] = fac_nueva
                else: lista.remove(fac_vieja)
                supabase.table("roles").update({"descripcion": ", ".join(lista)}).eq("id", int(row['id'])).execute()

LISTA_ICONOS = ['🏠','🏢','🏬','🏗️','🔑','🚪','🏘️','🏭','💰','🏦','🧾','💲','💳','📈','📉','💸','👥','👤','🤝','👨‍💼','👩‍💼','👷','🕵️','🧑‍💻','⚙️','🛠️','🔧','🔒','🔓','🛡️','✅','❌','🗑️','✏️','🔍','🚰','💡','🔥','⚡','📊','📑','📄','📅','🚀','🔔','🌐','📌','📝']

def enviar_reporte_correo(destinatario, pdf_bytes, nombre_archivo, tipo="Usuarios"):
    try:
        remitente = st.secrets["EMAIL_USER"]
        password = st.secrets["EMAIL_PASS"]
        msg = EmailMessage()
        msg['Subject'] = f'Reporte de {tipo} - InmoLeasing'
        msg['From'] = remitente
        msg['To'] = destinatario
        msg.set_content(f"Hola,\n\nSe adjunta reporte de {tipo}.\n\nSaludos.")
        msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename=nombre_archivo)
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(remitente, password.replace(" ", ""))
            smtp.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Error Email: {e}"); return False

def generar_pdf_usuarios(df, dict_roles):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "INMOLEASING - REPORTE DE USUARIOS", ln=True, align="C"); pdf.ln(5)
    pdf.set_font("Arial", "B", 8); pdf.set_fill_color(200, 220, 255)
    cw = [45, 60, 20, 40, 25]
    headers = ["NOMBRE", "EMAIL", "ROL", "ULTIMO ACCESO", "ESTADO"]
    for i, h in enumerate(headers): pdf.cell(cw[i], 10, h, 1, 0, "C", True)
    pdf.ln(); pdf.set_font("Arial", "", 7)
    for _, row in df.iterrows():
        textos = [limpiar_texto_pdf(t) for t in [row['NOMBRE'], row['EMAIL'], dict_roles.get(row['id_rol'], "S/R"), row.get('ULTIMO ACCESO', ''), row.get('estado', 'ACTIVO')]]
        h_fila = 5 * max([len(pdf.multi_cell(cw[i], 5, txt, split_only=True)) for i, txt in enumerate(textos)])
        if pdf.get_y() + h_fila > 275: pdf.add_page()
        x, y = pdf.get_x(), pdf.get_y()
        for i, txt in enumerate(textos):
            pdf.set_xy(x, y); pdf.rect(x, y, cw[i], h_fila)
            pdf.multi_cell(cw[i], 5, txt, align='L'); x += cw[i]
        pdf.set_xy(10, y + h_fila)
    return pdf.output(dest='S').encode('latin-1')

def generar_pdf_usuarios_detallado(df, dict_roles, dict_desc):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "INMOLEASING - USUARIOS Y FACULTADES", ln=True, align="C"); pdf.ln(5)
    pdf.set_font("Arial", "B", 9); pdf.set_fill_color(200, 220, 255)
    cw = [40, 35, 115]; headers = ["NOMBRE", "ROL", "FACULTADES ASIGNADAS"]
    for i, h in enumerate(headers): pdf.cell(cw[i], 8, h, 1, 0, "C", True)
    pdf.ln(); pdf.set_font("Arial", "", 8)
    for _, row in df.iterrows():
        f_raw = dict_desc.get(row['id_rol'], "")
        f_txt = "\n".join([f"- {f}" for f in ordenar_facultades_alfabeticamente(f_raw)]) if f_raw else "Sin facultades"
        textos = [limpiar_texto_pdf(t) for t in [row['NOMBRE'], dict_roles.get(row['id_rol'], "S/R"), f_txt]]
        h_fila = 5 * max([len(pdf.multi_cell(cw[i], 5, txt, split_only=True)) for i, txt in enumerate(textos)])
        if pdf.get_y() + h_fila > 275: pdf.add_page()
        x, y = pdf.get_x(), pdf.get_y()
        for i, txt in enumerate(textos):
            pdf.set_xy(x, y); pdf.rect(x, y, cw[i], h_fila)
            pdf.multi_cell(cw[i], 5, txt, align='L'); x += cw[i]
        pdf.set_xy(10, y + h_fila)
    return pdf.output(dest='S').encode('latin-1')

def generar_pdf_roles(df_roles):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "INMOLEASING - MATRIZ DE ROLES", ln=True, align="C"); pdf.ln(5)
    pdf.set_font("Arial", "B", 10); pdf.set_fill_color(200, 220, 255)
    cw = [60, 130]; headers = ["ROL", "FACULTADES ASIGNADAS"]
    for i, h in enumerate(headers): pdf.cell(cw[i], 10, h, 1, 0, "C", True)
    pdf.ln(); pdf.set_font("Arial", "", 9)
    for _, row in df_roles.iterrows():
        f_raw = row['descripcion']
        f_txt = "\n".join([f"- {f}" for f in ordenar_facultades_alfabeticamente(f_raw)]) if f_raw else "Sin facultades"
        textos = [limpiar_texto_pdf(t) for t in [row['nombre_rol'], f_txt]]
        h_fila = 6 * max([len(pdf.multi_cell(cw[i], 6, txt, split_only=True)) for i, txt in enumerate(textos)])
        if pdf.get_y() + h_fila > 275: pdf.add_page()
        x, y = pdf.get_x(), pdf.get_y()
        for i, txt in enumerate(textos):
            pdf.set_xy(x, y); pdf.rect(x, y, cw[i], h_fila)
            pdf.multi_cell(cw[i], 6, txt, align='L'); x += cw[i]
        pdf.set_xy(10, y + h_fila)
    return pdf.output(dest='S').encode('latin-1')

def generar_pdf_logs(df_logs):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "INMOLEASING - AUDITORIA DE SISTEMA", ln=True, align="C"); pdf.ln(5)
    pdf.set_font("Arial", "B", 8); pdf.set_fill_color(220, 220, 220)
    cw = [25, 30, 30, 105]; headers = ["FECHA", "USUARIO", "ACCION", "DETALLE"]
    for i, h in enumerate(headers): pdf.cell(cw[i], 8, h, 1, 0, "C", True)
    pdf.ln(); pdf.set_font("Arial", "", 7)
    for _, row in df_logs.iterrows():
        textos = [limpiar_texto_pdf(t) for t in [str(row['fecha'])[:16], str(row['usuario']), str(row['accion']), str(row['detalle'])]]
        h_fila = 5 * max([len(pdf.multi_cell(cw[i], 5, txt, split_only=True)) for i, txt in enumerate(textos)])
        if pdf.get_y() + h_fila > 275: pdf.add_page()
        x, y = pdf.get_x(), pdf.get_y()
        for i, txt in enumerate(textos):
            pdf.set_xy(x, y); pdf.rect(x, y, cw[i], h_fila)
            pdf.multi_cell(cw[i], 5, txt, align='L'); x += cw[i]
        pdf.set_xy(10, y + h_fila)
    return pdf.output(dest='S').encode('latin-1')

def mostrar_modulo_usuarios(supabase):
    st.header("👤 Gestión de Usuarios y Accesos")
    st.caption("v1.3.2 | Motor Cloud Link Activo")
    v_ses = st.session_state.get("usuario_actual", st.session_state.get("usuario", "ADMINISTRADOR"))
    usuario_actual = v_ses.get("nombre", "ADMINISTRADOR") if isinstance(v_ses, dict) else str(v_ses)
    moneda_sesion = st.session_state.get("moneda_usuario", "ALL")
    try:
        r_r = supabase.table("roles").select("*").execute()
        df_roles = pd.DataFrame(r_r.data)
        dict_roles = {r['id']: r['nombre_rol'] for r in r_r.data}
        dict_desc = {r['id']: r['descripcion'] for r in r_r.data}
        r_f = supabase.table("facultades").select("*").execute()
        df_fac = pd.DataFrame(r_f.data).sort_values('nombre_facultad')
        llaves = [f"{r['icono']} {r['nombre_facultad']}" for _, r in df_fac.iterrows()]
    except: df_roles, df_fac, dict_roles, dict_desc, llaves = pd.DataFrame(), pd.DataFrame(), {}, {}, []
    r_u = supabase.table("usuarios").select("*").execute()
    df_raw = pd.DataFrame(r_u.data)
    r_o = supabase.table("operadores").select("nombre, correo, telefono, estado").execute()
    df_ops = pd.DataFrame(r_o.data)
    df_ops = df_ops[df_ops['estado'] == 'ACTIVO'] if not df_ops.empty else df_ops
    if not df_raw.empty and moneda_sesion != "ALL": df_raw = df_raw[df_raw['moneda'] == moneda_sesion]
    t1, t2, t3, t4, t5 = st.tabs(["📋 Directorio", "➕ Nuevo", "⚙️ Gestionar", "🛡️ Roles", "📜 Logs"])
    with t1:
        if not df_raw.empty:
            bus = st.text_input("🔍 Buscar...").upper()
            df_d = df_raw.copy().sort_values('nombre')
            df_d['ROL'] = df_d['id_rol'].map(dict_roles)
            df_d['ESTADO'] = df_d['estado'].fillna('ACTIVO')
            df_d.rename(columns={'nombre':'NOMBRE','email':'EMAIL','moneda':'MONEDA'}, inplace=True)
            if bus: df_d = df_d[df_d['NOMBRE'].str.contains(bus)]
            st.dataframe(df_d[["NOMBRE","EMAIL","MONEDA","ROL","ESTADO"]], use_container_width=True, hide_index=True)
            st.markdown("---")
            pdf_b = generar_pdf_usuarios(df_d, dict_roles)
            pdf_d = generar_pdf_usuarios_detallado(df_d, dict_roles, dict_desc)
            c1, c2 = st.columns(2)
            c1.download_button("📄 PDF Básico", pdf_b, "u_basico.pdf")
            c2.download_button("📄 PDF Detallado", pdf_d, "u_detallado.pdf")
            st.markdown("#### 📤 Compartir")
            tipo_r = st.radio("Reporte:", ["Básico", "Detallado"], horizontal=True)
            pdf_sel = pdf_b if tipo_r == "Básico" else pdf_d
            col_e = st.columns(2)
            with col_e[0]:
                l_c = [f"{r['nombre']} - {r['correo']}" for _, r in df_ops.iterrows() if r['correo']]
                op_c = st.selectbox("Operador (Email)", ["-- Seleccione --"] + l_c)
                if st.button("Enviar Email"):
                    if op_c != "-- Seleccione --":
                        if enviar_reporte_correo(op_c.split(" - ")[-1], pdf_sel, "reporte.pdf"):
                            st.success("Enviado"); log_accion(supabase, usuario_actual, "ENVIO REPORTE", f"Email a {op_c}")
            with col_e[1]:
                l_t = [f"{r['nombre']} - {r['telefono']}" for _, r in df_ops.iterrows() if r['telefono']]
                op_t = st.selectbox("Operador (WA)", ["-- Seleccione --"] + l_t)
                if st.button("Link WhatsApp"):
                    if op_t != "-- Seleccione --":
                        tel = re.sub(r'\D', '', op_t.split(" - ")[-1])
                        ruta = f"u_{int(time.time())}.pdf"
                        try:
                            supabase.storage.from_("reportes").upload(path=ruta, file=pdf_sel, file_options={"content-type":"application/pdf"})
                            url = supabase.storage.from_("reportes").get_public_url(ruta)
                            st.markdown(f'<a href="https://wa.me/{tel}?text={urllib.parse.quote(url)}" target="_blank"><button style="width:100%;background-color:#25D366;color:white;border:none;padding:10px;border-radius:5px;">Abrir WA</button></a>', unsafe_allow_html=True)
                            log_accion(supabase, usuario_actual, "ENVIO WA", f"Link a {op_t}")
                        except Exception as e: st.error(f"Error: {e}")
    with t2:
        with st.form("f_n"):
            n, e, p = st.text_input("Nombre"), st.text_input("Email"), st.text_input("Pass", type="password")
            r = st.selectbox("Rol", options=list(dict_roles.items()), format_func=lambda x: x[1])
            m = st.selectbox("Moneda", ["EUR", "COP", "ALL"])
            if st.form_submit_button("Crear"):
                if n and e and p:
                    supabase.table("usuarios").insert({"nombre":n.upper(),"email":e.lower(),"password":encriptar_password(p),"id_rol":int(r[0]),"moneda":m,"estado":"ACTIVO"}).execute()
                    log_accion(supabase, usuario_actual, "CREAR USUARIO", n.upper()); st.success("Creado"); st.rerun()
    with t3:
        if not df_raw.empty:
            u_s = st.selectbox("Usuario a editar", df_raw['nombre'].tolist())
            u_d = df_raw[df_raw['nombre'] == u_s].iloc[0]
            with st.form("f_e"):
                e_n, e_e = st.text_input("Nombre", u_d['nombre']), st.text_input("Email", u_d['email'])
                e_p = st.text_input("Nueva Pass (blanco = misma)", type="password")
                e_r = st.selectbox("Rol", options=list(dict_roles.items()), format_func=lambda x: x[1])
                e_m = st.selectbox("Moneda", ["EUR", "COP", "ALL"])
                if st.form_submit_button("Actualizar"):
                    upd = {"nombre":e_n.upper(), "email":e_e.lower(), "id_rol":int(e_r[0]), "moneda":e_m}
                    if e_p: upd["password"] = encriptar_password(e_p)
                    supabase.table("usuarios").update(upd).eq("id", int(u_d['id'])).execute()
                    log_accion(supabase, usuario_actual, "EDITAR USUARIO", e_n.upper()); st.success("OK"); st.rerun()
    with t4:
        c_r1, c_r2 = st.columns(2)
        with c_r1:
            with st.form("f_fac"):
                f_i, f_n = st.selectbox("Icono", LISTA_ICONOS), st.text_input("Nombre Facultad")
                if st.form_submit_button("Añadir Facultad"):
                    supabase.table("facultades").insert({"icono":f_i, "nombre_facultad":f_n.upper()}).execute()
                    st.rerun()
        with c_r2:
            with st.form("f_rol"):
                rn, rf = st.text_input("Nombre Rol"), st.multiselect("Facultades", llaves)
                if st.form_submit_button("Crear Rol"):
                    supabase.table("roles").insert({"nombre_rol":rn.upper(), "descripcion":", ".join(rf)}).execute()
                    st.rerun()
    with t5:
        try:
            r_l = supabase.table("logs_actividad").select("*").order("fecha", desc=True).limit(100).execute()
            df_l = pd.DataFrame(r_l.data)
            if not df_l.empty:
                df_l['fecha'] = pd.to_datetime(df_l['fecha']).dt.strftime('%Y-%m-%d %H:%M')
                st.dataframe(df_l[["fecha", "usuario", "accion", "detalle"]], use_container_width=True, hide_index=True)
                st.download_button("Descargar Logs", generar_pdf_logs(df_l), "auditoria.pdf")
        except: st.info("Sin registros.")