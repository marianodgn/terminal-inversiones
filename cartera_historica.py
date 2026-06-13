import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
from fpdf import FPDF
import tempfile
import base64
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from fpdf import FPDF
import tempfile
import base64

# --- SISTEMA DE LOGIN (PUERTA DE SEGURIDAD) ---
def check_password():
    """Devuelve True si la contraseña es correcta."""
    def password_entered():
        # AQUÍ DEFINES TU CONTRASEÑA MAESTRA
        if st.session_state["password"] == "admin1234": 
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Borrar clave por seguridad
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔑 Ingrese su clave de acceso", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔑 Ingrese su clave de acceso", type="password", on_change=password_entered, key="password")
        st.error("🚫 Acceso Denegado. Contraseña incorrecta.")
        return False
    else:
        return True

# Si la contraseña no es correcta, detenemos la app aquí mismo
if not check_password():
    st.stop()

# --- AQUÍ EMPIEZA TODO TU CÓDIGO ORIGINAL DE LA TERMINAL ---
# st.set_page_config(layout="wide", page_title="Terminal Pro V4.0", page_icon="⚡")
# ... (todo el resto de tu código) ...

# 1. CONFIGURACIÓN DE PÁGINA (Vivid Dark Mode)
st.set_page_config(layout="wide", page_title="Terminal Pro V4.0", page_icon="⚡")

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

st.title("⚡ TERMINAL QUANTITATIVA DE INVERSIONES")
st.markdown("---")

# 2. ARCHIVO DE GUARDADO Y ESTADOS
ARCHIVO_CARTERA = "cartera_guardada.csv"

def cargar_cartera():
    if os.path.exists(ARCHIVO_CARTERA):
        return pd.read_csv(ARCHIVO_CARTERA).to_dict('records')
    return []

def guardar_cartera():
    pd.DataFrame(st.session_state.mi_cartera).to_csv(ARCHIVO_CARTERA, index=False)

if 'mi_cartera' not in st.session_state:
    st.session_state.mi_cartera = cargar_cartera()
if 'mostrar_ia' not in st.session_state:
    st.session_state.mostrar_ia = False
if 'reporte_pdf_generado' not in st.session_state:
    st.session_state.reporte_pdf_generado = None

mis_cedears = {
    "BERKSHIRE HATHAWAY": "BRKB.BA", "SALESFORCE": "CRM.BA", "JP MORGAN": "JPM.BA",
    "MCDONALDS": "MCD.BA", "MERCADO LIBRE": "MELI.BA", "MICROSTRATEGY": "MSTR.BA",
    "SERVICE NOW": "NOW.BA", "NU HOLDINGS": "NU.BA", "PROCTER GAMBLE": "PG.BA",
    "PALANTIR": "PLTR.BA", "SPDR S P 500": "SPY.BA"
}

inteligencia_mercado = {
    "BERKSHIRE HATHAWAY": "Wall Street destaca su enorme reserva de efectivo. Refugio seguro en volatilidad.",
    "SALESFORCE": "Visión optimista por su integración de IA (Einstein) en su ecosistema CRM.",
    "JP MORGAN": "Sólido reporte de ganancias. El sector bancario se beneficia de tasas actuales.",
    "MCDONALDS": "Acción defensiva. Sugerencia de mantener por su estabilidad frente a inflación.",
    "MERCADO LIBRE": "Líder en e-commerce LATAM. Perspectivas de crecimiento a largo plazo muy alcistas.",
    "MICROSTRATEGY": "Activo de altísima volatilidad, proxy del Bitcoin. Riesgo institucional alto.",
    "SERVICE NOW": "Fuerte crecimiento en suscripciones corporativas por digitalización.",
    "NU HOLDINGS": "Crecimiento explosivo en LATAM. Warren Buffett mantiene posición.",
    "PROCTER GAMBLE": "Acción hiper-defensiva. Funciona como ancla de estabilidad.",
    "PALANTIR": "Contratos gubernamentales de IA impulsan rentabilidad. Sentimiento muy optimista.",
    "SPDR S P 500": "Índice principal del mercado. Acumulación constante a largo plazo recomendada."
}

