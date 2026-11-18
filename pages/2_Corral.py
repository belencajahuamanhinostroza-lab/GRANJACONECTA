
import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

# -----------------------------------------
# RUTA PRINCIPAL DEL PROYECTO
# -----------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from mqtt_utils import (
    get_latest_telemetry,
    get_responses,
    mqtt_status
)

# -----------------------------------------
# CONFIGURACIÓN
# -----------------------------------------

st.set_page_config(
    page_title="Corral | GranjaConecta",
    page_icon="🐄",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background: #F1F8F2;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #123D2B, #286747);
}

section[data-testid="stSidebar"] * {
    color: white !important;
}

.main-title {
    color: #174B32;
    font-size: 36px;
    font-weight: 800;
}

.subtitle {
    color: #63836C;
    font-size: 14px;
}

.section-title {
    color: #174B32;
    font-size: 22px;
    font-weight: 750;
}

.metric-card {
    background: white;
    border-radius: 15px;
    padding: 17px;
    text-align: center;
    border: 1px solid #DCEBDF;
}

.metric-value {
    color: #174B32;
    font-size: 27px;
    font-weight: bold;
}

.metric-label {
    color: #63836C;
    font-size: 13px;
}

.barn-card {
    border-radius: 20px;
    padding: 20px;
    text-align: center;
    border: 2px solid #C8DDCC;
}

.gesture-card {
    background: #F1F8F2;
    border-radius: 12px;
    padding: 12px;
    text-align: center;
    min-height: 95px;
}

</style>
""", unsafe_allow_html=True)


# -----------------------------------------
# ENCABEZADO
# -----------------------------------------

st.markdown(
    '<div class="main-title">🐄 GranjaConecta</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">MÓDULO DE CONTROL INTELIGENTE · CORRAL</div>',
    unsafe_allow_html=True
)

st.write("")

connected = mqtt_status()

if connected:
    st.success("Conexión MQTT activa")
else:
    st.warning("Conectando con el ESP32 mediante MQTT...")


# -----------------------------------------
# RECIBIR TELEMETRÍA
# -----------------------------------------

data = get_latest_telemetry()

temp = data.get("temperatura")
hum = data.get("humedad")
vent = data.get("ventilacion")

door = str(data.get("puerta", "SIN DATO")).upper()


def number_or_none(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


temp = number_or_none(temp)
hum = number_or_none(hum)
vent = number_or_none(vent)


# -----------------------------------------
# ESTADO DE LA PUERTA
# -----------------------------------------

if door in ["ABIERTA", "ABIERTO", "OPEN"]:
    door_text = "PUERTA ABIERTA"
    door_emoji = "🚪"
    door_color = "#DDF2E1"

elif door in ["CERRADA", "CERRADO", "CLOSED"]:
    door_text = "PUERTA CERRADA"
    door_emoji = "🚪"
    door_color = "#DDF2E1"

else:
    door_text = "ESPERANDO ESTADO"
    door_emoji = "🚪"
    door_color = "#E9EFEA"


# -----------------------------------------
# COLOR DEL GRANERO SEGÚN TEMPERATURA
# -----------------------------------------

if temp is None:
    barn_color = "#E9EFEA"
    climate_text = "Esperando temperatura"

elif temp >= 30:
    barn_color = "#F6C18B"
    climate_text = "Temperatura elevada"

elif temp <= 15:
    barn_color = "#B9DDF5"
    climate_text = "Temperatura baja"

else:
    barn_color = "#DDF0E2"
    climate_text = "Temperatura normal"


# -----------------------------------------
# VAPOR SEGÚN HUMEDAD
# -----------------------------------------

if hum is None:
    vapor = "💨"
    humidity_text = "Esperando humedad"

elif hum >= 75:
    vapor = "🌫️ 🌫️ 🌫️"
    humidity_text = "Humedad elevada"

elif hum <= 35:
    vapor = "💨"
    humidity_text = "Humedad baja"

else:
    vapor = "🌫️"
    humidity_text = "Humedad normal"


# -----------------------------------------
# GRANERO VISUAL
# -----------------------------------------

st.markdown(
    '<div class="section-title">🏠 Vista general del granero</div>',
    unsafe_allow_html=True
)

st.write("")

barn_html = f"""
<div class="barn-card"
     style="background:{barn_color};">

    <h2 style="color:#75421F; margin-bottom:5px;">
        GRANERO
    </h2>

    <div style="font-size:30px;">
        ☀️ {vapor}
    </div>

    <div style="font-size:105px; line-height:1.4;">
        🏠
    </div>

    <div style="font-size:55px;">
        {door_emoji} 🐄 🌿
    </div>

    <h3 style="color:#174B32;">
        {door_text}
    </h3>

    <p style="color:#47765A;">
        {climate_text} · {humidity_text}
    </p>

