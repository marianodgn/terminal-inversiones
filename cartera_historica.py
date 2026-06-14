import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
from fpdf import FPDF
import tempfile

# 1. CONFIGURACIÓN DE PÁGINA (Vivid Dark Mode)
st.set_page_config(layout="wide", page_title="Terminal Pro V7.0", page_icon="⚡")

st.markdown("""
    <style>
    .main { background-color: #0E1117; color: #E0E0E0; }
    div[data-testid="stMetricValue"] { color: #00E5FF; font-size: 28px; font-weight: 900; text-shadow: 0px 0px 8px rgba(0, 229, 255, 0.4); }
    div[data-testid="stMetricLabel"] { color: #9E9E9E; font-weight: bold; font-size: 14px; }
    .stButton>button { background-color: #2979FF; color: white; border: none; border-radius: 4px; width: 100%; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }
    .stButton>button:hover { background-color: #1565C0; box-shadow: 0px 0px 10px rgba(41, 121, 255, 0.6); }
    h1, h2, h3 { color: #FFFFFF; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    hr { border-color: #333333; }
    </style>
""", unsafe_allow_html=True)

# --- SISTEMA DE LOGIN MULTI-USUARIO ---
def check_password():
    usuarios_permitidos = {
        "mariano": "admin1234",      
        "daniel": "corneta",
        "Juan": "nomada"
    }

    if "usuario_autenticado" not in st.session_state:
        st.session_state["usuario_autenticado"] = False
        st.session_state["usuario_actual"] = None

    if not st.session_state["usuario_autenticado"]:
        st.title("⚡ Acceso a la Plataforma")
        st.subheader("🔒 Iniciar Sesión")
        usuario = st.text_input("Usuario:")
        clave = st.text_input("Contraseña:", type="password")
        
        if st.button("Ingresar"):
            if usuario in usuarios_permitidos and usuarios_permitidos[usuario] == clave:
                st.session_state["usuario_autenticado"] = True
                st.session_state["usuario_actual"] = usuario
                st.rerun()
            else:
                st.error("🚫 Usuario o contraseña incorrectos.")
        return False
    else:
        with st.sidebar:
            st.markdown(f"👤 **Usuario Activo:** `{st.session_state['usuario_actual'].upper()}`")
            if st.button("Cerrar Sesión"):
                st.session_state["usuario_autenticado"] = False
                st.session_state["usuario_actual"] = None
                st.session_state.mi_cartera = []
                st.session_state.usuario_cargado = None
                st.rerun()
        return True

if not check_password():
    st.stop()

# --- GESTIÓN DE ARCHIVOS POR USUARIO ---
def obtener_nombre_archivo():
    usuario = st.session_state["usuario_actual"]
    return f"cartera_{usuario}.csv"

def cargar_cartera():
    archivo = obtener_nombre_archivo()
    if os.path.exists(archivo):
        return pd.read_csv(archivo).to_dict('records')
    return []

def guardar_cartera():
    archivo = obtener_nombre_archivo()
    pd.DataFrame(st.session_state.mi_cartera).to_csv(archivo, index=False)

usuario_actual = st.session_state["usuario_actual"]
if 'mi_cartera' not in st.session_state or st.session_state.get('usuario_cargado') != usuario_actual:
    st.session_state.mi_cartera = cargar_cartera()
    st.session_state['usuario_cargado'] = usuario_actual

if 'mostrar_ia' not in st.session_state:
    st.session_state.mostrar_ia = False


# --- TERMINAL QUANTITATIVA ---
st.title("⚡ TERMINAL QUANTITATIVA DE INVERSIONES")
st.markdown("---")