def calcular_rsi(precios, periodos=14):
    if len(precios) < periodos + 1: return 0
    delta = precios.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periodos).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periodos).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi.iloc[-1], 2)

# Función para generar PDF
def crear_pdf(df, reporte_ia_textos):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="REPORTE ESTRATEGICO DE PORTAFOLIO", ln=True, align='C')
    pdf.ln(10)
    
    # Resumen numérico
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="1. Resumen de Activos (Agrupados)", ln=True)
    pdf.set_font("Arial", '', 10)
    for _, row in df.iterrows():
        linea = f"{row['Empresa']} | Nominales: {row['Nominales']} | Precio Promedio: ${row['Costo_Entrada_Promedio']:,.2f} | Rto: {row['Rendimiento_%']}%"
        # Limpiar caracteres conflictivos
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
        
    # Guardar en archivo temporal
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    pdf.output(path)
    return path

# 3. BARRA LATERAL (OPERACIONES MÚLTIPLES)
with st.sidebar:
    st.header("⚙️ DATA INJECTION")
    seleccion = st.selectbox("Activo:", list(mis_cedears.keys()))
    nominales = st.number_input("Nominales:", min_value=1)
    fecha = st.date_input("Fecha de Compra:")
    objetivo = st.number_input("Objetivo de Ganancia (%):", min_value=1.0, value=15.0, step=1.0)
    
    if st.button("AÑADIR ORDEN AL REGISTRO"):
        ticker = mis_cedears[seleccion]
        hist = yf.Ticker(ticker).history(start=fecha, end=fecha + pd.Timedelta(days=5))
        if not hist.empty:
            # Se crea un ID único basado en el timestamp real
            nuevo_id = int(pd.Timestamp.now().timestamp() * 1000)
            st.session_state.mi_cartera.append({
                "ID_Orden": nuevo_id,
                "Empresa": seleccion, "Ticker": ticker, "Nominales": nominales, 
                "Costo_Entrada": round(hist['Close'].iloc[0], 2),
                "Objetivo_%": objetivo,
                "Fecha_Compra": str(fecha)
            })
            guardar_cartera()
            st.session_state.mostrar_ia = False
            st.success(f"Órden Registrada: {seleccion}")
        else:
            st.error("Mercado cerrado o sin datos en esa fecha.")

    st.markdown("---")
    if st.session_state.mi_cartera:
        df_historial = pd.DataFrame(st.session_state.mi_cartera)
        st.write("**Órdenes Históricas (Modo Edición)**")
        # Mostrar las órdenes individuales para poder borrar una compra específica
        st.dataframe(df_historial[['Empresa', 'Fecha_Compra', 'Nominales']], hide_index=True)
        
        opciones_borrar = [f"{row['Empresa']} ({row['Fecha_Compra']}) - {row['Nominales']} nom." for _, row in df_historial.iterrows()]
        a_borrar_idx = st.selectbox("Seleccionar órden a purgar:", range(len(opciones_borrar)), format_func=lambda x: opciones_borrar[x])
        
        if st.button("PURGAR ÓRDEN SELECCIONADA"):
            del st.session_state.mi_cartera[a_borrar_idx]
            guardar_cartera()
            st.session_state.mostrar_ia = False
            st.rerun()

