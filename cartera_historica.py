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
import json

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
                st.session_state.update({"usuario_autenticado": False, "usuario_actual": None, "mi_cartera": [], "saldo_reserva_resultados": 0.0, "saldo_capital_reserva": 0.0, "usuario_cargado": None})
                st.rerun()
        return True

if not check_password(): st.stop()

# --- GESTIÓN DE DATOS ---
COLUMNAS_CARTERA = [
    "ID_Orden", "Empresa", "Ticker", "Nominales", "Costo_Entrada", "Objetivo_%",
    "Fecha_Compra", "Origen_Capital", "Aporte_Externo", "Uso_Reserva_Resultados"
]
COLUMNAS_MOVIMIENTOS_RESERVA = ["Fecha_Movimiento", "Tipo", "Concepto", "Activo", "Importe_Capital", "Resultado_Neto", "Saldo_Capital_Reserva", "Saldo_Reserva_Neta", "Saldo_Reserva"]

def obtener_nombre_archivo(): return f"cartera_{st.session_state['usuario_actual']}.csv"
def obtener_nombre_reserva(): return f"reserva_resultados_{st.session_state['usuario_actual']}.csv"
def obtener_nombre_movimientos(): return f"movimientos_reserva_{st.session_state['usuario_actual']}.csv"
def obtener_nombre_puntos_recuperacion(): return f"puntos_recuperacion_{st.session_state['usuario_actual']}.json"
def leer_csv_seguro(archivo, columnas=None):
    if not os.path.exists(archivo) or os.path.getsize(archivo) == 0:
        return pd.DataFrame(columns=columnas)
    try:
        return pd.read_csv(archivo)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=columnas)
def numero_seguro(valor, default=0.0):
    numero = pd.to_numeric(valor, errors='coerce')
    return float(default) if pd.isna(numero) else float(numero)
def cargar_cartera(): return leer_csv_seguro(obtener_nombre_archivo(), COLUMNAS_CARTERA).to_dict('records')
def guardar_cartera(): pd.DataFrame(st.session_state.mi_cartera, columns=COLUMNAS_CARTERA).to_csv(obtener_nombre_archivo(), index=False)
def cargar_saldos_reserva():
    df_reserva = leer_csv_seguro(obtener_nombre_reserva(), ['Saldo_Capital_Reserva', 'Saldo_Reserva_Neta', 'Saldo_Reserva'])
    if not df_reserva.empty:
        if 'Saldo_Reserva_Neta' in df_reserva.columns:
            saldo_neto = numero_seguro(df_reserva['Saldo_Reserva_Neta'].iloc[-1])
        elif 'Saldo_Reserva' in df_reserva.columns:
            saldo_neto = numero_seguro(df_reserva['Saldo_Reserva'].iloc[-1])
        else:
            saldo_neto = 0.0
        saldo_capital = numero_seguro(df_reserva['Saldo_Capital_Reserva'].iloc[-1], max(saldo_neto, 0.0)) if 'Saldo_Capital_Reserva' in df_reserva.columns else max(saldo_neto, 0.0)
        return saldo_capital, saldo_neto
    return 0.0, 0.0
def guardar_saldos_reserva():
    pd.DataFrame([{
        'Saldo_Capital_Reserva': round(float(st.session_state.saldo_capital_reserva), 2),
        'Saldo_Reserva_Neta': round(float(st.session_state.saldo_reserva_resultados), 2),
        'Saldo_Reserva': round(float(st.session_state.saldo_reserva_resultados), 2)
    }]).to_csv(obtener_nombre_reserva(), index=False)
def registrar_movimiento_reserva(tipo, concepto, importe_capital, resultado_neto, saldo_capital, saldo_neto, activo=None):
    movimiento = {
        'Fecha_Movimiento': str(pd.Timestamp.now()), 'Tipo': tipo, 'Concepto': concepto,
        'Activo': activo or '', 'Importe_Capital': round(float(importe_capital), 2),
        'Resultado_Neto': round(float(resultado_neto), 2),
        'Saldo_Capital_Reserva': round(float(saldo_capital), 2),
        'Saldo_Reserva_Neta': round(float(saldo_neto), 2), 'Saldo_Reserva': round(float(saldo_neto), 2)
    }
    archivo = obtener_nombre_movimientos()
    df_mov = leer_csv_seguro(archivo, COLUMNAS_MOVIMIENTOS_RESERVA)
    df_mov = pd.concat([df_mov, pd.DataFrame([movimiento])], ignore_index=True)
    df_mov.to_csv(archivo, index=False)