mis_cedears = {
    "BERKSHIRE HATHAWAY": "BRKB.BA", "SALESFORCE": "CRM.BA", "JP MORGAN": "JPM.BA",
    "MCDONALDS": "MCD.BA", "MERCADO LIBRE": "MELI.BA", "MICROSTRATEGY": "MSTR.BA",
    "SERVICE NOW": "NOW.BA", "NU HOLDINGS": "NU.BA", "PROCTER GAMBLE": "PG.BA",
    "PALANTIR": "PLTR.BA", "SPDR S P 500": "SPY.BA"
}

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
    "DÓLAR OFICIAL": "Reserva de valor básica. Cotización basada en el tipo de cambio oficial mayorista."
}

def calcular_rsi(precios, periodos=14):
    if len(precios) < periodos + 1: return 0
    delta = precios.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periodos).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periodos).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi.iloc[-1], 2)

def crear_pdf(df, reporte_ia_textos, usuario):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=f"REPORTE ESTRATEGICO - USUARIO: {usuario.upper()}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="1. Resumen de Activos (Agrupados)", ln=True)
    pdf.set_font("Arial", '', 10)
    for _, row in df.iterrows():
        linea = f"{row['Empresa']} | Cantidad: {row['Nominales']} | Costo Promedio: ${row['Costo_Entrada_Promedio']:,.2f} | Rto: {row['Rendimiento_%']}%"
        linea = linea.encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(200, 8, txt=linea, ln=True)
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="2. Analisis de Inteligencia de Mercado (IA)", ln=True)
    pdf.set_font("Arial", '', 10)
    
    for texto in reporte_ia_textos:
        txt_limpio = texto.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, txt=txt_limpio)
        pdf.ln(4)
        
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    pdf.output(path)
    return path

# BARRA LATERAL CON SELECTOR DE DIVISAS
with st.sidebar:
    st.header("⚙️ DATA INJECTION")
    
    tipo_ingreso = st.radio("Categoría de Activo:", ["Renta Variable (CEDEARs)", "Divisa (Dólar Oficial)"])
    
    if tipo_ingreso == "Renta Variable (CEDEARs)":
        seleccion = st.selectbox("Activo:", list(mis_cedears.keys()))
        ticker_activo = mis_cedears[seleccion]
        etiqueta_cantidad = "Nominales:"
    else:
        seleccion = "DÓLAR OFICIAL"
        ticker_activo = "ARS=X"
        etiqueta_cantidad = "Cantidad de Dólares (USD):"
        
    nominales = st.number_input(etiqueta_cantidad, min_value=1.0, step=1.0)
    fecha = st.date_input("Fecha de Compra:")
    objetivo = st.number_input("Objetivo de Ganancia (%):", min_value=1.0, value=15.0, step=1.0)
    
    if st.button("AÑADIR ORDEN AL REGISTRO"):
        hist = yf.Ticker(ticker_activo).history(start=fecha, end=fecha + pd.Timedelta(days=5))
        if not hist.empty:
            nuevo_id = int(pd.Timestamp.now().timestamp() * 1000)
            st.session_state.mi_cartera.append({
                "ID_Orden": nuevo_id,
                "Empresa": seleccion, "Ticker": ticker_activo, "Nominales": nominales, 
                "Costo_Entrada": round(hist['Close'].iloc[0], 2),
                "Objetivo_%": objetivo,
                "Fecha_Compra": str(fecha)
            })
            guardar_cartera()
            st.session_state.mostrar_ia = False
            st.success(f"Órden Registrada para {usuario_actual}: {seleccion}")
        else:
            st.error("Mercado cerrado o sin datos en esa fecha.")

    st.markdown("---")
    if st.session_state.mi_cartera:
        df_historial = pd.DataFrame(st.session_state.mi_cartera)
        st.write("**Órdenes Históricas (Modo Edición)**")
        st.dataframe(df_historial[['Empresa', 'Fecha_Compra', 'Nominales']], hide_index=True)
        
        opciones_borrar = [f"{row['Empresa']} ({row['Fecha_Compra']}) - {row['Nominales']}" for _, row in df_historial.iterrows()]
        a_borrar_idx = st.selectbox("Seleccionar órden a purgar:", range(len(opciones_borrar)), format_func=lambda x: opciones_borrar[x])
        
        if st.button("PURGAR ÓRDEN SELECCIONADA"):
            del st.session_state.mi_cartera[a_borrar_idx]
            guardar_cartera()
            st.session_state.mostrar_ia = False
            st.rerun()