# 4. MOTOR DE AGRUPACIÓN Y MÉTRICAS GLOBALES
if st.session_state.mi_cartera:
    df_raw = pd.DataFrame(st.session_state.mi_cartera)
    
    # === AGRUPACIÓN TOTAL POR TITULO ===
    df_raw['Capital_Fila'] = df_raw['Costo_Entrada'] * df_raw['Nominales']
    df_agrupado = df_raw.groupby(['Empresa', 'Ticker']).agg(
        Nominales=('Nominales', 'sum'),
        Capital_Invertido=('Capital_Fila', 'sum'),
        Objetivo_Promedio=('Objetivo_%', 'mean')
    ).reset_index()
    
    df_agrupado['Costo_Entrada_Promedio'] = df_agrupado['Capital_Invertido'] / df_agrupado['Nominales']
    
    # Procesar precios en vivo y RSI sobre la data agrupada
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
    
    # KPIs Superiores
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("CAPITAL DESPLEGADO", f"$ {df_agrupado['Capital_Invertido'].sum():,.2f}")
    kpi2.metric("VALOR DE MERCADO", f"$ {df_agrupado['Valor_Actual'].sum():,.2f}")
    
    resultado_total = df_agrupado['Resultado_ARS'].sum()
    kpi3.metric("P/L NETO (ARS)", f"$ {resultado_total:,.2f}")
    rendimiento_global = ((df_agrupado['Valor_Actual'].sum() / df_agrupado['Capital_Invertido'].sum()) - 1) * 100
    kpi4.metric("RENDIMIENTO GLOBAL", f"{rendimiento_global:.2f} %")
    
    st.markdown("---")
    
    # 5. GRÁFICOS VÍVIDOS PARA DATA-VIZ
    col_graf1, col_graf2 = st.columns(2)
    
    # Paleta Vívida Neon Plotly
    paleta_dona = ['#00E5FF', '#FF007F', '#B2FF59', '#FFEA00', '#D500F9', '#FF3D00']
    
    with col_graf1:
        fig_pie = px.pie(df_agrupado, values='Valor_Actual', names='Empresa', hole=0.4,
                         title="Exposición de Capital por Activo", 
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
            decreasing={"marker":{"color":"#FF1744"}}, # Neon Red
            increasing={"marker":{"color":"#00E676"}}, # Neon Green
            totals={"marker":{"color":"#00E5FF"}}      # Cyan for total
        ))
        fig_wf.update_layout(title="Distribución de Ganancia/Pérdida Ponderada", 
                             paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#FFFFFF'))
        st.plotly_chart(fig_wf, use_container_width=True)

    # 6. MATRIZ DE ACTIVOS AGRUPADOS CON HIGHLIGHT
    st.subheader("📊 MATRIZ DE ACTIVOS PONDERADOS")
    def highlight_target(row):
        if row['Rendimiento_%'] >= row['Objetivo_Promedio']:
            return ['background-color: rgba(0, 230, 118, 0.2); color: #00E676; font-weight: bold; border-left: 4px solid #00E676;'] * len(row)
        elif row['Rendimiento_%'] < 0:
            return ['background-color: rgba(255, 23, 68, 0.1); color: #FF8A80;'] * len(row)
        return ['color: #E0E0E0;'] * len(row)

    # Ordenar y formatear para mostrar
    df_mostrar = df_agrupado[['Empresa', 'Nominales', 'Costo_Entrada_Promedio', 'Precio_Actual', 'RSI_Actual', 'Objetivo_Promedio', 'Rendimiento_%', 'Resultado_ARS']]
    st.dataframe(df_mostrar.style.apply(highlight_target, axis=1), use_container_width=True)

    # 7. MOTOR IA Y EXPORTACIÓN PDF
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
                elif rsi < 30 and row['Rendimiento_%'] < 0:
                    sug = "PROMEDIAR A LA BAJA. RSI crítico con P/L negativo. Aumentar nominales para mejorar Promedio."
                    st.info(sug)
                elif rsi > 70 and row['Rendimiento_%'] > 0:
                    sug = "AJUSTE STOP-LOSS. Activo caro pero en ganancia. Asegurar posiciones."
                    st.warning(sug)
                else:
                    sug = "HOLD (MANTENER). Esperar confirmación de volumen o tendencia."
                    st.write(sug)
                texto_empresa.append(f"Sugerencia: {sug}\n")
                
                textos_para_pdf.append(" | ".join(texto_empresa))
        
        # Generar botón PDF
        pdf_path = crear_pdf(df_agrupado, textos_para_pdf)
        with open(pdf_path, "rb") as pdf_file:
            PDFbyte = pdf_file.read()
        
        st.markdown("---")
        st.download_button(
            label="📄 DESCARGAR REPORTE PROFESIONAL (PDF)",
            data=PDFbyte,
            file_name="Reporte_Cuantitativo_IA.pdf",
            mime="application/octet-stream"
        )

else:
    st.info("NO HAY DATOS EN SISTEMA. Utiliza la terminal izquierda (DATA INJECTION) para ingresar tu primera orden y encender los motores.")