def obtener_movimientos_reserva():
    df_mov = leer_csv_seguro(obtener_nombre_movimientos(), COLUMNAS_MOVIMIENTOS_RESERVA)
    if 'Saldo_Reserva_Neta' not in df_mov.columns and 'Saldo_Reserva' in df_mov.columns:
        df_mov['Saldo_Reserva_Neta'] = df_mov['Saldo_Reserva']
    for columna in COLUMNAS_MOVIMIENTOS_RESERVA:
        if columna not in df_mov.columns:
            df_mov[columna] = 0.0 if columna in ['Importe_Capital', 'Resultado_Neto', 'Saldo_Capital_Reserva', 'Saldo_Reserva_Neta', 'Saldo_Reserva'] else ''
    return df_mov

def resetear_reservas():
    st.session_state.saldo_capital_reserva = 0.0
    st.session_state.saldo_reserva_resultados = 0.0
    guardar_saldos_reserva()
    archivo_movimientos = obtener_nombre_movimientos()
    if os.path.exists(archivo_movimientos):
        os.remove(archivo_movimientos)

def resetear_reserva_capital():
    st.session_state.saldo_capital_reserva = 0.0
    guardar_saldos_reserva()

def resetear_reserva_neta():
    st.session_state.saldo_reserva_resultados = 0.0
    guardar_saldos_reserva()

def cargar_puntos_recuperacion():
    archivo = obtener_nombre_puntos_recuperacion()
    if not os.path.exists(archivo) or os.path.getsize(archivo) == 0:
        return []
    with open(archivo, 'r', encoding='utf-8') as f:
        datos = json.load(f)
    return datos if isinstance(datos, list) else []

def guardar_puntos_recuperacion(puntos):
    with open(obtener_nombre_puntos_recuperacion(), 'w', encoding='utf-8') as f:
        json.dump(puntos, f, ensure_ascii=False, indent=2)

def crear_punto_recuperacion(nombre):
    puntos = cargar_puntos_recuperacion()
    punto = {
        'ID_Punto': int(pd.Timestamp.now().timestamp() * 1000),
        'Nombre': nombre.strip() or f"Punto {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}",
        'Fecha_Creacion': str(pd.Timestamp.now()),
        'Cartera': st.session_state.mi_cartera,
        'Saldo_Capital_Reserva': round(numero_seguro(st.session_state.saldo_capital_reserva), 2),
        'Saldo_Reserva_Neta': round(numero_seguro(st.session_state.saldo_reserva_resultados), 2),
        'Movimientos_Reserva': obtener_movimientos_reserva().to_dict('records')
    }
    puntos.append(punto)
    guardar_puntos_recuperacion(puntos)

def restaurar_punto_recuperacion(punto):
    st.session_state.mi_cartera = punto.get('Cartera', [])
    st.session_state.saldo_capital_reserva = numero_seguro(punto.get('Saldo_Capital_Reserva', 0.0))
    st.session_state.saldo_reserva_resultados = numero_seguro(punto.get('Saldo_Reserva_Neta', punto.get('Saldo_Reserva', 0.0)))
    guardar_cartera()
    guardar_saldos_reserva()
    pd.DataFrame(punto.get('Movimientos_Reserva', []), columns=COLUMNAS_MOVIMIENTOS_RESERVA).to_csv(obtener_nombre_movimientos(), index=False)