</div>
"""

st.markdown(barn_html, unsafe_allow_html=True)

st.caption(
    "La representación de la puerta y las condiciones ambientales "
    "se actualizará con los datos recibidos del ESP32."
)


# -----------------------------------------
# INDICADORES AMBIENTALES
# -----------------------------------------

st.write("")

st.markdown(
    '<div class="section-title">📊 Estado del corral</div>',
    unsafe_allow_html=True
)

c1, c2, c3 = st.columns(3)

with c1:
    value = f"{temp:.1f} °C" if temp is not None else "—"

    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size:28px;">🌡️</div>
        <div class="metric-value">{value}</div>
        <div class="metric-label">Temperatura</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    value = f"{hum:.1f} %" if hum is not None else "—"

    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size:28px;">💧</div>
        <div class="metric-value">{value}</div>
        <div class="metric-label">Humedad</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    value = f"{vent:.0f} %" if vent is not None else "—"

    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size:28px;">🌬️</div>
        <div class="metric-value">{value}</div>
        <div class="metric-label">Ventilación</div>
    </div>
    """, unsafe_allow_html=True)


# -----------------------------------------
# CÁMARA Y RECONOCIMIENTO DE GESTOS
# -----------------------------------------

st.write("")
st.divider()

st.markdown(
    '<div class="section-title">📷 Reconocimiento de gestos</div>',
    unsafe_allow_html=True
)

st.write(
    "Coloca tu mano frente a la cámara para que el modelo "
    "entrenado reconozca el gesto y envíe la orden al ESP32."
)

camera_path = ROOT_DIR / "camera_gestos.html"

if camera_path.exists():

    components.html(
        camera_path.read_text(encoding="utf-8"),
        height=650,
        scrolling=True
    )

else:

    st.warning(
        "La cámara estará disponible cuando agreguemos "
        "camera_gestos.html a la carpeta principal del proyecto."
    )


# -----------------------------------------
# TABLA DE LOS SEIS GESTOS
# -----------------------------------------

st.markdown(
    '<div class="section-title">✋ Gestos configurados</div>',
    unsafe_allow_html=True
)

gestures = [
    ("✋", "Mano abierta", "Abrir puerta"),
    ("✊", "Puño cerrado", "Cerrar puerta"),
    ("👍", "Pulgar arriba", "Subir ventilación"),
    ("👎", "Pulgar abajo", "Bajar ventilación"),
    ("👉", "Índice derecha", "Bajar humedad"),
    ("👈", "Índice izquierda", "Subir humedad"),
]

columns = st.columns(3)

for index, (emoji, gesture, action) in enumerate(gestures):

    with columns[index % 3]:

        st.markdown(f"""
        <div class="gesture-card">
            <div style="font-size:32px;">{emoji}</div>
            <b style="color:#174B32;">{gesture}</b>
            <div style="font-size:12px; color:#63836C;">
                {action}
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.write("")


# -----------------------------------------
# ALERTAS AMBIENTALES
# -----------------------------------------

st.divider()

st.markdown(
    '<div class="section-title">🔔 Alertas ambientales</div>',
    unsafe_allow_html=True
)

with st.expander("Configurar límites de alerta"):

    col1, col2 = st.columns(2)

    with col1:
        temp_high = st.number_input(
            "Temperatura máxima (°C)",
            value=30.0
        )

        temp_low = st.number_input(
            "Temperatura mínima (°C)",
            value=15.0
        )

    with col2:
        hum_high = st.number_input(
            "Humedad máxima (%)",
            value=75.0
        )

        hum_low = st.number_input(
            "Humedad mínima (%)",
            value=35.0
        )


if temp is None or hum is None:

    st.info(
        "Esperando datos de los sensores DHT22. "
        "Comprueba que Wokwi esté ejecutándose."
    )

else:

    alerts = []

    if temp >= temp_high:
        alerts.append("🌡️ Temperatura demasiado alta.")

    if temp <= temp_low:
        alerts.append("🥶 Temperatura demasiado baja.")

    if hum >= hum_high:
        alerts.append("💧 Humedad demasiado alta.")

    if hum <= hum_low:
        alerts.append("🌵 Humedad demasiado baja.")

    if alerts:

        for alert in alerts:
            st.warning(alert)

    else:

        st.success(
            "✅ El ambiente del corral está dentro "
            "de los límites configurados."
        )


# -----------------------------------------
# RESPUESTAS DEL ESP32
# -----------------------------------------

st.divider()

st.markdown(
    '<div class="section-title">📡 Confirmaciones del ESP32</div>',
    unsafe_allow_html=True
)

responses = get_responses()

if responses:

    for response in reversed(responses[-5:]):

        if isinstance(response, dict):
            message = (
                response.get("mensaje")
                or response.get("respuesta")
                or str(response)
            )
        else:
            message = str(response)

        st.info(message)

else:

    st.caption(
        "Todavía no se han recibido confirmaciones."
    )


# -----------------------------------------
# PIE DE PÁGINA
# -----------------------------------------

st.write("")
st.caption(
    "GRANJACONECTA · TECNOLOGÍA PARA EL CAMPO"
)
