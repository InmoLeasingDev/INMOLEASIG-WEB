from fpdf import FPDF
import streamlit as st
import pandas as pd

# --- FUNCIÓN DEL REPORTE PDF ---
def generar_pdf_usuarios(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "INMOLEASING - REPORTE DE USUARIOS", ln=True, align="C")
    pdf.ln(10)
    
    # Cabeceras
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(200, 220, 255)
    cols = [("NOMBRE", 60), ("EMAIL", 80), ("ROL", 40)]
    for col in cols:
        pdf.cell(col[1], 10, col[0], border=1, fill=True)
    pdf.ln()
    
    # Datos
    pdf.set_font("Arial", "", 9)
    for _, row in df.iterrows():
        pdf.cell(60, 10, str(row['nombre']), border=1)
        pdf.cell(80, 10, str(row['email']), border=1)
        pdf.cell(40, 10, str(row['Rol']), border=1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- MÓDULO PRINCIPAL ---
def mostrar_modulo_usuarios(supabase):
    st.header("👤 Gestión de Usuarios")
    
    # Carga de datos
    res = supabase.table("usuarios").select("id, nombre, email, moneda, id_rol, roles(nombre_rol)").execute()
    df_raw = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    if not df_raw.empty:
        df_raw['Rol'] = df_raw['roles'].apply(lambda x: x['nombre_rol'] if x else "Sin Rol")
    
    tab1, tab2, tab3 = st.tabs(["📋 Directorio", "➕ Nuevo Usuario", "⚙️ Gestionar"])

    with tab1:
        if not df_raw.empty:
            df_mostrar = df_raw[["nombre", "email", "moneda", "Rol"]]
            st.dataframe(df_mostrar, use_container_width=True)
            
            # Generar y descargar PDF
            pdf_bytes = generar_pdf_usuarios(df_mostrar)
            st.download_button("📄 Descargar Reporte PDF", pdf_bytes, "reporte_usuarios.pdf", "application/pdf")
        else:
            st.info("No hay usuarios registrados.")

    with tab2:
        st.subheader("Crear nuevo acceso")
        with st.form("registro_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                n_nom = st.text_input("Nombre Completo")
                n_ema = st.text_input("Correo Electrónico")
            with col2:
                n_pas = st.text_input("Contraseña", type="password")
                n_mon = st.selectbox("Moneda", ["COP", "USD", "EUR", "ALL"])
            
            n_rol_id = st.number_input("ID Rol (1: Admin, 2: Agente)", 1, 3, 2)

            if st.form_submit_button("🚀 Registrar Usuario"):
                # VALIDACIÓN Y TRANSFORMACIÓN
                email_f = n_ema.strip().lower()
                nombre_f = n_nom.strip().upper()

                if "@" not in email_f or "." not in email_f:
                    st.error("❌ El correo no es válido.")
                elif len(n_pas) < 4:
                    st.error("❌ Contraseña muy corta.")
                else:
                    try:
                        supabase.table("usuarios").insert({
                            "nombre": nombre_f, "email": email_f, 
                            "password": n_pas, "moneda": n_mon, "id_rol": n_rol_id
                        }).execute()
                        st.success(f"¡USUARIO {nombre_f} CREADO!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

    with tab3:
        st.subheader("Eliminar Usuario")
        if not df_raw.empty:
            u_eliminar = st.selectbox("Seleccione para eliminar", df_raw['nombre'].tolist())
            id_e = df_raw[df_raw['nombre'] == u_eliminar]['id'].values[0]
            if st.button("🗑️ Borrar Definitivamente", type="primary"):
                supabase.table("usuarios").delete().eq("id", id_e).execute()
                st.rerun()