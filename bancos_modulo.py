import streamlit as st
import pandas as pd

def mostrar_modulo_bancos(supabase):
    st.header("🏦 Gestión de Bancos y Tesorería")
    st.caption("Control de Cuentas, Extractos, Notas Bancarias y Conciliación.")

    # --- Identificar al usuario ---
    var_sesion = st.session_state.get("usuario_actual", st.session_state.get("usuario", "ADMINISTRADOR"))
    usuario_actual = var_sesion.get("nombre", "ADMINISTRADOR") if isinstance(var_sesion, dict) else str(var_sesion)

    # --- LAS 3 PESTAÑAS MAESTRAS DE TESORERÍA ---
    tab1, tab2, tab3 = st.tabs([
        "💳 Mis Cuentas Bancarias", 
        "📝 Extractos y Notas (ND/NC)", 
        "⚖️ Conciliación Bancaria"
    ])

    with tab1:
        st.subheader("🏦 Cuentas Bancarias de la Empresa")
        
        # --- LECTURA DE CUENTAS BANCARIAS ---
        try:
            res_bancos = supabase.table("fin_cuentas_bancarias").select("*").eq("estado", "ACTIVO").execute()
            df_bancos = pd.DataFrame(res_bancos.data) if res_bancos.data else pd.DataFrame()
        except Exception as e:
            df_bancos = pd.DataFrame()
            st.error(f"Error al conectar con tesorería: {e}")

        # --- CUADRÍCULA VISUAL ---
        if not df_bancos.empty:
            df_bancos_view = df_bancos[['nombre_interno', 'banco', 'iban', 'moneda', 'saldo_actual']].copy()
            df_bancos_view.columns = ['CUENTA (INTERNO)', 'ENTIDAD', 'IBAN', 'MONEDA', 'SALDO CONTABLE']
            
            df_bancos_view['SALDO CONTABLE'] = df_bancos_view.apply(
                lambda row: f"{'€' if row['MONEDA'] == 'EUR' else '$'} {float(row['SALDO CONTABLE']):,.2f}", axis=1
            )
            
            st.dataframe(df_bancos_view, use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ No hay cuentas bancarias registradas. Añade la primera.")

        st.markdown("---")
        
        # --- FORMULARIO PARA AÑADIR NUEVA CUENTA ---
        with st.expander("➕ Añadir Nueva Cuenta Bancaria", expanded=df_bancos.empty):
            with st.form("form_nuevo_banco", clear_on_submit=True):
                c1, c2 = st.columns(2)
                b_nombre = c1.text_input("Nombre Interno *", placeholder="Ej: BBVA Operaciones")
                b_entidad = c2.text_input("Entidad Bancaria *", placeholder="Ej: BBVA")
                
                c3, c4, c5 = st.columns([2, 1, 1])
                b_iban = c3.text_input("IBAN / Número de Cuenta *")
                b_moneda = c4.selectbox("Moneda", ["EUR", "COP", "USD"])
                b_saldo = c5.number_input("Saldo Inicial", min_value=0.0, step=100.0)
                
                st.caption("💡 Esta cuenta se vinculará automáticamente a la cuenta contable NIIF '1110 - Bancos Nacionales'.")
                
                if st.form_submit_button("💾 Registrar Banco"):
                    if b_nombre and b_entidad and b_iban:
                        try:
                            res_cta = supabase.table("fin_cuentas_contables").select("id").eq("codigo", "1110").execute()
                            id_cta_banco = res_cta.data[0]['id'] if res_cta.data else None
                            
                            datos_banco = {
                                "nombre_interno": b_nombre.strip().upper(),
                                "banco": b_entidad.strip().upper(),
                                "iban": b_iban.strip().upper().replace(" ", ""),
                                "moneda": b_moneda,
                                "saldo_actual": b_saldo,
                                "id_cuenta_contable": id_cta_banco
                            }
                            supabase.table("fin_cuentas_bancarias").insert(datos_banco).execute()
                            st.success("✅ Cuenta bancaria registrada con éxito.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error al guardar: {e}")
                    else:
                        st.warning("⚠️ Rellena los campos obligatorios (*).")

    with tab2:
        st.subheader("Extractos y Notas de Ajuste")
        st.info("Aquí subiremos el Excel/CSV del banco y registraremos las Notas de Débito (Comisiones) o Crédito.")

    with tab3:
        st.subheader("Conciliación Bancaria Mensual")
        st.info("Aquí cruzaremos los movimientos del banco (Tab 2) con las facturas cobradas/pagadas (Módulo Contabilidad).")