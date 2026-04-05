import streamlit as st
import pandas as pd
from fpdf import FPDF
import streamlit as st
import pandas as pd
from fpdf import FPDF
from herramientas import enviar_reporte_correo, log_accion

# --- MOTOR GENERADOR DE PDF PARA EL LIBRO DIARIO (SINTAXIS CLÁSICA) ---
def generar_pdf_diario(df, mes, moneda, total, operador_usuario, titular="INMOLEASING"):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # --- 1. TITULAR PRINCIPAL (OPERADOR O HOLDING) ---
    pdf.set_font("helvetica", "B", 18)
    pdf.cell(0, 10, titular, ln=1, align="C") 
    
    # --- 2. TÍTULO DEL REPORTE Y TOTALES ---
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 8, f"Libro Diario Oficial - {mes}", ln=1, align="C")
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 8, f"Entorno: {moneda} | Total Diario Cuadrado: {total:,.2f}", ln=1, align="C")
    
    # --- 3. FIRMA DE AUDITORÍA ---
    pdf.set_font("helvetica", "I", 9) 
    pdf.cell(0, 6, f"Generado por el usuario: {operador_usuario}", ln=1, align="C")
    
    pdf.ln(5)

    # Encabezados de Tabla
    pdf.set_fill_color(200, 220, 255) 
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(25, 8, "Fecha", border=1, align="C", fill=True)
    pdf.cell(105, 8, "Cuenta Contable", border=1, align="C", fill=True)
    pdf.cell(30, 8, "Debe", border=1, align="C", fill=True)
    pdf.cell(30, 8, "Haber", border=1, ln=1, align="C", fill=True)

    # Filas de Datos
    pdf.set_font("helvetica", "", 8)
    for _, row in df.iterrows():
        pdf.cell(25, 6, str(row.iloc[0]), border=1, align="C")
        pdf.cell(105, 6, str(row.iloc[1])[:60], border=1) 
        pdf.cell(30, 6, str(row.iloc[2]), border=1, align="R")
        pdf.cell(30, 6, str(row.iloc[3]), border=1, ln=1, align="R")

    return bytes(pdf.output(dest='S').encode('latin1'))

