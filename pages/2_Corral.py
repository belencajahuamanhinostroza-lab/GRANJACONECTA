
import streamlit as st
import streamlit.components.v1 as components
import paho.mqtt.client as mqtt
import json
import uuid
import queue
import os
import hashlib
import numpy as np
from PIL import Image

# =====================================================
# 1. CONFIGURACION
# =====================================================

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

# =====================================================
# 2. ESTILOS
# =====================================================

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

# =====================================================
# 3. ESTADO DE STREAMLIT
# =====================================================

if "telemetria" not in st.session_state:
    st.session_state.telemetria = {}

if "respuestas" not in st.session_state:
    st.session_state.respuestas = []

if "ultimo_gesto" not in st.session_state:
    st.session_state.ultimo_gesto = "Esperando gesto"

if "ultima_accion" not in st.session_state:
    st.session_state.ultima_accion = "Ninguna"

if "humedad_visual" not in st.session_state:
    st.session_state.humedad_visual = 50

if "ultima_imagen" not in st.session_state:
    st.session_state.ultima_imagen = None

if "mqtt_estado" not in st.session_state:
    st.session_state.mqtt_estado = False

# =====================================================
# 4. CONEXION MQTT
# =====================================================

@st.cache_resource
def crear_conexion_mqtt():

    mensajes = queue.Queue()

    cliente = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="GranjaConecta_Corral_" + uuid.uuid4().hex[:8]
    )

    def al_conectar(client, userdata, flags, reason_code, properties):

        if reason_code == 0:

            mensajes.put(("conexion", "conectado"))

            client.subscribe(TOPICO_TELEMETRIA)
            client.subscribe(TOPICO_RESPUESTAS)

        else:
            mensajes.put(("conexion", "error"))

    def al_recibir(client, userdata, msg):

        try:
            contenido = msg.payload.decode("utf-8")
            mensajes.put((msg.topic, contenido))

        except Exception as error:
            print("Error recibiendo MQTT:", error)

    cliente.on_connect = al_conectar
    cliente.on_message = al_recibir

    try:
        cliente.connect(BROKER, PUERTO, 60)
        cliente.loop_start()

        return cliente, mensajes, None

    except Exception as error:

        return None, mensajes, str(error)


cliente_mqtt, cola_mensajes, error_mqtt = crear_conexion_mqtt()

# =====================================================
# 5. FUNCION PARA ENVIAR COMANDOS
# =====================================================

def publicar_comando(comando):

    if cliente_mqtt is None:
        st.error("No hay conexión MQTT con el broker.")
        return False

    try:

        resultado = cliente_mqtt.publish(
            TOPICO_COMANDOS,
            comando,
            qos=0,
            retain=False
        )

        if resultado.rc == mqtt.MQTT_ERR_SUCCESS:
            return True

        st.error("No se pudo enviar el comando MQTT.")
        return False

    except Exception as error:

        st.error(f"Error enviando comando: {error}")
        return False


# =====================================================
# 6. ACTUALIZAR TELEMETRIA
# =====================================================

def procesar_mensajes():

    while True:

        try:

            topico, contenido = cola_mensajes.get_nowait()

            if topico == "conexion":

                st.session_state.mqtt_estado = (
                    contenido == "conectado"
                )

            elif topico == TOPICO_TELEMETRIA:

                datos = json.loads(contenido)

                st.session_state.telemetria.update(datos)

                if "humedadVisual" in datos:
                    st.session_state.humedad_visual = int(
                        datos["humedadVisual"]
                    )

            elif topico == TOPICO_RESPUESTAS:

                st.session_state.respuestas.append(contenido)

                st.session_state.respuestas = (
                    st.session_state.respuestas[-10:]
                )

        except queue.Empty:
            break

        except Exception as error:
            print("Error procesando telemetria:", error)
            break


# =====================================================
# 7. ACTUALIZACION AUTOMATICA CADA 2 SEGUNDOS
# =====================================================