def cerrar_posicion_por_cantidad(activo, cantidad_cierre, precio_cierre):
    cantidad_pendiente = float(cantidad_cierre)
    resultado_realizado = 0.0
    capital_cerrado = 0.0
    lotes_activo = sorted(
        [pos for pos in st.session_state.mi_cartera if pos['Empresa'] == activo],
        key=lambda pos: (str(pos.get('Fecha_Compra', '')), int(pos.get('ID_Orden', 0)))
    )
    cartera_actualizada = [pos for pos in st.session_state.mi_cartera if pos['Empresa'] != activo]

    for posicion in lotes_activo:
        nominales_lote = float(posicion['Nominales'])
        if cantidad_pendiente <= 0:
            cartera_actualizada.append(posicion)
            continue

        cantidad_a_cerrar = min(nominales_lote, cantidad_pendiente)
        costo_lote = float(posicion['Costo_Entrada'])
        resultado_realizado += (float(precio_cierre) - costo_lote) * cantidad_a_cerrar
        capital_cerrado += costo_lote * cantidad_a_cerrar
        cantidad_pendiente -= cantidad_a_cerrar

        nominales_restantes = round(nominales_lote - cantidad_a_cerrar, 8)
        if nominales_restantes > 0:
            posicion_actualizada = posicion.copy()
            posicion_actualizada['Nominales'] = nominales_restantes
            cartera_actualizada.append(posicion_actualizada)

    st.session_state.mi_cartera = sorted(
        cartera_actualizada,
        key=lambda pos: (str(pos.get('Fecha_Compra', '')), int(pos.get('ID_Orden', 0)))
    )
    valor_liquidado = float(precio_cierre) * float(cantidad_cierre)
    return round(resultado_realizado, 2), round(capital_cerrado, 2), round(valor_liquidado, 2)

def obtener_precio_actual_cierre(ticker):
    hist = yf.Ticker(ticker).history(period="5d")
    if not hist.empty:
        return round(float(hist['Close'].iloc[-1]), 2)
    return 0.0

