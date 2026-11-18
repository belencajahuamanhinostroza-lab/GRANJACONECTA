
import streamlit as st
import streamlit.components.v1 as components
import json
import os
import uuid
import queue
import threading
import time
import numpy as np
from PIL import Image

# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================

st.set_page_config(
    page_title="GranjaConecta - Corral",
    page_icon="🐄",
    layout="wide"
)

BROKER = "broker.mqttdashboard.com"
PUERTO = 1883

TOPICO_COMANDOS = "granjaconecta/comandos"
TOPICO_TELEMETRIA = "granjaconecta/telemetria"
TOPICO_RESPUESTAS = "granjaconecta/respuestas"

RUTA_MODELO = "keras_model.h5"
RUTA_LABELS = "labels.txt"

# =========================================================
# IMPORTACIONES OPCIONALES
# =========================================================

try:
    import paho.mqtt.client as mqtt
    MQTT_DISPONIBLE = True
except ImportError:
    mqtt = None
    MQTT_DISPONIBLE = False

try:
    from tensorflow.keras.models import load_model
    TENSORFLOW_DISPONIBLE = True
except Exception:
    load_model = None
    TENSORFLOW_DISPONIBLE = False


# =========================================================
# ESTILOS
# =========================================================

st.markdown("""
<style>
.stApp {
    background-color: #e5f2d8;
}

section[data-testid="stSidebar"] {
    background-color: #245c36;
}

section[data-testid="stSidebar"] * {
    color: white !important;
}

h1, h2, h3 {
    color: #245c36;
}

div[data-testid="stMetric"] {
    background-color: #f7fff1;
    border: 1px solid #b8d5a5;
    padding: 12px;
    border-radius: 12px;
}

.stButton button {
    border-radius: 10px;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# ESTADO DE LA APLICACIÓN
# =========================================================

if "humedad_visual" not in st.session_state:
    st.session_state.humedad_visual = 50

if "telemetria" not in st.session_state:
    st.session_state.telemetria = {}

if "respuestas" not in st.session_state:
    st.session_state.respuestas = []

if "ultimo_gesto" not in st.session_state:
    st.session_state.ultimo_gesto = "Esperando gesto"

if "ultima_accion" not in st.session_state:
    st.session_state.ultima_accion = "Ninguna"


# =========================================================
# CONEXIÓN MQTT
# =========================================================

@st.cache_resource
def crear_conexion_mqtt():

    if not MQTT_DISPONIBLE:
        return None, None

    mensajes = queue.Queue()

    try:
        cliente = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="GranjaConecta_Corral_" + uuid.uuid4().hex[:8]
        )

        def al_conectar(client, userdata, flags, reason_code, properties):
            if reason_code == 0:
                client.subscribe(TOPICO_TELEMETRIA)
                client.subscribe(TOPICO_RESPUESTAS)

        def al_recibir(client, userdata, msg):
            try:
                contenido = msg.payload.decode("utf-8")
                mensajes.put((msg.topic, contenido))
            except Exception:
                pass

        cliente.on_connect = al_conectar
        cliente.on_message = al_recibir

        cliente.connect(BROKER, PUERTO, 60)
        cliente.loop_start()

        return cliente, mensajes

    except Exception as error:
        print("Error de conexión MQTT:", error)
        return None, None


cliente_mqtt = None
cola_mensajes = None

if MQTT_DISPONIBLE:
    cliente_mqtt, cola_mensajes = crear_conexion_mqtt()


def publicar_comando(comando):

    if cliente_mqtt is None:
        st.error(
            "No hay conexión MQTT. Revisa la instalación de paho-mqtt "
            "y la conexión con el broker."
        )
        return

    try:
        mensaje = json.dumps({"comando": comando})
        resultado = cliente_mqtt.publish(
            TOPICO_COMANDOS,
            mensaje
        )

        if resultado.rc == 0:
            st.success("Comando enviado: " + comando)
        else:
            st.error("No se pudo enviar el comando MQTT.")

    except Exception as error:
        st.error(f"Error enviando comando: {error}")


# =========================================================
# RECEPCIÓN DE TELEMETRÍA
# =========================================================

if cola_mensajes is not None:

    while True:
        try:
            topico, contenido = cola_mensajes.get_nowait()

            datos = json.loads(contenido)

            if topico == TOPICO_TELEMETRIA:
                st.session_state.telemetria.update(datos)

            elif topico == TOPICO_RESPUESTAS:
                st.session_state.respuestas.append(contenido)

        except queue.Empty:
            break

        except Exception:
            break


# =========================================================
# CARGAR MODELO DE TEACHABLE MACHINE
# =========================================================

@st.cache_resource
def cargar_modelo():

    if not TENSORFLOW_DISPONIBLE:
        return None

    if not os.path.exists(RUTA_MODELO):
        return None

    try:
        return load_model(RUTA_MODELO, compile=False)
    except Exception as error:
        print("Error cargando modelo:", error)
        return None


modelo = cargar_modelo()


def cargar_etiquetas():

    if not os.path.exists(RUTA_LABELS):
        return []

    with open(RUTA_LABELS, "r", encoding="utf-8") as archivo:
        return [
            linea.strip().split(" ", 1)[-1]
            for linea in archivo.readlines()
            if linea.strip()
        ]


etiquetas = cargar_etiquetas()


# =========================================================
# RECONOCIMIENTO DE GESTOS
# =========================================================

def reconocer_gesto(imagen):

    if modelo is None:
        return None, None

    try:
        imagen = Image.open(imagen).convert("RGB")
        imagen = imagen.resize((224, 224))

        arreglo = np.asarray(imagen, dtype=np.float32)

        datos = np.ndarray(
            shape=(1, 224, 224, 3),
            dtype=np.float32
        )

        datos[0] = (arreglo / 127.0) - 1.0

        prediccion = modelo.predict(datos, verbose=0)

        indice = int(np.argmax(prediccion[0]))
        confianza = float(prediccion[0][indice]) * 100

        if indice < len(etiquetas):
            etiqueta = etiquetas[indice]
        else:
            etiqueta = f"Clase {indice}"

        return indice, confianza

    except Exception as error:
        st.error(f"Error al reconocer el gesto: {error}")
        return None, None


def ejecutar_gesto(indice):

    acciones = {
        0: ("Abrir puerta", "PUERTA_ABRIR"),
        1: ("Cerrar puerta", "PUERTA_CERRAR"),
        2: ("Subir ventilación", "VENTILACION_SUBIR"),
        3: ("Bajar ventilación", "VENTILACION_BAJAR"),
        4: ("Subir humedad visual", "HUMEDAD_SUBIR"),
        5: ("Bajar humedad visual", "HUMEDAD_BAJAR")
    }

    if indice not in acciones:
        return

    nombre, comando = acciones[indice]

    st.session_state.ultimo_gesto = nombre
    st.session_state.ultima_accion = nombre

    if indice == 4:
        st.session_state.humedad_visual = min(
            100,
            st.session_state.humedad_visual + 25
        )

    elif indice == 5:
        st.session_state.humedad_visual = max(
            0,
            st.session_state.humedad_visual - 25
        )

    publicar_comando(comando)


# =========================================================
# ENCABEZADO
# =========================================================

st.title("🐄 GranjaConecta - Control del Corral")

st.write(
    "Monitoreo y control del corral mediante reconocimiento "
    "de gestos y comunicación MQTT con ESP32."
)

if not MQTT_DISPONIBLE:
    st.warning(
        "La librería paho-mqtt no está instalada. "
        "La página se mostrará, pero MQTT no estará disponible."
    )
elif cliente_mqtt is None:
    st.warning("No se pudo establecer la conexión con el broker MQTT.")

st.divider()


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:
    st.title("🐄 GranjaConecta")
    st.markdown("---")
    st.subheader("Panel del corral")
    st.write("Control por gestos")
    st.write("Monitoreo ambiental")
    st.write("Control de puerta")
    st.write("Control de ventilación")
    st.markdown("---")
    st.caption("Sistema académico de simulación")


# =========================================================
# ESCENARIO DEL GRANERO
# =========================================================

st.subheader("🏡 Interior del granero")

humedad = st.session_state.humedad_visual

html_granero = f"""
<div style="
    width:100%;
    height:330px;
    background:linear-gradient(#b8d9e9 0%,#dcebd3 65%);
    border:8px solid #754523;
    border-radius:15px;
    position:relative;
    overflow:hidden;
    font-family:Arial;
">

    <div style="
        position:absolute;
        top:0;
        width:100%;
        height:45px;
        background:#754523;
    "></div>

    <div style="
        position:absolute;
        top:45px;
        left:0;
        width:100%;
        height:12px;
        background:#9c6536;
    "></div>

    <div style="
        position:absolute;
        top:65px;
        left:20px;
        width:115px;
        height:85px;
        background:#9ed7ed;
        border:9px solid #754523;
    ">
        <div style="
            position:absolute;
            left:50%;
            height:100%;
            width:5px;
            background:#754523;
        "></div>
        <div style="
            position:absolute;
            top:50%;
            height:5px;
            width:100%;
            background:#754523;
        "></div>
    </div>

    <div style="
        position:absolute;
        bottom:0;
        width:100%;
        height:95px;
        background:#8d633e;
        border-top:12px solid #4f8c38;
    "></div>

    <div style="
        position:absolute;
        bottom:65px;
        left:40%;
        font-size:90px;
    ">🐄</div>

    <div style="
        position:absolute;
        bottom:90px;
        right:8%;
        width:75px;
        height:130px;
        background:#9b6338;
        border:6px solid #603b21;
        border-radius:5px;
        display:flex;
        align-items:center;
        justify-content:center;
        color:white;
        font-size:28px;
    ">🚪</div>

    <div style="
        position:absolute;
        top:75px;
        right:35%;
        font-size:45px;
    ">🌀</div>

    <div style="
        position:absolute;
        top:135px;
        left:5%;
        font-size:24px;
    ">🌫️</div>

    <div style="
        position:absolute;
        top:170px;
        right:15%;
        font-size:24px;
    ">🌫️</div>

    <div style="
        position:absolute;
        bottom:15px;
        left:15px;
        color:white;
        font-weight:bold;
        font-size:17px;
        text-shadow:1px 1px 3px black;
    ">
        Humedad visual: {humedad}%
    </div>

</div>
"""

components.html(html_granero, height=350)


# =========================================================
# CÁMARA Y RESULTADO
# =========================================================

st.divider()
st.subheader("📷 Reconocimiento de gestos")

col_camara, col_resultado = st.columns([1, 1])

with col_camara:

    st.markdown("#### Cámara")

    foto = st.camera_input(
        "Captura un gesto con tu mano",
        key="camara_corral"
    )

with col_resultado:

    st.markdown("#### Gesto reconocido")

    st.info(
        f"**Gesto:** {st.session_state.ultimo_gesto}"
    )

    st.info(
        f"**Acción:** {st.session_state.ultima_accion}"
    )

    if foto is not None:

        if modelo is None:
            st.error(
                "No se pudo cargar el modelo. "
                "Verifica keras_model.h5 y TensorFlow."
            )

        else:

            indice, confianza = reconocer_gesto(foto)

            if indice is not None:

                if confianza >= 70:

                    st.success(
                        f"Confianza del reconocimiento: {confianza:.1f}%"
                    )

                    ejecutar_gesto(indice)

                    st.rerun()

                else:

                    st.warning(
                        f"Confianza baja: {confianza:.1f}%. "
                        "Intenta tomar otra fotografía."
                    )


# =========================================================
# INDICADORES DE TELEMETRÍA
# =========================================================

st.divider()
st.subheader("📊 Monitoreo del corral")

datos = st.session_state.telemetria

temperatura = datos.get("temperatura", "--")
humedad_real = datos.get("humedad", "--")
ventilacion = datos.get("ventilacion", "--")
puerta = datos.get("puerta", "--")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        "🌡️ Temperatura",
        f"{temperatura} °C" if temperatura != "--" else "--"
    )

with c2:
    st.metric(
        "💧 Humedad real",
        f"{humedad_real} %" if humedad_real != "--" else "--"
    )

with c3:
    st.metric(
        "🌀 Ventilación",
        f"{ventilacion} %" if ventilacion != "--" else "--"
    )

with c4:
    st.metric(
        "🚪 Puerta",
        str(puerta)
    )

st.caption(
    "La humedad visual modificada por gestos es una representación "
    "gráfica y no modifica la humedad física medida por el sensor."
)


# =========================================================
# CONTROLES MANUALES
# =========================================================

st.divider()
st.subheader("🎮 Controles manuales")

col_puerta, col_ventilacion, col_humedad = st.columns(3)

with col_puerta:

    st.markdown("#### 🚪 Puerta")

    if st.button("Abrir puerta", use_container_width=True):
        publicar_comando("PUERTA_ABRIR")

    if st.button("Cerrar puerta", use_container_width=True):
        publicar_comando("PUERTA_CERRAR")


with col_ventilacion:

    st.markdown("#### 🌀 Ventilación")

    if st.button("Subir ventilación", use_container_width=True):
        publicar_comando("VENTILACION_SUBIR")

    if st.button("Bajar ventilación", use_container_width=True):
        publicar_comando("VENTILACION_BAJAR")


with col_humedad:

    st.markdown("#### 💧 Humedad visual")

    if st.button("Subir humedad visual", use_container_width=True):
        st.session_state.humedad_visual = min(
            100,
            st.session_state.humedad_visual + 25
        )
        publicar_comando("HUMEDAD_SUBIR")
        st.rerun()

    if st.button("Bajar humedad visual", use_container_width=True):
        st.session_state.humedad_visual = max(
            0,
            st.session_state.humedad_visual - 25
        )
        publicar_comando("HUMEDAD_BAJAR")
        st.rerun()


# =========================================================
# ACTUALIZACIÓN DE DATOS
# =========================================================

st.divider()

if st.button("🔄 Actualizar telemetría", use_container_width=True):
    st.rerun()

st.caption(
    "GranjaConecta | Prototipo académico con ESP32, Wokwi y MQTT"
)