@st.fragment(run_every="2s")
def mostrar_monitoreo():

    procesar_mensajes()

    datos = st.session_state.telemetria

    temperatura = datos.get("temperatura", "--")
    humedad = datos.get("humedad", "--")
    ventilacion = datos.get("ventilacion", "--")
    puerta = datos.get("puerta", "--")

    nivel_agua = datos.get("nivelAgua", "--")

    st.subheader("📊 Monitoreo del corral")

    if st.session_state.mqtt_estado:
        st.success("Conectado al broker MQTT")
    else:
        st.warning("Esperando conexión MQTT...")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        valor = (
            f"{temperatura} °C"
            if temperatura != "--"
            else "--"
        )
        st.metric("🌡️ Temperatura", valor)

    with c2:
        valor = (
            f"{humedad} %"
            if humedad != "--"
            else "--"
        )
        st.metric("💧 Humedad real", valor)

    with c3:
        valor = (
            f"{ventilacion} %"
            if ventilacion != "--"
            else "--"
        )
        st.metric("🌀 Ventilación", valor)

    with c4:
        st.metric("🚪 Puerta", str(puerta))

    st.metric(
        "💧 Humedad visual",
        f"{st.session_state.humedad_visual}%"
    )

    st.caption(
        "La humedad visual es una representación gráfica. "
        "No modifica la humedad real medida por el DHT22."
    )

    st.caption(
        f"Último nivel de agua recibido: {nivel_agua}%"
    )

    if st.session_state.respuestas:

        with st.expander("📩 Últimas respuestas del ESP32"):

            for respuesta in reversed(
                st.session_state.respuestas
            ):
                st.write("• " + respuesta)


# =====================================================
# 8. CARGAR MODELO KERAS
# =====================================================

@st.cache_resource
def cargar_modelo():

    from tensorflow.keras.models import load_model

    if not os.path.exists(RUTA_MODELO):
        raise FileNotFoundError(
            "No se encuentra keras_model.h5"
        )

    return load_model(RUTA_MODELO, compile=False)


@st.cache_data
def cargar_etiquetas():

    if not os.path.exists(RUTA_LABELS):
        raise FileNotFoundError(
            "No se encuentra labels.txt"
        )

    with open(
        RUTA_LABELS,
        "r",
        encoding="utf-8"
    ) as archivo:

        etiquetas = []

        for linea in archivo:

            linea = linea.strip()

            if linea:
                partes = linea.split(" ", 1)

                if len(partes) == 2:
                    etiquetas.append(partes[1])
                else:
                    etiquetas.append(partes[0])

    return etiquetas


# =====================================================
# 9. RECONOCIMIENTO DE GESTOS
# =====================================================

def reconocer_gesto(imagen, modelo):

    imagen = Image.open(imagen).convert("RGB")

    imagen = imagen.resize((224, 224))

    arreglo = np.asarray(
        imagen,
        dtype=np.float32
    )

    datos = np.ndarray(
        shape=(1, 224, 224, 3),
        dtype=np.float32
    )

    # Normalizacion utilizada en el modelo original
    datos[0] = (arreglo / 127.0) - 1.0

    prediccion = modelo.predict(
        datos,
        verbose=0
    )

    indice = int(np.argmax(prediccion[0]))

    confianza = float(
        prediccion[0][indice]
    ) * 100

    return indice, confianza


# =====================================================
# 10. ACCIONES DE LOS SEIS GESTOS
# =====================================================

ACCIONES = {

    0: {
        "nombre": "Abrir puerta",
        "comando": "PUERTA_ABRIR",
        "emoji": "✋"
    },

    1: {
        "nombre": "Cerrar puerta",
        "comando": "PUERTA_CERRAR",
        "emoji": "✊"
    },

    2: {
        "nombre": "Subir ventilación",
        "comando": "VENTILACION_SUBIR",
        "emoji": "👍"
    },

    3: {
        "nombre": "Bajar ventilación",
        "comando": "VENTILACION_BAJAR",
        "emoji": "👎"
    },

    4: {
        "nombre": "Subir humedad visual",
        "comando": "HUMEDAD_SUBIR",
        "emoji": "🫶"
    },

    5: {
        "nombre": "Bajar humedad visual",
        "comando": "HUMEDAD_BAJAR",
        "emoji": "🫶"
    }
}


def ejecutar_gesto(indice):

    if indice not in ACCIONES:
        st.error("Gesto no reconocido.")
        return

    accion = ACCIONES[indice]

    nombre = accion["nombre"]
    comando = accion["comando"]

    enviado = publicar_comando(comando)

    if enviado:

        st.session_state.ultimo_gesto = (
            accion["emoji"] + " " + nombre
        )

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


# =====================================================
# 11. BARRA LATERAL
# =====================================================

with st.sidebar:

    st.title("🐄 GranjaConecta")

    st.markdown("---")

    st.subheader("Panel del corral")

    st.write("📷 Reconocimiento de gestos")
    st.write("🚪 Control de puerta")
    st.write("🌀 Control de ventilación")
    st.write("💧 Humedad visual")
    st.write("🌡️ Monitoreo ambiental")

    st.markdown("---")

    st.caption("Sistema académico de simulación")


# =====================================================
# 12. ENCABEZADO
# =====================================================

st.title("🐄 GranjaConecta - Corral")

st.write(
    "Monitoreo y control del corral mediante "
    "reconocimiento de gestos y comunicación MQTT."
)