# MOTOR DE AGRUPACIÓN Y MÉTRICAS
if st.session_state.mi_cartera:
    df_raw = pd.DataFrame(st.session_state.mi_cartera)
    
    df_raw['Capital_Fila'] = df_raw['Costo_Entrada'] * df_raw['Nominales']
    df_agrupado = df_raw.groupby(['Empresa', 'Ticker']).agg(
        Nominales=('Nominales', 'sum'),
        Capital_Invertido=('Capital_Fila', 'sum'),
        Objetivo_Promedio=('Objetivo_%', 'mean')
    ).reset_index()
    
    df_agrupado['Costo_Entrada_Promedio'] = df_agrupado['Capital_Invertido'] / df_agrupado['Nominales']
    
    precios_actuales, rsis = [], []
    for t in df_agrupado['Ticker']:
        hist_1mo = yf.Ticker(t).history(period="3mo")
        if not hist_1mo.empty:
            precios_actuales.append(round(hist_1mo['Close'].iloc[-1], 2))
            rsis.append(calcular_rsi(hist_1mo['Close']))
        else:
            precios_actuales.append(0)
            rsis.append(0)
            
    df_agrupado['Precio_Actual'] = precios_actuales
    df_agrupado['RSI_Actual'] = rsis
    df_agrupado['Valor_Actual'] = df_agrupado['Precio_Actual'] * df_agrupado['Nominales']
    df_agrupado['Resultado_ARS'] = df_agrupado['Valor_Actual'] - df_agrupado['Capital_Invertido']
    df_agrupado['Rendimiento_%'] = round((df_agrupado['Resultado_ARS'] / df_agrupado['Capital_Invertido']) * 100, 2)
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("CAPITAL DESPLEGADO", f"$ {df_agrupado['Capital_Invertido'].sum():,.2f}")
    kpi2.metric("VALOR DE MERCADO", f"$ {df_agrupado['Valor_Actual'].sum():,.2f}")
    
    resultado_total = df_agrupado['Resultado_ARS'].sum()
    kpi3.metric("P/L NETO (ARS)", f"$ {resultado_total:,.2f}")
    rendimiento_global = ((df_agrupado['Valor_Actual'].sum() / df_agrupado['Capital_Invertido'].sum()) - 1) * 100
    kpi4.metric("RENDIMIENTO GLOBAL", f"{rendimiento_global:.2f} %")
    
    st.markdown("---")
    
    # GRÁFICOS PRINCIPALES
    col_graf1, col_graf2 = st.columns(2)
    paleta_dona = ['#00E5FF', '#FF007F', '#B2FF59', '#FFEA00', '#D500F9', '#FF3D00']
    
    with col_graf1:
        fig_pie = px.pie(df_agrupado, values='Valor_Actual', names='Empresa', hole=0.4,
                         title=f"Exposición de Capital de {usuario_actual.capitalize()}", 
                         color_discrete_sequence=paleta_dona)
        fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#FFFFFF'))
        fig_pie.update_traces(marker=dict(line=dict(color='#0E1117', width=2)))
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_graf2:
        fig_wf = go.Figure(go.Waterfall(
            name="P/L", orientation="v",
            measure=["relative"] * len(df_agrupado) + ["total"],
            x=df_agrupado['Empresa'].tolist() + ["NET P/L"],
            y=df_agrupado['Resultado_ARS'].tolist() + [resultado_total],
            textposition="outside", text=[f"${v:,.0f}" for v in df_agrupado['Resultado_ARS']] + [f"${resultado_total:,.0f}"],
            decreasing={"marker":{"color":"#FF1744"}}, 
            increasing={"marker":{"color":"#00E676"}}, 
            totals={"marker":{"color":"#00E5FF"}}      
        ))
        fig_wf.update_layout(title="Distribución de Ganancia/Pérdida Ponderada", 
                             paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#FFFFFF'))
        st.plotly_chart(fig_wf, use_container_width=True)

    # === NUEVO GRÁFICO: TENDENCIA HISTÓRICA (COSTO VS MERCADO) ===
    st.markdown("---")
    st.subheader("📈 ANÁLISIS DE TENDENCIA HISTÓRICA")
    st.write("Selecciona un activo para comparar su precio de mercado contra tu costo promedio ponderado a lo largo del tiempo.")
    
    activo_tendencia = st.selectbox("Seleccionar activo para análisis detallado:", df_agrupado['Empresa'].tolist())
    
    if activo_tendencia:
        # Filtrar solo las compras de ese activo
        df_compras_activo = df_raw[df_raw['Empresa'] == activo_tendencia].copy()
        ticker_tend = df_compras_activo['Ticker'].iloc[0]
        
        # Convertir fechas para operar
        df_compras_activo['Fecha_Compra'] = pd.to_datetime(df_compras_activo['Fecha_Compra'])
        df_compras_activo = df_compras_activo.sort_values('Fecha_Compra')
        
        fecha_primer_compra = df_compras_activo['Fecha_Compra'].min()
        
        # Obtener datos de mercado desde la primera compra
        hist_tend = yf.Ticker(ticker_tend).history(start=fecha_primer_compra)
        
        if not hist_tend.empty:
            hist_tend.index = hist_tend.index.tz_localize(None) # Limpiar zonas horarias
            fechas_mercado = hist_tend.index
            
            # Calcular el Costo Promedio Ponderado para cada día
            costos_diarios = []
            
            for fecha_dia in fechas_mercado:
                # Compras realizadas hasta este día inclusive
                compras_hasta_hoy = df_compras_activo[df_compras_activo['Fecha_Compra'].dt.date <= fecha_dia.date()]
                
                if not compras_hasta_hoy.empty:
                    nom_total = compras_hasta_hoy['Nominales'].sum()
                    cap_total = (compras_hasta_hoy['Costo_Entrada'] * compras_hasta_hoy['Nominales']).sum()
                    costos_diarios.append(cap_total / nom_total)
                else:
                    costos_diarios.append(0)
            
            # Crear gráfico de líneas
            fig_tend = go.Figure()
            
            # Línea de Mercado
            fig_tend.add_trace(go.Scatter(x=fechas_mercado, y=hist_tend['Close'].values, 
                                          mode='lines', name='Precio Mercado', 
                                          line=dict(color='#00E5FF', width=2)))
            
            # Línea de Costo Promedio
            fig_tend.add_trace(go.Scatter(x=fechas_mercado, y=costos_diarios, 
                                          mode='lines', name='Costo Promedio (Tu Inversión)', 
                                          line=dict(color='#FFEA00', width=2, dash='dash')))
            
            fig_tend.update_layout(title=f"Evolución: Mercado vs Tu Costo ({activo_tendencia})",
                                   paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                                   font=dict(color='#FFFFFF'), hovermode="x unified",
                                   legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))
                                   
            st.plotly_chart(fig_tend, use_container_width=True)
        else:
            st.warning("Aún no hay suficientes datos históricos de mercado para graficar esta tendencia.")

    # MATRIZ DE ACTIVOS
    st.markdown("---")
    st.subheader("📊 MATRIZ DE ACTIVOS PONDERADOS")
    def highlight_target(row):
        if row['Rendimiento_%'] >= row['Objetivo_Promedio']:
            return ['background-color: rgba(0, 230, 118, 0.2); color: #00E676; font-weight: bold; border-left: 4px solid #00E676;'] * len(row)
        elif row['Rendimiento_%'] < 0:
            return ['background-color: rgba(255, 23, 68, 0.1); color: #FF8A80;'] * len(row)
        return ['color: #E0E0E0;'] * len(row)

    df_mostrar = df_agrupado[['Empresa', 'Nominales', 'Costo_Entrada_Promedio', 'Precio_Actual', 'RSI_Actual', 'Objetivo_Promedio', 'Rendimiento_%', 'Resultado_ARS']]
    st.dataframe(df_mostrar.style.apply(highlight_target, axis=1), use_container_width=True)

    # MOTOR IA Y EXPORTACIÓN
    st.markdown("---")
    col_ia1, col_ia2 = st.columns([3,1])
    with col_ia1:
        st.subheader("🤖 Análisis de Consenso e IA")
    
    with col_ia2:
        if st.button("⚡ EJECUTAR MOTOR IA"):
            st.session_state.mostrar_ia = True
            
    if st.session_state.mostrar_ia:
        textos_para_pdf = []
        for _, row in df_agrupado.iterrows():
            with st.expander(f"SCAN {row['Empresa']} | ROI: {row['Rendimiento_%']}%", expanded=True):
                
                texto_empresa = []
                texto_empresa.append(f"ACTIVO: {row['Empresa']}")
                
                fundamentales = inteligencia_mercado.get(row['Empresa'], "Datos estables. Sujeto a volatilidad.")
                st.write(f"**📖 Datos Fundamentales:** {fundamentales}")
                texto_empresa.append(f"Fundamentales: {fundamentales}")
                
                rsi = row['RSI_Actual']
                if row['Empresa'] == "DÓLAR OFICIAL":
                    tecnico = f"⚖️ PARÁMETRO DIVISA. El RSI ({rsi}) no es un indicador de sobrecompra tradicional debido al crawling peg."
                else:
                    if rsi > 70:
                        tecnico = f"⚠️ SOBRECOMPRA (RSI {rsi}). Riesgo técnico de corrección inminente."
                    elif rsi < 30:
                        tecnico = f"📉 SOBREVENTA (RSI {rsi}). Descuento estadístico masivo. Posible rebote."
                    else:
                        tecnico = f"⚖️ NEUTRAL (RSI {rsi}). Estabilidad tendencial."
                
                st.write(f"**📊 Parámetro Técnico:** {tecnico}")
                texto_empresa.append(f"Tecnico: {tecnico}")
                
                st.write("**💡 ACCIÓN RECOMENDADA:**")
                if row['Rendimiento_%'] >= row['Objetivo_Promedio']:
                    sug = f"TOMA DE GANANCIAS ACTIVADA. Objetivo del {row['Objetivo_Promedio']}% superado. Liquidar parcial."
                    st.success(sug)
                elif rsi < 30 and row['Rendimiento_%'] < 0 and row['Empresa'] != "DÓLAR OFICIAL":
                    sug = "PROMEDIAR A LA BAJA. RSI crítico con P/L negativo. Aumentar nominales para mejorar Promedio."
                    st.info(sug)
                elif rsi > 70 and row['Rendimiento_%'] > 0 and row['Empresa'] != "DÓLAR OFICIAL":
                    sug = "AJUSTE STOP-LOSS. Activo caro pero en ganancia. Asegurar posiciones."
                    st.warning(sug)
                else:
                    sug = "HOLD (MANTENER). Conservar posición estructural en la cartera."
                    st.write(sug)
                texto_empresa.append(f"Sugerencia: {sug}\n")
                
                textos_para_pdf.append(" | ".join(texto_empresa))
        
        pdf_path = crear_pdf(df_agrupado, textos_para_pdf, usuario_actual)
        with open(pdf_path, "rb") as pdf_file:
            PDFbyte = pdf_file.read()
        
        st.markdown("---")
        st.download_button(
            label="📄 DESCARGAR REPORTE PROFESIONAL (PDF)",
            data=PDFbyte,
            file_name=f"Reporte_IA_{usuario_actual}.pdf",
            mime="application/octet-stream"
        )

else:
    st.info("NO HAY DATOS EN SISTEMA. Utiliza la terminal izquierda (DATA INJECTION) para ingresar tu primera orden y encender los motores.")
