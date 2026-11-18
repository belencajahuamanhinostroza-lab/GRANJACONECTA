
import json
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from mqtt_utils import (
    get_latest_telemetry,
    get_responses,
    publish_command,
    mqtt_status
)

st.set_page_config(
    page_title="Corral | GranjaConecta",
    page_icon="🐄",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background: #f2fbf4;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #123d2b, #1e6542);
}

section[data-testid="stSidebar"] * {
    color: white !important;
}

.barn {
    background: linear-gradient(180deg, #dff3e5, #f9fff9);
    border: 2px solid #b8d9c1;
    border-radius: 20px;
    padding: 18px;
    text-align: center;
}

.barn-title {
    font-size: 1.5rem;
    font-weight: 800;
    color: #164b34;
}

.barn-door {
    font-size: 5rem;
    line-height: 1.2;
}

.barn-note {
    font-weight: 700;
    color: #164b34;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------
# TÍTULO
# ---------------------------------

st.title("🐄 Corral")

st.write(
    "Controla la puerta y la ventilación con gestos, "
    "voz o escritura. El panel se actualiza con la "
    "telemetría MQTT del ESP32."
)


# ---------------------------------
# RECIBIR DATOS DEL ESP32
# ---------------------------------

data = get_latest_telemetry()

temp = data.get("temperatura")
hum = data.get("humedad")
vent = data.get("ventilacion")

door = str(
    data.get("puerta", "Sin dato")
).upper()


# ---------------------------------
# COLOR DEL GRANERO SEGÚN TEMPERATURA
# ---------------------------------

if temp is None:
    barn_color = "#e7f3e9"
    climate = "Esperando temperatura"

elif float(temp) >= 30:
    barn_color = "#f6c18b"
    climate = "Temperatura alta"

elif float(temp) <= 15:
    barn_color = "#b8d9f4"
    climate = "Temperatura baja"

else:
    barn_color = "#dff3e5"
    climate = "Temperatura normal"


# ---------------------------------
# ESTADO VISUAL DE LA PUERTA
# ---------------------------------

if door in ("ABIERTA", "ABIERTO", "OPEN"):
    door_icon = "🚪"
    door_label = "Puerta abierta"

elif door in ("CERRADA", "CERRADO", "CLOSED"):
    door_icon = "🚪"
    door_label = "Puerta cerrada"

else:
    door_icon = "🚪"
    door_label = "Estado de puerta sin confirmar"


# ---------------------------------
# VAPOR SEGÚN HUMEDAD
# ---------------------------------

if hum is None:
    steam = "💨 Datos de humedad pendientes"

elif float(hum) >= 75:
    steam = "🌫️🌫️🌫️ Humedad alta: mucho vapor"

elif float(hum) <= 35:
    steam = "💨 Humedad baja: poco vapor"

else:
    steam = "Humedad normal: vapor habitual"


# ---------------------------------
# REPRESENTACIÓN DEL GRANERO
# ---------------------------------

st.markdown(
    f"""
    <div class="barn" style="background:{barn_color};">

        <div class="barn-title">
            🏠 GRANERO · GRANJACONECTA
        </div>

        <div style="font-size:2rem;">
            {steam}
        </div>

        <div class="barn-door">
            {door_icon} 🐄
        </div>

        <div class="barn-note">
            {door_label} · {climate}
        </div>

    </div>
    """,
    unsafe_allow_html=True
)


# ---------------------------------
# MÉTRICAS DEL CORRAL
# ---------------------------------

st.subheader("Estado ambiental y del granero")

m1, m2, m3, m4 = st.columns(4)

m1.metric(
    "Temperatura",
    f"{temp} °C" if temp is not None else "—"
)

m2.metric(
    "Humedad",
    f"{hum} %" if hum is not None else "—"
)

m3.metric(
    "Ventilación",
    f"{vent} %" if vent is not None else "—"
)

m4.metric(
    "Puerta",
    door
)


# ---------------------------------
# ALERTAS
# ---------------------------------

st.subheader("Alertas del corral")

hot = st.number_input(
    "Alerta de temperatura alta (°C)",
    value=30.0,
    step=1.0
)

cold = st.number_input(
    "Alerta de temperatura baja (°C)",
    value=15.0,
    step=1.0
)

humid_high = st.number_input(
    "Alerta de humedad alta (%)",
    value=75.0,
    step=1.0
)

humid_low = st.number_input(
    "Alerta de humedad baja (%)",
    value=35.0,
    step=1.0
)


if temp is None or hum is None:

    st.info(
        "Esperando telemetría del ESP32. "
        "Inicia Wokwi y comprueba la conexión MQTT."
    )

else:

    alerts = []

    if float(temp) >= hot:
        alerts.append("🌡️ Temperatura elevada.")

    if float(temp) <= cold:
        alerts.append("🥶 Temperatura baja.")

    if float(hum) >= humid_high:
        alerts.append("💧 Humedad elevada: hay mucho vapor.")

    if float(hum) <= humid_low:
        alerts.append("🌵 Humedad baja: hay poco vapor.")

    if alerts:

        for alert in alerts:
            st.warning(alert)

    else:
        st.success(
            "✅ Temperatura y humedad dentro "
            "de los rangos configurados."
        )


# ---------------------------------
# CÁMARA Y RECONOCIMIENTO DE GESTOS
# ---------------------------------

st.divider()

st.subheader("📷 Cámara: reconocimiento de gestos")

st.write(
    "Permite el acceso a la cámara cuando el navegador "
    "lo solicite. Mantén un gesto estable un instante "
    "para evitar órdenes repetidas."
)

html_path = (
    Path(__file__).resolve().parents[1]
    / "camera_gestos.html"
)

if html_path.exists():

    components.html(
        html_path.read_text(encoding="utf-8"),
        height=650,
        scrolling=True
    )

else:

    st.error(
        "No se encontró camera_gestos.html "
        "en la raíz del repositorio."
    )


# ---------------------------------
# CONTROL POR ESCRITURA
# ---------------------------------

st.divider()

st.subheader("🎙️ Control por escritura")

texto = st.text_input(
    "Escribe una orden",
    placeholder=(
        "Ej.: abrir puerta, cerrar puerta, "
        "subir ventilación..."
    )
)


if st.button("Enviar orden escrita"):

    t = texto.lower().strip()

    mapping = {

        "abrir puerta": "PUERTA_ABRIR",
        "abre puerta": "PUERTA_ABRIR",

        "cerrar puerta": "PUERTA_CERRAR",
        "cierra puerta": "PUERTA_CERRAR",

        "subir ventilacion": "VENTILACION_SUBIR",
        "aumentar ventilacion": "VENTILACION_SUBIR",

        "bajar ventilacion": "VENTILACION_BAJAR",
        "disminuir ventilacion": "VENTILACION_BAJAR",

        "subir humedad": "HUMEDAD_SUBIR",
        "aumentar humedad": "HUMEDAD_SUBIR",

        "bajar humedad": "HUMEDAD_BAJAR",
        "disminuir humedad": "HUMEDAD_BAJAR",
    }

    cmd = mapping.get(t)

    if cmd:

        ok, msg = publish_command(cmd)

        if ok:
            st.success(msg)
        else:
            st.error(msg)

    else:

        st.warning(
            "No reconocí esa orden. Prueba: abrir puerta, "
            "cerrar puerta, subir ventilación, "
            "bajar ventilación, subir humedad "
            "o bajar humedad."
        )


# ---------------------------------
# RESPUESTAS DEL ESP32
# ---------------------------------

st.subheader("Respuestas recientes del ESP32")

responses = get_responses()

if responses:

    for item in reversed(responses[-5:]):
        st.write(f"• {item}")

else:

    st.caption(
        "Todavía no hay confirmaciones recibidas."
    )