####################################
# inicio del módulo de contabilidad
####################################
def mostrar_modulo_contabilidad(supabase):
    st.header("📖 Contabilidad y Finanzas")
    st.caption("Control de Facturación, Tesorería, Impuestos y Libros Contables.")

    # --- Identificar al usuario y su Entorno Operativo ---
    var_sesion = st.session_state.get("usuario_actual", st.session_state.get("usuario", "ADMINISTRADOR"))
    usuario_actual = var_sesion.get("nombre", "ADMINISTRADOR") if isinstance(var_sesion, dict) else str(var_sesion)
    
    # 🛡️ Entorno Operativo Estricto
    moneda_sesion = st.session_state.get("moneda_usuario", "EUR")

    # --- LAS 5 PESTAÑAS MAESTRAS DEL MÓDULO ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Dashboard", 
        "🧾 Facturación (CxC)", 
        "💸 Tesorería (CxP y Bancos)", 
        "📚 Libro Diario",
        "🏛️ Estados Financieros y Cierres"
    ])

    with tab1:
        st.subheader(f"Resumen Financiero ({moneda_sesion})")
        st.info("Aquí irán los gráficos de ingresos, gastos y cuentas por cobrar filtrados por tu entorno operativo.")

    with tab2:
        st.subheader("🧾 Emisión de Documentos y Cuentas por Cobrar")
        st.caption("Genera facturas a propietarios (honorarios) o clientes temporales.")
        
        try:
            # Filtramos propietarios por la moneda de la sesión
            res_prop = supabase.table("propietarios").select("id, nombre, identificacion").eq("estado", "ACTIVO").eq("moneda", moneda_sesion).execute()
            df_prop = pd.DataFrame(res_prop.data) if res_prop.data else pd.DataFrame()
        except:
            df_prop = pd.DataFrame()

        with st.expander("✨ Crear Nuevo Documento de Cobro", expanded=True):
            with st.form("form_facturacion_erp", clear_on_submit=True):
                st.markdown("#### 1. Datos del Cliente")
                c1, c2 = st.columns(2)
                tipo_cliente = c1.radio("Facturar a:", ["Propietario Registrado", "Cliente Manual (Temporal)"], horizontal=True)
                
                nombre_entidad = ""
                if tipo_cliente == "Propietario Registrado":
                    if not df_prop.empty:
                        opciones_prop = [f"{r['nombre']} (ID: {r['identificacion']})" for _, r in df_prop.iterrows()]
                        sel_prop = c2.selectbox("Selecciona el Propietario *", opciones_prop)
                        nombre_entidad = sel_prop.split(" (ID:")[0] 
                    else:
                        c2.warning(f"No hay propietarios activos en {moneda_sesion}.")
                else:
                    nombre_entidad = c2.text_input("Nombre del Cliente / Inquilino *", placeholder="Ej: Juan Pérez")

                st.markdown("#### 2. Datos del Documento")
                c3, c4, c5 = st.columns([2, 2, 1])
                tipo_doc = c3.selectbox("Tipo de Documento", ["CUENTA DE COBRO", "FACTURA", "RECIBO", "NOTA DE DÉBITO"])
                n_doc = c4.text_input("Número de Documento *", placeholder="Ej: FAC-001")
                f_emi = c5.date_input("Fecha Emisión")
                
                st.markdown("#### 3. Conceptos a Cobrar")
                col_d1, col_d2, col_d3 = st.columns([3, 1, 1])
                concepto_1 = col_d1.text_input("Concepto Principal *", placeholder="Ej: Honorarios de Gestión Mes Marzo")
                cant_1 = col_d2.number_input("Cantidad", value=1.0, min_value=0.1)
                simbolo = "€" if moneda_sesion == "EUR" else "$"
                precio_1 = col_d3.number_input(f"Precio Unitario ({simbolo}) *", value=0.0, min_value=0.0, step=10.0)
                
                st.markdown("---")
                if st.form_submit_button("🚀 Emitir Documento y Registrar Deuda"):
                    if nombre_entidad and n_doc and concepto_1 and precio_1 > 0:
                        total_final = cant_1 * precio_1
                        try:
                            # 1. Guardar el Documento (Con sello de Moneda)
                            doc_data = {
                                "tipo_documento": tipo_doc, 
                                "numero_documento": n_doc.strip().upper(),
                                "fecha_emision": str(f_emi), 
                                "nombre_entidad": nombre_entidad.upper(),
                                "total": float(total_final), 
                                "moneda": moneda_sesion,      # <-- BLINDAJE
                                "estado": "PENDIENTE"
                            }
                            res_doc = supabase.table("fin_documentos").insert(doc_data).execute()
                            
                            # 2. Registrar en Cuentas por Cobrar (Con sello de Moneda)
                            cxc_data = {
                                "id_documento": res_doc.data[0]['id'], 
                                "nombre_entidad": nombre_entidad.upper(),
                                "monto_total": float(total_final), 
                                "saldo_pendiente": float(total_final),
                                "moneda": moneda_sesion,      # <-- BLINDAJE
                                "estado": "PENDIENTE"
                            }
                            supabase.table("fin_cuentas_cobrar").insert(cxc_data).execute()
                            
                            # (Opcional en el futuro: Disparar el asiento contable aquí)
                            
                            st.success(f"✅ Documento {n_doc} emitido por {simbolo} {total_final:,.2f}. Registrado en Cartera ({moneda_sesion}).")
                        except Exception as e:
                            st.error(f"❌ Error en la base de datos: {e}")
                    else:
                        st.warning("⚠️ Rellena todos los campos obligatorios (*) y usa un precio mayor a 0.")

    with tab3:
        st.subheader("Gestión de Bancos y Pagos a Proveedores/Propietarios")
        st.info(f"Aquí registraremos salidas de dinero, comisiones y conciliación para el entorno {moneda_sesion}.")