if cliente_mqtt is None:

    st.error(
        "No se pudo iniciar MQTT. "
        "Comprueba la conexión y la instalación de paho-mqtt."
    )

    if error_mqtt:
        st.caption(error_mqtt)

# =====================================================
# 13. ESCENARIO DEL GRANERO
# =====================================================

st.divider()

st.subheader("🏡 Interior del granero")

humedad_actual = st.session_state.humedad_visual

html_granero = f"""
<div style="
    width:100%;
    height:320px;
    background:linear-gradient(#b8d9e9 0%,#dcebd3 70%);
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
        height:90px;
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
        top:145px;
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
        bottom:12px;
        left:15px;
        color:white;
        font-weight:bold;
        font-size:16px;
        text-shadow:1px 1px 3px black;
    ">
        Humedad visual: {humedad_actual}%
    </div>

</div>
"""

components.html(
    html_granero,
    height=340
)

# =====================================================
# 14. CAMARA Y RECONOCIMIENTO
# =====================================================

st.divider()

st.subheader("📷 Reconocimiento de gestos")

col_camara, col_resultado = st.columns([1, 1])

with col_camara:

    st.markdown("#### Cámara")

    foto = st.camera_input(
        "Toma una fotografía de tu gesto",
        key="camara_corral"
    )

with col_resultado:

    st.markdown("#### Resultado del reconocimiento")

    st.info(
        "Último gesto: " +
        st.session_state.ultimo_gesto
    )

    st.info(
        "Acción: " +
        st.session_state.ultima_accion
    )

    if foto is not None:

        contenido = foto.getvalue()

        hash_imagen = hashlib.md5(
            contenido
        ).hexdigest()

        # Evitar enviar varias veces el mismo gesto
        if hash_imagen != st.session_state.ultima_imagen:

            st.session_state.ultima_imagen = hash_imagen

            try:

                modelo = cargar_modelo()
                etiquetas = cargar_etiquetas()

                indice, confianza = reconocer_gesto(
                    foto,
                    modelo
                )

                if indice >= len(etiquetas):

                    st.error(
                        "El índice reconocido no coincide "
                        "con las etiquetas del modelo."
                    )

                elif confianza >= 70:

                    st.success(
                        f"Confianza: {confianza:.1f}%"
                    )

                    st.write(
                        "Etiqueta del modelo: "
                        + etiquetas[indice]
                    )

                    if indice in ACCIONES:

                        ejecutar_gesto(indice)

                        st.rerun()

                    else:

                        st.warning(
                            "La clase reconocida no tiene "
                            "una acción configurada."
                        )

                else:

                    st.warning(
                        f"Confianza baja: {confianza:.1f}%. "
                        "Intenta otra fotografía."
                    )

            except Exception as error:

                st.error(
                    f"Error con el modelo: {error}"
                )

# =====================================================
# 15. MONITOREO AUTOMATICO
# =====================================================

st.divider()

mostrar_monitoreo()

# =====================================================
# 16. CONTROLES MANUALES
# =====================================================

st.divider()

st.subheader("🎮 Controles manuales del corral")

col_puerta, col_ventilacion, col_humedad = st.columns(3)

with col_puerta:

    st.markdown("#### 🚪 Puerta")

    if st.button(
        "Abrir puerta",
        use_container_width=True
    ):

        if publicar_comando("PUERTA_ABRIR"):
            st.success("Comando enviado")

    if st.button(
        "Cerrar puerta",
        use_container_width=True
    ):

        if publicar_comando("PUERTA_CERRAR"):
            st.success("Comando enviado")


with col_ventilacion:

    st.markdown("#### 🌀 Ventilación")

    if st.button(
        "Subir ventilación",
        use_container_width=True
    ):

        if publicar_comando("VENTILACION_SUBIR"):
            st.success("Comando enviado")

    if st.button(
        "Bajar ventilación",
        use_container_width=True
    ):

        if publicar_comando("VENTILACION_BAJAR"):
            st.success("Comando enviado")


with col_humedad:

    st.markdown("#### 💧 Humedad visual")

    if st.button(
        "Subir humedad visual",
        use_container_width=True
    ):

        if publicar_comando("HUMEDAD_SUBIR"):
            st.success("Comando enviado")

    if st.button(
        "Bajar humedad visual",
        use_container_width=True
    ):

        if publicar_comando("HUMEDAD_BAJAR"):
            st.success("Comando enviado")


# =====================================================
# 17. PIE DE PAGINA
# =====================================================

st.divider()

st.caption(
    "GranjaConecta | ESP32 + Wokwi + MQTT | "
    "Prototipo académico de monitoreo y control ganadero."
)