usuario_actual = st.session_state["usuario_actual"]
if 'mi_cartera' not in st.session_state or st.session_state.get('usuario_cargado') != usuario_actual:
    st.session_state.mi_cartera = cargar_cartera()
    st.session_state.saldo_capital_reserva, st.session_state.saldo_reserva_resultados = cargar_saldos_reserva()
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
        st.markdown("#### Origen del capital")
        valor_estimado_operacion = 0.0
        origen_capital = st.radio(
            "Fuente de fondeo:",
            ["Aporte de capital externo", "Reserva de resultados realizados", "Fondeo mixto"],
            help="Define si la nueva posición se financia con dinero nuevo, con ganancias/pérdidas realizadas acumuladas o con una combinación de ambas."
        )
        uso_reserva = 0.0
        if origen_capital in ["Reserva de resultados realizados", "Fondeo mixto"]:
            st.caption(f"Capital disponible en reserva: $ {st.session_state.saldo_capital_reserva:,.2f} | Resultado neto acumulado: $ {st.session_state.saldo_reserva_resultados:,.2f}")
            uso_reserva = st.number_input("Monto a imputar desde la reserva:", min_value=0.0, value=0.0, step=1000.0)
        
        if st.button("INYECCIÓN DE DATOS"):

            hist = yf.Ticker(ticker_activo).history(start=fecha, end=fecha + pd.Timedelta(days=5))
            if not hist.empty:
                costo_entrada = round(hist['Close'].iloc[0], 2)
                capital_operacion = round(costo_entrada * nominales, 2)
                if origen_capital == "Aporte de capital externo" and uso_reserva > 0:
                    st.error("Para aporte externo no debe imputar fondos desde la reserva.")
                elif uso_reserva > st.session_state.saldo_capital_reserva:
                    st.error("El monto imputado supera el saldo disponible en la reserva de resultados realizados.")
                elif uso_reserva > capital_operacion:
                    st.error("El monto imputado desde la reserva no puede superar el capital de la operación.")
                elif origen_capital == "Reserva de resultados realizados" and uso_reserva != capital_operacion:
                    st.error(f"Para fondeo íntegro desde reserva debe imputar exactamente $ {capital_operacion:,.2f}.")
                else:
                    aporte_externo = round(capital_operacion - uso_reserva, 2)
                    st.session_state.mi_cartera.append({
                        "ID_Orden": int(pd.Timestamp.now().timestamp() * 1000),
                        "Empresa": seleccion, "Ticker": ticker_activo, "Nominales": nominales, 
                        "Costo_Entrada": costo_entrada, "Objetivo_%": objetivo, "Fecha_Compra": str(fecha),
                        "Origen_Capital": origen_capital, "Aporte_Externo": aporte_externo, "Uso_Reserva_Resultados": round(uso_reserva, 2)
                    })
                    if uso_reserva > 0:
                        st.session_state.saldo_capital_reserva = numero_seguro(st.session_state.saldo_capital_reserva) - uso_reserva
                        guardar_saldos_reserva()
                        registrar_movimiento_reserva("Aplicación a inversión", f"Fondeo de {seleccion}", -uso_reserva, 0.0, st.session_state.saldo_capital_reserva, st.session_state.saldo_reserva_resultados, seleccion)
                    guardar_cartera()
                    st.session_state.mostrar_ia = False
                    st.rerun()
            else: st.error("Sin datos en esa fecha.")

        st.markdown("---")
        st.subheader("🏦 Reserva de resultados realizados")
        st.metric("Capital liquidado disponible", f"$ {st.session_state.saldo_capital_reserva:,.2f}")
        st.metric("Reserva neta acumulada", f"$ {st.session_state.saldo_reserva_resultados:,.2f}")
        st.caption("Capital liquidado = efectivo bruto de cierres. Reserva neta = ganancias menos pérdidas realizadas.")
        col_reset_capital, col_reset_neta = st.columns(2)
        with col_reset_capital:
            if st.button("RESET CAPITAL"):
                resetear_reserva_capital()
                st.session_state.mostrar_ia = False
                st.rerun()
        with col_reset_neta:
            if st.button("RESET NETA"):
                resetear_reserva_neta()
                st.session_state.mostrar_ia = False
                st.rerun()
        if st.button("RESETEAR AMBAS RESERVAS"):
            resetear_reservas()
            st.session_state.mostrar_ia = False
            st.rerun()

        st.markdown("#### Punto de recuperación")
        nombre_punto = st.text_input("Nombre del guardado:", value=f"Guardado {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
        if st.button("GUARDAR PUNTO DE RECUPERACIÓN"):
            crear_punto_recuperacion(nombre_punto)
            st.success("Punto de recuperación guardado.")
        puntos_recuperacion = cargar_puntos_recuperacion()
        if puntos_recuperacion:
            opciones_puntos = {f"{p['Nombre']} | {p['Fecha_Creacion']}": p for p in puntos_recuperacion}
            punto_seleccionado = st.selectbox("Volver a un punto guardado:", list(opciones_puntos.keys()))
            if st.button("RESTAURAR PUNTO SELECCIONADO"):
                restaurar_punto_recuperacion(opciones_puntos[punto_seleccionado])
                st.session_state.mostrar_ia = False
                st.rerun()

        with st.expander("Movimientos de reserva"):
            movimientos_reserva = obtener_movimientos_reserva()
            if movimientos_reserva.empty:
                st.info("Aún no hay cierres registrados en la reserva.")
            else:
                columnas_reserva = ['Fecha_Movimiento', 'Tipo', 'Activo', 'Importe_Capital', 'Resultado_Neto', 'Saldo_Capital_Reserva', 'Saldo_Reserva_Neta']
                st.dataframe(movimientos_reserva[columnas_reserva], use_container_width=True)

        st.markdown("---")
        if st.session_state.mi_cartera:
            df_historial = pd.DataFrame(st.session_state.mi_cartera)
            df_historial['Capital_Original'] = df_historial['Costo_Entrada'] * df_historial['Nominales']
            resumen_cierre = df_historial.groupby(['Empresa', 'Ticker']).agg(
                Nominales_Disponibles=('Nominales', 'sum'),
                Capital_Original=('Capital_Original', 'sum')
            ).reset_index()
            resumen_cierre['Costo_Promedio'] = resumen_cierre['Capital_Original'] / resumen_cierre['Nominales_Disponibles']

            opciones_activos_cierre = resumen_cierre.index.tolist()
            activo_cierre_idx = st.selectbox(
                "Activo a cerrar parcialmente:",
                opciones_activos_cierre,
                format_func=lambda idx: f"{resumen_cierre.loc[idx, 'Empresa']} ({resumen_cierre.loc[idx, 'Ticker']})"
            )
            fila_cierre = resumen_cierre.loc[activo_cierre_idx]
            activo_cierre = fila_cierre['Empresa']
            ticker_cierre = fila_cierre['Ticker']
            cantidad_disponible = float(fila_cierre['Nominales_Disponibles'])
            etiqueta_cierre = "Cantidad de divisa a cerrar:" if activo_cierre == "DÓLAR OFICIAL" else "Nominales a cerrar:"
            st.caption(f"Disponible en cartera: {cantidad_disponible:,.2f} | Costo promedio: $ {float(fila_cierre['Costo_Promedio']):,.2f}")
            if activo_cierre == "DÓLAR OFICIAL":
                cantidad_cierre = st.number_input(etiqueta_cierre, min_value=0.0, max_value=cantidad_disponible, value=min(1.0, cantidad_disponible), step=1.0)
            else:
                opciones_nominales = list(range(1, int(cantidad_disponible) + 1))
                cantidad_cierre = st.selectbox(etiqueta_cierre, opciones_nominales, index=len(opciones_nominales) - 1) if opciones_nominales else 0
            precio_actual_cierre = obtener_precio_actual_cierre(ticker_cierre)
            precio_sugerido_cierre = precio_actual_cierre if precio_actual_cierre > 0 else float(fila_cierre['Costo_Promedio'])
            st.caption(f"Precio actual de referencia: $ {precio_sugerido_cierre:,.2f} ARS. Puede ajustarlo manualmente si su precio efectivo de operación fue distinto.")
            precio_cierre = st.number_input(
                "Precio efectivo de cierre:",
                min_value=0.0,
                value=float(precio_sugerido_cierre),
                step=1.0,
                key=f"precio_cierre_{ticker_cierre}"
            )
            valor_estimado_liquidado = precio_cierre * cantidad_cierre
            resultado_estimado = (precio_cierre - float(fila_cierre['Costo_Promedio'])) * cantidad_cierre
            st.caption(f"Capital bruto estimado a reserva: $ {valor_estimado_liquidado:,.2f} | Resultado neto estimado: $ {resultado_estimado:,.2f}.")
            if st.button("CERRAR CANTIDAD Y REALIZAR RESULTADO"):
                if cantidad_cierre <= 0:
                    st.error("Debe ingresar una cantidad mayor a cero para cerrar la posición.")
                else:
                    resultado_realizado, capital_cerrado, valor_liquidado = cerrar_posicion_por_cantidad(activo_cierre, cantidad_cierre, precio_cierre)
                    st.session_state.saldo_capital_reserva = numero_seguro(st.session_state.saldo_capital_reserva) + valor_liquidado
                    st.session_state.saldo_reserva_resultados = numero_seguro(st.session_state.saldo_reserva_resultados) + resultado_realizado
                    registrar_movimiento_reserva(
                        "Cierre de posición",
                        f"Cierre parcial de {cantidad_cierre:,.2f} unidades a $ {precio_cierre:,.2f} | Costo original: $ {capital_cerrado:,.2f}",
                        valor_liquidado, resultado_realizado, st.session_state.saldo_capital_reserva, st.session_state.saldo_reserva_resultados, activo_cierre
                    )
                    guardar_saldos_reserva()
                    guardar_cartera()
                    st.session_state.mostrar_ia = False
                    st.rerun()

            st.markdown("---")
            opciones_borrar = [f"{row['Empresa']} ({row['Fecha_Compra']}) - {row['Nominales']}" for _, row in df_historial.iterrows()]
            a_borrar_idx = st.selectbox("Seleccionar para purgar sin impacto contable:", range(len(opciones_borrar)), format_func=lambda x: opciones_borrar[x])
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

        kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
        kpi1.metric("CAPITAL DESPLEGADO", f"$ {df_agrupado['Capital_Invertido'].sum():,.2f}")
        kpi2.metric("VALOR DE MERCADO", f"$ {df_agrupado['Valor_Actual'].sum():,.2f}")
        resultado_total = df_agrupado['Resultado_ARS'].sum()
        kpi3.metric("P/L NETO (ARS)", f"$ {resultado_total:,.2f}")
        kpi4.metric("RENDIMIENTO GLOBAL", f"{((df_agrupado['Valor_Actual'].sum() / df_agrupado['Capital_Invertido'].sum()) - 1) * 100:.2f} %")
        kpi5.metric("RESERVA BRUTA / NETA", f"$ {st.session_state.saldo_capital_reserva:,.2f}", f"Neta $ {st.session_state.saldo_reserva_resultados:,.2f}")

        # --- GRÁFICOS RESTAURADOS ---
        st.markdown("---")
        col_graf1, col_graf2 = st.columns(2)
        paleta_dona = ['#66fcf1', '#45a29e', '#c5c6c7', '#ffffff', '#1f2833', '#8b9dc3']
        
        with col_graf1:
            fig_pie = px.pie(df_agrupado, values='Valor_Actual', names='Empresa', hole=0.5,
                             title=f"Distribución Patrimonial", color_discrete_sequence=paleta_dona)
            fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#c5c6c7'))
            fig_pie.update_traces(marker=dict(line=dict(color='#0b0c10', width=3)))
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_graf2:
            fig_wf = go.Figure(go.Waterfall(
                name="P/L", orientation="v", measure=["relative"] * len(df_agrupado) + ["total"],
                x=df_agrupado['Empresa'].tolist() + ["NET P/L"], y=df_agrupado['Resultado_ARS'].tolist() + [resultado_total],
                textposition="outside", text=[f"${v:,.0f}" for v in df_agrupado['Resultado_ARS']] + [f"${resultado_total:,.0f}"],
                decreasing={"marker":{"color":"#ff4655"}}, increasing={"marker":{"color":"#66fcf1"}}, totals={"marker":{"color":"#45a29e"}}      
            ))
            fig_wf.update_layout(title="Influencia de Ganancia/Pérdida", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#c5c6c7'))
            st.plotly_chart(fig_wf, use_container_width=True)

        # --- MATRIZ ---
        st.markdown("---")
        st.subheader("📊 MATRIZ DEL LEDGER")
        def highlight_target(row):
            if row['Rendimiento_%'] >= row['Objetivo_Promedio']: return ['background-color: rgba(102, 252, 241, 0.15); color: #66fcf1; border-left: 4px solid #66fcf1;'] * len(row)
            elif row['Rendimiento_%'] < 0: return ['background-color: rgba(255, 70, 85, 0.1); color: #ff4655;'] * len(row)
            return ['color: #c5c6c7;'] * len(row)
        st.dataframe(df_agrupado[['Empresa', 'Nominales', 'Costo_Entrada_Promedio', 'Precio_Actual', 'RSI_Actual', 'Objetivo_Promedio', 'Rendimiento_%', 'Resultado_ARS']].style.apply(highlight_target, axis=1), use_container_width=True)

        with st.expander("🏦 Detalle de fondeo por inyección"):
            columnas_fondeo = ['Empresa', 'Fecha_Compra', 'Nominales', 'Costo_Entrada', 'Origen_Capital', 'Aporte_Externo', 'Uso_Reserva_Resultados']
            for col in columnas_fondeo:
                if col not in df_raw.columns:
                    df_raw[col] = 0.0 if col in ['Aporte_Externo', 'Uso_Reserva_Resultados'] else 'No informado'
            st.dataframe(df_raw[columnas_fondeo], use_container_width=True)
            archivo_mov = obtener_nombre_movimientos()
            if os.path.exists(archivo_mov):
                st.markdown("**Movimientos de la reserva de resultados realizados**")
                st.dataframe(obtener_movimientos_reserva(), use_container_width=True)

        # --- MOTOR DE SUGERENCIAS IA (INTERNO) ---
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