# --- LA NUEVA PESTAÑA PARA EL CFO ---
    with tab4:
        st.subheader("📚 Libro Diario Oficial")
        st.caption(f"Registro cronológico de operaciones contables ({moneda_sesion}).")
        
        c1, c2 = st.columns([1, 3])
        mes_filtro = c1.selectbox("Filtrar por Mes:", ["Todos", "01 - Enero", "02 - Febrero", "03 - Marzo", "04 - Abril", "05 - Mayo", "06 - Junio", "07 - Julio", "08 - Agosto", "09 - Septiembre", "10 - Octubre", "11 - Noviembre", "12 - Diciembre"], index=0)
        st.markdown("---")
        
        try:
            res_ast = supabase.table("fin_asientos").select("id, fecha_contable").eq("moneda", moneda_sesion).order("fecha_contable", desc=False).execute()
            df_ast = pd.DataFrame(res_ast.data) if res_ast.data else pd.DataFrame()
            # 🎯 Añadimos 'tercero' a la consulta SQL de Supabase
            res_ap = supabase.table("fin_apuntes").select("id_asiento, id_cuenta_contable, debito, credito, tercero").execute()
            df_ap = pd.DataFrame(res_ap.data) if res_ap.data else pd.DataFrame()
            res_ctas = supabase.table("fin_cuentas_contables").select("id, codigo, nombre").eq("moneda", moneda_sesion).execute()
            df_ctas = pd.DataFrame(res_ctas.data) if res_ctas.data else pd.DataFrame()
            
            if not df_ast.empty and not df_ap.empty and not df_ctas.empty:
                if mes_filtro != "Todos":
                    num_mes = mes_filtro.split(" - ")[0]
                    df_ast = df_ast[df_ast['fecha_contable'].astype(str).str[5:7] == num_mes]
                    
                if not df_ast.empty:
                    df_diario = pd.merge(df_ap, df_ast, left_on="id_asiento", right_on="id", how="inner")
                    df_diario = pd.merge(df_diario, df_ctas, left_on="id_cuenta_contable", right_on="id", how="left")
                    df_diario['Fecha'] = pd.to_datetime(df_diario['fecha_contable']).dt.strftime('%d/%m/%Y')
                    df_diario['Cuenta'] = df_diario['codigo'].astype(str) + ". " + df_diario['nombre'].fillna("CUENTA DESCONOCIDA")
                    
                    # 🎯 Limpiamos los nulos para que se vea bonito cuando no hay tercero
                    df_diario['Tercero'] = df_diario.get('tercero', pd.Series()).fillna("---")
                    
                    
                    df_diario['debito'] = pd.to_numeric(df_diario['debito']).fillna(0)
                    df_diario['credito'] = pd.to_numeric(df_diario['credito']).fillna(0)
                    
                    # 💡 SOLUCIÓN: Ordenar por Fecha, Asiento y obligar a que el DEBE (>0) salga siempre primero
                    df_diario = df_diario.sort_values(by=['fecha_contable', 'id_asiento', 'debito'], ascending=[True, True, False])
                    
                    simbolo_view = "€" if moneda_sesion == "EUR" else "$"
                    # 🎯 Añadimos 'Tercero' a las vistas finales
                    df_view = df_diario[['Fecha', 'Cuenta', 'Tercero', 'debito', 'credito']].copy()
                    df_view[f"Debe {simbolo_view}"] = df_view['debito'].apply(lambda x: f"{x:,.2f}" if x > 0 else "")
                    df_view[f"Haber {simbolo_view}"] = df_view['credito'].apply(lambda x: f"{x:,.2f}" if x > 0 else "")
                    df_final = df_view[['Fecha', 'Cuenta', 'Tercero', f"Debe {simbolo_view}", f"Haber {simbolo_view}"]]
                    st.dataframe(df_final, use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    tot_d, tot_c = df_diario['debito'].sum(), df_diario['credito'].sum()
                    if round(tot_d, 2) == round(tot_c, 2):
                        st.success(f"⚖️ **Total Diario Cuadrado:** {simbolo_view} {tot_d:,.2f}")
                    else:
                        st.error(f"❌ **Descuadre:** DEBE {tot_d:,.2f} vs HABER {tot_c:,.2f}")

                    # --- PANEL DE EXPORTACIÓN ---
                    st.markdown("#### 🖨️ Exportar y Compartir")
                    try:
                        res_ops = supabase.table("operadores").select("nombre").eq("estado", "ACTIVO").eq("moneda", moneda_sesion).execute()
                        titular_reporte = res_ops.data[0]['nombre'].upper() if len(res_ops.data) == 1 else "INMOLEASING"
                    except: titular_reporte = "INMOLEASING"
                    
                    pdf_bytes = generar_pdf_diario(df_final, mes_filtro, moneda_sesion, tot_d, usuario_actual, titular_reporte)
                    c_exp1, c_exp2, c_exp3, c_exp4 = st.columns(4)
                    
                    with c_exp1:
                        if st.download_button("📄 PDF", pdf_bytes, f"Diario_{mes_filtro}.pdf", "application/pdf", use_container_width=True):
                            log_accion(supabase, usuario_actual, "DESCARGA", f"PDF Diario {mes_filtro}")
                    with c_exp2:
                        if st.download_button("📊 Excel", df_final.to_csv(index=False).encode('utf-8'), f"Diario_{mes_filtro}.csv", "text/csv", use_container_width=True):
                            log_accion(supabase, usuario_actual, "DESCARGA", f"Excel Diario {mes_filtro}")
                    with c_exp3:
                        if st.button("📧 Correo", use_container_width=True):
                            st.session_state.mostrar_correo_diario = not st.session_state.get("mostrar_correo_diario", False)
                            st.rerun()
                    with c_exp4:
                        if st.button("💬 WhatsApp", use_container_width=True):
                            log_accion(supabase, usuario_actual, "WA", f"Link Diario {mes_filtro}")
                            st.session_state.mostrar_wa_diario = not st.session_state.get("mostrar_wa_diario", False)
                            st.rerun()
                    
                    # Paneles de Correo/WA omitidos aquí para asegurar que el bloque cierre sin errores de token.
                else: st.info("📅 Sin asientos este mes.")
            else: st.info("ℹ️ Libro Diario vacío.")
        except Exception as e: st.error(f"Error: {e}")
# --- AHORA SÍ EMPIEZA LA PESTAÑA 5 ---
    with tab5:
        st.subheader("🏛️ Reportes Oficiales y Auditoría Contable")
        
        # Sub-pestañas para organizar la contabilidad
        tab_bp, tab_lm, tab_bg = st.tabs(["⚖️ Balance de Prueba", "📖 Libro Mayor", "📈 Estados Financieros"])
        
        # --- 🚀 EXTRACCIÓN MAESTRA DE DATOS FINANCIEROS ---
        simbolo_view = "€" if moneda_sesion == "EUR" else "$"
        
        try:
            # 1. Traer Catálogo
            res_ctas = supabase.table("fin_cuentas_contables").select("id, codigo, nombre, naturaleza").eq("moneda", moneda_sesion).execute()
            df_ctas = pd.DataFrame(res_ctas.data) if res_ctas.data else pd.DataFrame()
            
            # 2. Traer Asientos Contabilizados
            res_ast = supabase.table("fin_asientos").select("id, fecha_contable, descripcion").eq("estado", "CONTABILIZADO").eq("moneda", moneda_sesion).execute()
            df_ast = pd.DataFrame(res_ast.data) if res_ast.data else pd.DataFrame()
            
            if not df_ast.empty and not df_ctas.empty:
                ids_asientos = df_ast['id'].tolist()
                
                # 3. Traer Apuntes (El detalle del DEBE y HABER)
                res_ap = supabase.table("fin_apuntes").select("id_asiento, id_cuenta_contable, debito, credito, descripcion_linea, tercero").execute()
                df_ap_raw = pd.DataFrame(res_ap.data) if res_ap.data else pd.DataFrame()
                
                if not df_ap_raw.empty:
                    df_ap = df_ap_raw[df_ap_raw['id_asiento'].isin(ids_asientos)].copy()
                    
                    # 4. Fusión de Tablas (Data Warehouse Contable)
                    df_full = pd.merge(df_ap, df_ast, left_on="id_asiento", right_on="id", how="left")
                    df_full = pd.merge(df_full, df_ctas, left_on="id_cuenta_contable", right_on="id", how="left")
                    
                    df_full['debito'] = pd.to_numeric(df_full['debito']).fillna(0)
                    df_full['credito'] = pd.to_numeric(df_full['credito']).fillna(0)
                else:
                    df_full = pd.DataFrame()
            else:
                df_full = pd.DataFrame()
        except Exception as e:
            st.error(f"Error cargando motor contable: {e}")
            df_full = pd.DataFrame()

        # =========================================================
        # 1. BALANCE DE PRUEBA (SUMAS Y SALDOS)
        # =========================================================
        with tab_bp:
            st.markdown("### Balance de Comprobación (Sumas y Saldos)")
            st.caption("Verifica matemáticamente que la contabilidad esté libre de errores. Sumas y Saldos deben ser idénticos.")
            
            if not df_full.empty:
                # Agrupamos todo por cuenta contable
                df_bp = df_full.groupby(['codigo', 'nombre', 'naturaleza']).agg({'debito': 'sum', 'credito': 'sum'}).reset_index()
                
                # Calculadora de Saldos según su Naturaleza
                def calc_saldos(row):
                    d, c = row['debito'], row['credito']
                    if row['naturaleza'] == 'DEUDORA':
                        saldo = d - c
                        return pd.Series([saldo if saldo > 0 else 0, abs(saldo) if saldo < 0 else 0])
                    else: # ACREEDORA
                        saldo = c - d
                        return pd.Series([abs(saldo) if saldo < 0 else 0, saldo if saldo > 0 else 0])
                
                df_bp[['saldo_deudor', 'saldo_acreedor']] = df_bp.apply(calc_saldos, axis=1)
                
                # Formateo visual
                df_bp_view = df_bp.copy()
                for col in ['debito', 'credito', 'saldo_deudor', 'saldo_acreedor']:
                    df_bp_view[col] = df_bp_view[col].apply(lambda x: f"{simbolo_view} {x:,.2f}" if x > 0 else "-")
                
                df_bp_view.columns = ['CÓDIGO', 'CUENTA', 'NATURALEZA', 'SUMA DEBE', 'SUMA HABER', 'SALDO DEUDOR', 'SALDO ACREEDOR']
                st.dataframe(df_bp_view.sort_values('CÓDIGO'), use_container_width=True, hide_index=True)
                
                # Ecuación Patrimonial (Totales)
                st.markdown("---")
                tot_d, tot_c = df_bp['debito'].sum(), df_bp['credito'].sum()
                tot_sd, tot_sc = df_bp['saldo_deudor'].sum(), df_bp['saldo_acreedor'].sum()
                
                c_t1, c_t2 = st.columns(2)
                if round(tot_d, 2) == round(tot_c, 2): c_t1.success(f"✅ Sumas Iguales: {simbolo_view} {tot_d:,.2f}")
                else: c_t1.error(f"❌ Descuadre en Sumas: DEBE {tot_d:,.2f} vs HABER {tot_c:,.2f}")
                    
                if round(tot_sd, 2) == round(tot_sc, 2): c_t2.success(f"✅ Saldos Iguales: {simbolo_view} {tot_sd:,.2f}")
                else: c_t2.error(f"❌ Descuadre en Saldos: DEUDOR {tot_sd:,.2f} vs ACREEDOR {tot_sc:,.2f}")
            else:
                st.info("ℹ️ No hay movimientos contables registrados para generar el balance.")

        # =========================================================
        # 2. LIBRO MAYOR (CUENTAS T / AUDITORÍA)
        # =========================================================
        with tab_lm:
            st.markdown("### Libro Mayor (Auditoría por Cuenta)")
            st.caption("Revisa el extracto detallado y el saldo acumulado de las cuentas contables.")
            
            if not df_full.empty:
                # 1. Filtros Superiores (Vista, Cuenta y Mes)
                c_filtro1, c_filtro2, c_filtro3 = st.columns([1.5, 2.5, 1])
                
                # 💡 SOLUCIÓN: Separamos la decisión con un Radio Button
                tipo_vista = c_filtro1.radio("Tipo de Consulta:", ["Cuenta Específica", "Todas las cuentas"])
                
                meses_opciones = ["Todos", "01 - Enero", "02 - Febrero", "03 - Marzo", "04 - Abril", "05 - Mayo", "06 - Junio", "07 - Julio", "08 - Agosto", "09 - Septiembre", "10 - Octubre", "11 - Noviembre", "12 - Diciembre"]
                mes_sel = c_filtro3.selectbox("📅 Filtrar por Mes:", meses_opciones, index=0)
                
                opciones_ctas = df_bp.apply(lambda r: f"{r['codigo']} - {r['nombre']} ({r['naturaleza']})", axis=1).tolist()
                
                # Lógica visual dependiendo del radio button
                if tipo_vista == "Cuenta Específica":
                    cta_sel = c_filtro2.selectbox("🔍 Selecciona la cuenta a auditar:", ["-- Seleccione --"] + opciones_ctas)
                else:
                    cta_sel = "Todas las cuentas"
                    c_filtro2.info("Se mostrará el mayor de todas las cuentas con movimientos.")
                
                st.markdown("---")
                
                # Ejecutamos la búsqueda si está todo en orden
                if cta_sel != "-- Seleccione --":
                    # 2. Preparamos el filtro global de mes
                    df_base_mayor = df_full.copy()
                    if mes_sel != "Todos":
                        num_mes = mes_sel.split(" - ")[0]
                        df_base_mayor = df_base_mayor[df_base_mayor['fecha_contable'].astype(str).str[5:7] == num_mes]
                        
                    if df_base_mayor.empty:
                        st.info(f"📅 No hay movimientos contables en el periodo seleccionado ({mes_sel}).")
                    else:
                        # 3. Determinamos qué cuentas vamos a procesar
                        if cta_sel == "Todas las cuentas":
                            # Procesamos TODAS las cuentas que existen en el balance
                            cuentas_a_procesar = df_bp[['codigo', 'nombre', 'naturaleza']].to_dict('records')
                        else:
                            # Procesamos SOLO la cuenta seleccionada
                            cod_sel = cta_sel.split(" - ")[0]
                            row_cta = df_bp[df_bp['codigo'] == cod_sel].iloc[0]
                            cuentas_a_procesar = [{'codigo': cod_sel, 'nombre': row_cta['nombre'], 'naturaleza': row_cta['naturaleza']}]
                        
                        cuentas_mostradas = 0
                        
                        # 4. Bucle dinámico para renderizar las tablas
                        for cta in cuentas_a_procesar:
                            df_cta = df_base_mayor[df_base_mayor['codigo'] == cta['codigo']].copy()
                            
                            # Solo dibujamos la cuenta si tiene movimientos en este mes/filtro
                            if not df_cta.empty:
                                cuentas_mostradas += 1
                                df_cta = df_cta.sort_values('fecha_contable')
                                nat_sel = cta['naturaleza']
                                
                                st.markdown(f"##### 🗂️ {cta['codigo']} - {cta['nombre']} | Naturaleza: `{nat_sel}`")
                                
                                # Calcular el saldo acumulado línea por línea para esta cuenta
                                saldo_acum = 0.0
                                saldos = []
                                for _, row in df_cta.iterrows():
                                    if nat_sel == 'DEUDORA': saldo_acum += (row['debito'] - row['credito'])
                                    else: saldo_acum += (row['credito'] - row['debito'])
                                    saldos.append(saldo_acum)
                                
                                df_cta['saldo_acumulado'] = saldos
                                df_cta['tercero'] = df_cta.get('tercero', pd.Series()).fillna("---")
                                
                                # Preparar vista (Mismo orden que acordamos)
                                df_mayor_view = df_cta[['fecha_contable', 'descripcion', 'tercero', 'debito', 'credito', 'saldo_acumulado']].copy()
                                df_mayor_view.columns = ['FECHA', 'ORIGEN DEL ASIENTO', 'TERCERO', 'DEBE', 'HABER', 'SALDO ACUM.']
                                
                                for col in ['DEBE', 'HABER', 'SALDO ACUM.']:
                                    df_mayor_view[col] = df_mayor_view[col].apply(lambda x: f"{simbolo_view} {x:,.2f}" if x != 0 else "-")
                                    
                                st.dataframe(df_mayor_view, use_container_width=True, hide_index=True)
                                st.write("") # Espacio en blanco entre tablas para que respire visualmente
                                
                        if cuentas_mostradas == 0:
                            st.info("ℹ️ Las cuentas seleccionadas no tuvieron movimientos en este periodo.")
            else:
                st.info("ℹ️ No hay datos contables registrados en el sistema.")
        # =========================================================
        # 3. ESTADOS FINANCIEROS (BALANCE Y P&G)
        # =========================================================
        with tab_bg:
            st.markdown("### Estados Financieros Oficiales")
            st.info("🚧 El generador de Balance General y Estado de Resultados está en construcción.")
            st.write("Ahora que el Balance de Comprobación está calculando los saldos reales (Activos, Pasivos, Patrimonio, Ingresos y Gastos), el próximo paso es organizar esos saldos en el formato de presentación oficial NIIF.")
            
            c1, c2 = st.columns(2)
            c1.button("⚖️ Generar Balance General", disabled=True)
            c2.button("📈 Generar Estado de Resultados (P&G)", disabled=True)