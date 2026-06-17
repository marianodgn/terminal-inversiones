import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from fpdf import FPDF
import tempfile

# 1. CONFIGURACIÓN DE PÁGINA Y UI (Glassmorphism & Pulse)
st.set_page_config(layout="wide", page_title="DSL - Dynamic Strategy Ledger", page_icon="💠")

st.markdown("""
    <style>
    .main { background-color: #0b0c10; color: #c5c6c7; }
    div[data-testid="stMetricValue"] { color: #66fcf1; font-size: 28px; font-weight: 900; text-shadow: 0px 0px 10px rgba(102, 252, 241, 0.5); }
    div[data-testid="stMetricLabel"] { color: #45a29e; font-weight: bold; font-size: 14px; letter-spacing: 1px; }
    .stButton>button { background: linear-gradient(135deg, #1f2833 0%, #0b0c10 100%); color: #66fcf1; border: 1px solid #45a29e; border-radius: 6px; width: 100%; font-weight: bold; text-transform: uppercase; transition: all 0.3s ease; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .stButton>button:hover { background: #45a29e; color: #0b0c10; box-shadow: 0px 0px 15px rgba(102, 252, 241, 0.6); transform: translateY(-2px); }
    h1, h2, h3, h4 { color: #ffffff; font-family: 'Segoe UI', sans-serif; letter-spacing: 1px; }
    hr { border-color: #1f2833; }
    @keyframes pulse-neon { 0% { box-shadow: 0 0 0 0 rgba(102, 252, 241, 0.7); } 70% { box-shadow: 0 0 0 15px rgba(102, 252, 241, 0); } 100% { box-shadow: 0 0 0 0 rgba(102, 252, 241, 0); } }
    .tp-alert { background: linear-gradient(90deg, #0b0c10 0%, #1f2833 100%); color: #66fcf1; padding: 18px; border-radius: 10px; font-size: 18px; text-align: center; margin-bottom: 20px; border: 1px solid #66fcf1; animation: pulse-neon 2s infinite; font-weight: bold; }
    .rsi-alert { background: rgba(31, 40, 51, 0.7); backdrop-filter: blur(10px); color: #e0e0e0; padding: 15px; border-radius: 10px; border-left: 6px solid #ff4655; margin-bottom: 20px; font-size: 16px; box-shadow: 0 8px 32px 0 rgba(0,0,0,0.37); }
    .scan-alert { background: rgba(31, 40, 51, 0.7); border-left: 6px solid #66fcf1; padding: 15px; margin-top: 10px; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- SISTEMA DE LOGIN ---
def check_password():
    usuarios_permitidos = {"mariano": "admin1234", "daniel": "corneta", "Juan": "nomada"}
    if "usuario_autenticado" not in st.session_state:
        st.session_state.update({"usuario_autenticado": False, "usuario_actual": None})

    if not st.session_state["usuario_autenticado"]:
        st.markdown("<h1 style='text-align: center; color: #66fcf1;'>💠 DYNAMIC STRATEGY LEDGER</h1>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            usuario = st.text_input("ID de Operador:")
            clave = st.text_input("Clave de Encriptación:", type="password")
            if st.button("INICIALIZAR SISTEMA"):
                if usuario in usuarios_permitidos and usuarios_permitidos[usuario] == clave:
                    st.session_state.update({"usuario_autenticado": True, "usuario_actual": usuario})
                    st.rerun()
                else:
                    st.error("🚫 Credenciales inválidas.")
        return False
    else:
        with st.sidebar:
            st.markdown(f"👤 **Operador:** `{st.session_state['usuario_actual'].upper()}`")
            if st.button("DESCONECTAR"):
                st.session_state.update({"usuario_autenticado": False, "usuario_actual": None, "mi_cartera": [], "usuario_cargado": None})
                st.rerun()
        return True

if not check_password(): st.stop()

# --- GESTIÓN DE DATOS ---
def obtener_nombre_archivo(): return f"cartera_{st.session_state['usuario_actual']}.csv"
def cargar_cartera(): return pd.read_csv(obtener_nombre_archivo()).to_dict('records') if os.path.exists(obtener_nombre_archivo()) else []
def guardar_cartera(): pd.DataFrame(st.session_state.mi_cartera).to_csv(obtener_nombre_archivo(), index=False)

usuario_actual = st.session_state["usuario_actual"]
if 'mi_cartera' not in st.session_state or st.session_state.get('usuario_cargado') != usuario_actual:
    st.session_state.mi_cartera = cargar_cartera()
    st.session_state['usuario_cargado'] = usuario_actual
if 'mostrar_ia' not in st.session_state:
    st.session_state.mostrar_ia = False

# LISTAS Y DICCIONARIOS
mis_cedears = {
    "BERKSHIRE HATHAWAY": "BRKB.BA", "SALESFORCE": "CRM.BA", "JP MORGAN": "JPM.BA",
    "MCDONALDS": "MCD.BA", "MERCADO LIBRE": "MELI.BA", "MICROSTRATEGY": "MSTR.BA",
    "SERVICE NOW": "NOW.BA", "NU HOLDINGS": "NU.BA", "PROCTER GAMBLE": "PG.BA",
    "PALANTIR": "PLTR.BA", "SPDR S P 500": "SPY.BA", "NIKE": "NKE.BA"
}

lista_escaner_global = {
    "APPLE": "AAPL.BA", "AMAZON": "AMZN.BA", "GOOGLE": "GOOGL.BA", "TESLA": "TSLA.BA",
    "NVIDIA": "NVDA.BA", "META": "META.BA", "COCA COLA": "KO.BA", "DISNEY": "DIS.BA",
    "VISA": "V.BA", "WALMART": "WMT.BA", "PFIZER": "PFE.BA", "AMD": "AMD.BA"
}
todos_los_cedears = {**mis_cedears, **lista_escaner_global}

inteligencia_mercado = {
    "BERKSHIRE HATHAWAY": "Wall Street destaca su enorme reserva de efectivo. Refugio seguro en volatilidad.",
    "SALESFORCE": "Visión optimista por su integración de IA en su ecosistema CRM.",
    "JP MORGAN": "Sólido reporte de ganancias. El sector bancario se beneficia de tasas actuales.",
    "MCDONALDS": "Acción defensiva. Sugerencia de mantener por su estabilidad frente a inflación.",
    "MERCADO LIBRE": "Líder en e-commerce LATAM. Perspectivas de crecimiento a largo plazo muy alcistas.",
    "MICROSTRATEGY": "Activo de altísima volatilidad, proxy del Bitcoin. Riesgo institucional alto.",
    "SERVICE NOW": "Fuerte crecimiento en suscripciones corporativas por digitalización.",
    "NU HOLDINGS": "Crecimiento explosivo en LATAM. Warren Buffett mantiene posición.",
    "PROCTER GAMBLE": "Acción hiper-defensiva. Funciona como ancla de estabilidad.",
    "PALANTIR": "Contratos gubernamentales de IA impulsan rentabilidad. Sentimiento muy optimista.",
    "SPDR S P 500": "Índice principal del mercado. Acumulación constante a largo plazo recomendada.",
    "NIKE": "Marca global dominante. Gran poder de precios, aunque susceptible a ciclos de consumo y mercado asiático.",
    "DÓLAR OFICIAL": "Reserva de valor básica. Cotización basada en el tipo de cambio oficial mayorista."
}

# FUNCIONES MATEMÁTICAS Y PDF
def calcular_indicadores(df):
    if len(df) < 20: return df
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['Vol_SMA20'] = df['Volume'].rolling(window=20).mean()
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['BB_Upper'] = df['SMA_20'] + 2 * df['Close'].rolling(window=20).std()
    df['BB_Lower'] = df['SMA_20'] - 2 * df['Close'].rolling(window=20).std()
    ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema_12 - ema_26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df

def crear_pdf(df, reporte_ia_textos, usuario):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=f"DSL STRATEGY REPORT - OPERADOR: {usuario.upper()}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="1. Resumen de Activos Ponderados", ln=True)
    pdf.set_font("Arial", '', 10)
    for _, row in df.iterrows():
        linea = f"{row['Empresa']} | Cantidad: {row['Nominales']} | Costo: ${row['Costo_Entrada_Promedio']:,.2f} | Rto: {row['Rendimiento_%']}%"
        pdf.cell(200, 8, txt=linea.encode('latin-1', 'replace').decode('latin-1'), ln=True)
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="2. Analisis Cuantitativo de IA", ln=True)
    pdf.set_font("Arial", '', 10)
    for texto in reporte_ia_textos:
        pdf.multi_cell(0, 6, txt=texto.encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(4)
        
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    pdf.output(path)
    return path

# --- INTERFAZ PRINCIPAL ---
st.title("💠 DYNAMIC STRATEGY LEDGER - DSL")

tab_ledger, tab_tech = st.tabs(["📊 MATRIZ DEL LEDGER & ESCÁNER", "📈 SIMULADOR DE ANÁLISIS TÉCNICO"])

# ==========================================
# PESTAÑA 1: LEDGER Y ESCÁNER DE MERCADO
# ==========================================
with tab_ledger:
    espacio_alerta_tp = st.empty()
    espacio_alerta_rsi = st.empty()

    with st.sidebar:
        st.header("⚙️ DATA INJECTION")
        tipo_ingreso = st.radio("Categoría:", ["Renta Variable", "Divisa"])
        
        if tipo_ingreso == "Renta Variable":
            seleccion = st.selectbox("Activo:", list(mis_cedears.keys()))
            ticker_activo = mis_cedears[seleccion]
            etiqueta_cantidad = "Nominales:"
        else:
            seleccion = "DÓLAR OFICIAL"
            ticker_activo = "ARS=X"
            etiqueta_cantidad = "Cantidad (USD):"
            
        nominales = st.number_input(etiqueta_cantidad, min_value=1.0, step=1.0)
        fecha = st.date_input("Fecha de Compra:")
        objetivo = st.number_input("Take Profit (%):", min_value=1.0, value=15.0, step=1.0)
        
        if st.button("INYECCIÓN DE DATOS"):
            hist = yf.Ticker(ticker_activo).history(start=fecha, end=fecha + pd.Timedelta(days=5))
            if not hist.empty:
                st.session_state.mi_cartera.append({
                    "ID_Orden": int(pd.Timestamp.now().timestamp() * 1000),
                    "Empresa": seleccion, "Ticker": ticker_activo, "Nominales": nominales, 
                    "Costo_Entrada": round(hist['Close'].iloc[0], 2), "Objetivo_%": objetivo, "Fecha_Compra": str(fecha)
                })
                guardar_cartera()
                st.session_state.mostrar_ia = False
                st.rerun()
            else: st.error("Sin datos en esa fecha.")

        st.markdown("---")
        if st.session_state.mi_cartera:
            df_historial = pd.DataFrame(st.session_state.mi_cartera)
            opciones_borrar = [f"{row['Empresa']} ({row['Fecha_Compra']}) - {row['Nominales']}" for _, row in df_historial.iterrows()]
            a_borrar_idx = st.selectbox("Seleccionar para purgar:", range(len(opciones_borrar)), format_func=lambda x: opciones_borrar[x])
            if st.button("PURGAR DATO"):
                del st.session_state.mi_cartera[a_borrar_idx]
                guardar_cartera()
                st.session_state.mostrar_ia = False
                st.rerun()

    if st.session_state.mi_cartera:
        df_raw = pd.DataFrame(st.session_state.mi_cartera)
        df_raw['Capital_Fila'] = df_raw['Costo_Entrada'] * df_raw['Nominales']
        df_agrupado = df_raw.groupby(['Empresa', 'Ticker']).agg(
            Nominales=('Nominales', 'sum'), Capital_Invertido=('Capital_Fila', 'sum'), Objetivo_Promedio=('Objetivo_%', 'mean')
        ).reset_index()
        df_agrupado['Costo_Entrada_Promedio'] = df_agrupado['Capital_Invertido'] / df_agrupado['Nominales']
        
        precios_actuales, rsis = [], []
        for t in df_agrupado['Ticker']:
            hist_1mo = yf.Ticker(t).history(period="3mo")
            if not hist_1mo.empty:
                precios_actuales.append(round(hist_1mo['Close'].iloc[-1], 2))
                df_indicadores = calcular_indicadores(hist_1mo)
                rsis.append(round(df_indicadores['RSI'].iloc[-1], 2) if 'RSI' in df_indicadores else 0)
            else:
                precios_actuales.append(0); rsis.append(0)
                
        df_agrupado['Precio_Actual'] = precios_actuales
        df_agrupado['RSI_Actual'] = rsis
        df_agrupado['Valor_Actual'] = df_agrupado['Precio_Actual'] * df_agrupado['Nominales']
        df_agrupado['Resultado_ARS'] = df_agrupado['Valor_Actual'] - df_agrupado['Capital_Invertido']
        df_agrupado['Rendimiento_%'] = round((df_agrupado['Resultado_ARS'] / df_agrupado['Capital_Invertido']) * 100, 2)

        tp_alcanzados = df_agrupado[df_agrupado['Rendimiento_%'] >= df_agrupado['Objetivo_Promedio']]
        if not tp_alcanzados.empty:
            espacio_alerta_tp.markdown(f"""<div class='tp-alert'>⚡ <b>¡OBJETIVO DE GANANCIA ALCANZADO!</b><br>Considerar cierre en: <b>{", ".join(tp_alcanzados['Empresa'].tolist())}</b></div>""", unsafe_allow_html=True)
        
        rsi_compra = df_agrupado[(df_agrupado['RSI_Actual'] < 35) & (df_agrupado['Empresa'] != "DÓLAR OFICIAL")]
        rsi_venta = df_agrupado[(df_agrupado['RSI_Actual'] > 70) & (df_agrupado['Empresa'] != "DÓLAR OFICIAL")]
        if not rsi_compra.empty or not rsi_venta.empty:
            msg = []
            if not rsi_compra.empty: msg.append(f"🟢 <b>OPORTUNIDAD ACUMULACIÓN (RSI < 35):</b> {', '.join(rsi_compra['Empresa'].tolist())}")
            if not rsi_venta.empty: msg.append(f"🔴 <b>RIESGO CORRECCIÓN (RSI > 70):</b> {', '.join(rsi_venta['Empresa'].tolist())}")
            espacio_alerta_rsi.markdown(f"<div class='rsi-alert'><b>📊 ALERTAS TÉCNICAS EN CARTERA:</b><br><br>{'<br>'.join(msg)}</div>", unsafe_allow_html=True)

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("CAPITAL DESPLEGADO", f"$ {df_agrupado['Capital_Invertido'].sum():,.2f}")
        kpi2.metric("VALOR DE MERCADO", f"$ {df_agrupado['Valor_Actual'].sum():,.2f}")
        resultado_total = df_agrupado['Resultado_ARS'].sum()
        kpi3.metric("P/L NETO (ARS)", f"$ {resultado_total:,.2f}")
        kpi4.metric("RENDIMIENTO GLOBAL", f"{((df_agrupado['Valor_Actual'].sum() / df_agrupado['Capital_Invertido'].sum()) - 1) * 100:.2f} %")

        st.markdown("---")
        def highlight_target(row):
            if row['Rendimiento_%'] >= row['Objetivo_Promedio']: return ['background-color: rgba(102, 252, 241, 0.15); color: #66fcf1; border-left: 4px solid #66fcf1;'] * len(row)
            elif row['Rendimiento_%'] < 0: return ['background-color: rgba(255, 70, 85, 0.1); color: #ff4655;'] * len(row)
            return ['color: #c5c6c7;'] * len(row)
        st.dataframe(df_agrupado[['Empresa', 'Nominales', 'Costo_Entrada_Promedio', 'Precio_Actual', 'RSI_Actual', 'Objetivo_Promedio', 'Rendimiento_%', 'Resultado_ARS']].style.apply(highlight_target, axis=1), use_container_width=True)

        # --- MOTOR DE SUGERENCIAS IA (INTERNO - RESTAURADO) ---
        st.markdown("---")
        col_ia1, col_ia2 = st.columns([3,1])
        with col_ia1: st.subheader("🤖 SCANNER CUANTITATIVO (ACTIVOS EN CARTERA)")
        with col_ia2:
            if st.button("⚡ EJECUTAR SCAN INTERNO"): st.session_state.mostrar_ia = True
                
        if st.session_state.mostrar_ia:
            textos_para_pdf = []
            for _, row in df_agrupado.iterrows():
                with st.expander(f"SCAN LOG: {row['Empresa']} | ROI: {row['Rendimiento_%']}%", expanded=True):
                    t_emp = [f"ACTIVO: {row['Empresa']}"]
                    fun = inteligencia_mercado.get(row['Empresa'], "Datos estables.")
                    st.write(f"**📖 Fundamentales:** {fun}"); t_emp.append(f"Fundamentales: {fun}")
                    
                    rsi = row['RSI_Actual']
                    if row['Empresa'] == "DÓLAR OFICIAL":
                        tec = f"⚖️ PARÁMETRO DIVISA (RSI {rsi})."
                    else:
                        tec = f"⚠️ SOBRECOMPRA (RSI {rsi})." if rsi > 70 else (f"📉 SOBREVENTA (RSI {rsi})." if rsi < 30 else f"⚖️ NEUTRAL (RSI {rsi}).")
                    
                    st.write(f"**📊 Técnico:** {tec}"); t_emp.append(f"Tecnico: {tec}")
                    
                    if row['Rendimiento_%'] >= row['Objetivo_Promedio']:
                        sug = "TOMA DE GANANCIAS ACTIVADA."
                        st.success(sug)
                    elif rsi < 30 and row['Rendimiento_%'] < 0 and row['Empresa'] != "DÓLAR OFICIAL":
                        sug = "PROMEDIAR A LA BAJA SUGERIDO."
                        st.info(sug)
                    elif rsi > 70 and row['Rendimiento_%'] > 0 and row['Empresa'] != "DÓLAR OFICIAL":
                        sug = "AJUSTE DE STOP-LOSS RECOMENDADO."
                        st.warning(sug)
                    else:
                        sug = "MANTENER POSICIÓN (HOLD)."
                        st.write(sug)
                    t_emp.append(f"Sugerencia: {sug}\n")
                    textos_para_pdf.append(" | ".join(t_emp))
            
            pdf_path = crear_pdf(df_agrupado, textos_para_pdf, usuario_actual)
            with open(pdf_path, "rb") as f:
                st.download_button("📄 DESCARGAR LOG DE CARTERA (PDF)", data=f.read(), file_name=f"DSL_Log_{usuario_actual}.pdf", mime="application/octet-stream")

        # --- MOTOR DE SUGERENCIAS DE MERCADO (EXTERNO) ---
        st.markdown("---")
        st.subheader("📡 RADAR CUANTITATIVO: Oportunidades Externas")
        st.write("Escanea activos que **NO tienes en cartera** buscando anomalías de Volumen y RSI de sobreventa.")
        
        if st.button("🔍 INICIAR ESCÁNER DE MERCADO (Heavy Process)"):
            with st.spinner("Descargando y procesando flujos de mercado..."):
                activos_propios = df_agrupado['Empresa'].tolist()
                candidatos = {k: v for k, v in todos_los_cedears.items() if k not in activos_propios}
                
                sugerencias_encontradas = 0
                for emp, tk in candidatos.items():
                    data = yf.Ticker(tk).history(period="3mo")
                    if not data.empty and len(data) > 20:
                        data = calcular_indicadores(data)
                        ultimo_rsi = data['RSI'].iloc[-1]
                        volumen_actual = data['Volume'].iloc[-1]
                        volumen_promedio = data['Vol_SMA20'].iloc[-1]
                        macd = data['MACD'].iloc[-1]
                        macd_sig = data['MACD_Signal'].iloc[-1]
                        
                        if ultimo_rsi < 45 and volumen_actual > volumen_promedio:
                            sugerencias_encontradas += 1
                            respaldo = "Positivo (MACD > Señal)" if macd > macd_sig else "Esperar cruce alcista (MACD < Señal)"
                            st.markdown(f"""
                            <div class='scan-alert'>
                                <b>{emp} ({tk})</b> - Potencial de Entrada<br>
                                📉 <b>RSI:</b> {ultimo_rsi:.2f} (Zona atractiva)<br>
                                📊 <b>Volumen:</b> Ingreso de capital detectado (+{((volumen_actual/volumen_promedio)-1)*100:.0f}% sobre la media)<br>
                                ⚙️ <b>Refuerzo MACD:</b> {respaldo}
                            </div>
                            """, unsafe_allow_html=True)
                if sugerencias_encontradas == 0:
                    st.info("El Radar no detectó anomalías fuertes de compra (Volumen + RSI bajo) en el mercado externo hoy.")
    else:
        st.info("El Ledger está vacío. Inyecte datos para comenzar.")

# ==========================================
# PESTAÑA 2: SIMULADOR DE ANÁLISIS TÉCNICO
# ==========================================
with tab_tech:
    st.subheader("🔬 LABORATORIO DE ANÁLISIS TÉCNICO")
    st.write("Analiza gráficamente el comportamiento de los activos que posees en tu cartera.")
    
    if st.session_state.mi_cartera:
        df_agrupado_tech = pd.DataFrame(st.session_state.mi_cartera).groupby('Empresa').first().reset_index()
        activos_disponibles = df_agrupado_tech['Empresa'].tolist()
        
        if "DÓLAR OFICIAL" in activos_disponibles: activos_disponibles.remove("DÓLAR OFICIAL")
        
        if activos_disponibles:
            col_t1, col_t2 = st.columns([1, 3])
            with col_t1:
                activo_tech = st.selectbox("Seleccionar Activo en Cartera:", activos_disponibles)
                periodo_tech = st.selectbox("Periodo:", ["3mo", "6mo", "1y", "2y"], index=1)
                ver_bollinger = st.checkbox("Bandas de Bollinger", value=True)
                ver_sma = st.checkbox("Medias Móviles (20 y 50)", value=True)
            
            ticker_tech = mis_cedears.get(activo_tech) or lista_escaner_global.get(activo_tech)
            
            with st.spinner("Generando modelos matemáticos..."):
                df_tech = yf.Ticker(ticker_tech).history(period=periodo_tech)
                
                if not df_tech.empty:
                    df_tech.index = df_tech.index.tz_localize(None)
                    df_tech = calcular_indicadores(df_tech)
                    
                    fig_precio = go.Figure()
                    fig_precio.add_trace(go.Candlestick(
                        x=df_tech.index, open=df_tech['Open'], high=df_tech['High'], 
                        low=df_tech['Low'], close=df_tech['Close'], name="Precio"
                    ))
                    
                    if ver_bollinger:
                        fig_precio.add_trace(go.Scatter(x=df_tech.index, y=df_tech['BB_Upper'], line=dict(color='rgba(102, 252, 241, 0.3)', dash='dash'), name="BB Upper"))
                        fig_precio.add_trace(go.Scatter(x=df_tech.index, y=df_tech['BB_Lower'], line=dict(color='rgba(102, 252, 241, 0.3)', dash='dash'), name="BB Lower", fill='tonexty', fillcolor='rgba(102, 252, 241, 0.05)'))
                    
                    if ver_sma:
                        fig_precio.add_trace(go.Scatter(x=df_tech.index, y=df_tech['SMA_20'], line=dict(color='#ffea00', width=1.5), name="SMA 20"))
                        fig_precio.add_trace(go.Scatter(x=df_tech.index, y=df_tech['SMA_50'], line=dict(color='#ff4655', width=1.5), name="SMA 50"))

                    fig_precio.update_layout(
                        title=f"Acción del Precio y Volatilidad: {activo_tech}",
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#c5c6c7'),
                        xaxis_rangeslider_visible=False, height=500, margin=dict(l=0, r=0, t=40, b=0)
                    )
                    
                    fig_ind = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.5, 0.5])
                    
                    fig_ind.add_trace(go.Scatter(x=df_tech.index, y=df_tech['RSI'], line=dict(color='#66fcf1', width=2), name="RSI 14"), row=1, col=1)
                    fig_ind.add_hline(y=70, line_dash="dash", line_color="#ff4655", row=1, col=1)
                    fig_ind.add_hline(y=30, line_dash="dash", line_color="#45a29e", row=1, col=1)
                    
                    fig_ind.add_trace(go.Bar(x=df_tech.index, y=df_tech['MACD'] - df_tech['MACD_Signal'], marker_color='rgba(102, 252, 241, 0.5)', name="Histograma"), row=2, col=1)
                    fig_ind.add_trace(go.Scatter(x=df_tech.index, y=df_tech['MACD'], line=dict(color='#ffea00', width=1.5), name="MACD"), row=2, col=1)
                    fig_ind.add_trace(go.Scatter(x=df_tech.index, y=df_tech['MACD_Signal'], line=dict(color='#ff4655', width=1.5), name="Señal"), row=2, col=1)

                    fig_ind.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#c5c6c7'),
                        height=400, margin=dict(l=0, r=0, t=10, b=0)
                    )
                    
                    with col_t2:
                        st.plotly_chart(fig_precio, use_container_width=True)
                        st.plotly_chart(fig_ind, use_container_width=True)
        else:
            st.info("No hay acciones de renta variable en tu cartera para analizar.")
    else:
        st.info("Debes ingresar activos en el Ledger para habilitar el Laboratorio de Análisis Técnico.")
