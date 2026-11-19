
import streamlit as st
import streamlit.components.v1 as components
import streamlit.autorefresh
import paho.mqtt.client as mqtt
import json
import queue
import re
import unicodedata
import io
import time

from threading import Lock

try:
    from streamlit_mic_recorder import mic_recorder
    import speech_recognition as sr
    MICROFONO_DISPONIBLE = True
except ImportError:
    MICROFONO_DISPONIBLE = False


# =========================================================
# 1. CONFIGURACIÓN
# =========================================================

st.set_page_config(
    page_title="GranjaConecta | Bebedero",
    page_icon="🐔",
    layout="wide"
)

BROKER = "broker.mqttdashboard.com"
PUERTO = 1883
TOPIC = "granjaconecta"

# =========================================================
# 2. ESTILOS
# =========================================================

st.markdown("""
<style>
.stApp {
    background-color: #EDF5E9;
    color: #17472D;
}

[data-testid="stSidebar"] {
    background-color: #DCEBD8;
}

h1, h2, h3, h4, p, label {
    color: #17472D !important;
}

.titulo {
    color: #17472D;
    font-size: 34px;
    font-weight: 800;
}

.subtitulo {
    color: #52735A;
    font-size: 15px;
    margin-bottom: 18px;
}

.tarjeta {
    background: white;
    border: 1px solid #C9DDC5;
    border-radius: 15px;
    padding: 17px;
    margin-bottom: 10px;
}

div.stButton > button {
    background: #17472D;
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: bold;
    min-height: 43px;
    width: 100%;
}

div.stButton > button:hover {
    background: #286341;
    color: white;
}

div[data-testid="stMetric"] {
    background: white;
    padding: 15px;
    border-radius: 12px;
    border: 1px solid #C9DDC5;
}

div[data-testid="stMetric"] label {
    color: #52735A !important;
}

div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #17472D !important;
}

hr {
    border-color: #C9DDC5;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# 3. ESTADO INICIAL
# =========================================================

if "telemetria" not in st.session_state:
    st.session_state.telemetria = {
        "temperatura": 0,
        "humedad": 0,
        "lecturaDHTValida": False,
        "agua": 0,
        "nivelAgua": 0,
        "distancia": 0,
        "distanciaHC": 0,
        "lecturaHCValida": False,
        "lecturaAguaValida": False,
        "estadoAgua": "ESPERANDO DATOS",
        "puerta": "cerrada",
        "valvula": "cerrada",
        "vaciando": False,
        "ventilacion": 0,
        "ajusteTermico": 0,
        "humedadVisual": 0
    }

if "conexion_mqtt" not in st.session_state:
    st.session_state.conexion_mqtt = False

if "respuesta" not in st.session_state:
    st.session_state.respuesta = (
        "Esperando conexión con el ESP32."
    )

if "historial" not in st.session_state:
    st.session_state.historial = []

if "alertas" not in st.session_state:
    st.session_state.alertas = []

if "ultimo_audio" not in st.session_state:
    st.session_state.ultimo_audio = None

if "ultimo_mensaje_esp" not in st.session_state:
    st.session_state.ultimo_mensaje_esp = ""

if "ultimo_comando" not in st.session_state:
    st.session_state.ultimo_comando = ""


# =========================================================
# 4. COLA DE MENSAJES MQTT
# =========================================================

# El hilo MQTT guarda los mensajes en una cola.
# Streamlit los procesa desde el hilo principal.

mensajes_mqtt = queue.Queue()
mqtt_lock = Lock()


# =========================================================
# 5. CONEXIÓN MQTT
# =========================================================

@st.cache_resource
def crear_cliente_mqtt():

    cliente = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="STREAMLIT_BEBEDERO"
    )

    def al_conectar(client, userdata, flags, reason_code, properties):

        if reason_code == 0:
            client.subscribe(TOPIC)
            mensajes_mqtt.put({
                "tipo_interno": "conexion",
                "estado": True
            })
        else:
            mensajes_mqtt.put({
                "tipo_interno": "conexion",
                "estado": False
            })

    def al_desconectar(client, userdata, disconnect_flags,
                       reason_code, properties):

        mensajes_mqtt.put({
            "tipo_interno": "conexion",
            "estado": False
        })

    def al_recibir(client, userdata, msg):

        try:
            contenido = json.loads(
                msg.payload.decode("utf-8")
            )

            mensajes_mqtt.put(contenido)

        except Exception as error:
            print("Error leyendo MQTT:", error)

    cliente.on_connect = al_conectar
    cliente.on_disconnect = al_desconectar
    cliente.on_message = al_recibir

    try:
        cliente.connect(
            BROKER,
            PUERTO,
            keepalive=60
        )

        cliente.loop_start()

    except Exception as error:
        print("Error de conexión MQTT:", error)

    return cliente


cliente = crear_cliente_mqtt()


# =========================================================
# 6. RECIBIR MENSAJES DEL ESP32
# =========================================================

def procesar_mensajes_recibidos():

    while True:

        try:
            mensaje = mensajes_mqtt.get_nowait()

        except queue.Empty:
            break

        tipo = mensaje.get("tipo")

        if mensaje.get("tipo_interno") == "conexion":

            st.session_state.conexion_mqtt = mensaje["estado"]

            if mensaje["estado"]:
                st.session_state.respuesta = (
                    "Conexión MQTT establecida. "
                    "Esperando telemetría del ESP32."
                )
            else:
                st.session_state.respuesta = (
                    "Se perdió la conexión MQTT."
                )

            continue

        if tipo == "telemetria":

            datos = mensaje.get("datos", {})

            st.session_state.telemetria.update(datos)

            st.session_state.conexion_mqtt = True

        elif tipo == "respuesta":

            texto = mensaje.get(
                "message",
                "El ESP32 recibió una orden."
            )

            st.session_state.ultimo_mensaje_esp = texto
            st.session_state.respuesta = texto


procesar_mensajes_recibidos()


# =========================================================
# 7. ENVIAR COMANDOS MQTT
# =========================================================

def enviar_comando(comando):

    if not cliente.is_connected():

        st.session_state.respuesta = (
            "No hay conexión con MQTT. "
            "Verifica que Wokwi esté ejecutándose."
        )

        return False

    mensaje = {
        "tipo": "comando",
        "command": comando
    }

    try:

        resultado = cliente.publish(
            TOPIC,
            json.dumps(mensaje),
            qos=0
        )

        if resultado.rc != mqtt.MQTT_ERR_SUCCESS:

            st.session_state.respuesta = (
                "No se pudo enviar la orden MQTT."
            )

            return False

        st.session_state.ultimo_comando = comando

        st.session_state.respuesta = (
            f"Orden enviada al ESP32: {comando}. "
            "Esperando confirmación."
        )

        return True

    except Exception as error:

        st.session_state.respuesta = (
            f"Error enviando la orden: {error}"
        )

        return False


# =========================================================
# 8. INTERPRETAR VOZ Y TEXTO
# =========================================================

def normalizar(texto):

    texto = texto.lower().strip()

    texto = unicodedata.normalize(
        "NFD",
        texto
    )

    texto = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )

    return texto


def procesar_orden(texto):

    mensaje = normalizar(texto)

    if not mensaje:
        return

    comando = None

    # PUERTA
    if any(x in mensaje for x in [
        "abrir puerta",
        "abre la puerta",
        "abre puerta"
    ]):
        comando = "PUERTA_ABRIR"

    elif any(x in mensaje for x in [
        "cerrar puerta",
        "cierra la puerta",
        "cierra puerta"
    ]):
        comando = "PUERTA_CERRAR"

    # VÁLVULA
    elif any(x in mensaje for x in [
        "abrir valvula",
        "abre la valvula",
        "abre valvula",
        "iniciar llenado"
    ]):
        comando = "VALVULA_ABRIR"

    elif any(x in mensaje for x in [
        "cerrar valvula",
        "cierra la valvula",
        "detener llenado",
        "detener el agua"
    ]):
        comando = "VALVULA_CERRAR"

    # BEBEDERO
    elif any(x in mensaje for x in [
        "vaciar",
        "vacia el bebedero",
        "vaciar el bebedero",
        "drenar el bebedero"
    ]):
        comando = "BEBEDERO_VACIAR"

    elif any(x in mensaje for x in [
        "llenar completamente",
        "llena completamente",
        "llenar el bebedero",
        "llena el bebedero",
        "llenar bebedero",
        "llena bebedero"
    ]):
        comando = "BEBEDERO_LLENO"

    # VENTILACIÓN
    elif any(x in mensaje for x in [
        "aumentar ventilacion",
        "subir ventilacion",
        "mas ventilacion"
    ]):
        comando = "VENTILACION_SUBIR"

    elif any(x in mensaje for x in [
        "disminuir ventilacion",
        "bajar ventilacion",
        "menos ventilacion"
    ]):
        comando = "VENTILACION_BAJAR"

    # TEMPERATURA
    elif any(x in mensaje for x in [
        "subir temperatura",
        "aumentar temperatura",
        "mas temperatura"
    ]):
        comando = "AJUSTE_TERMICO_SUBIR"

    elif any(x in mensaje for x in [
        "bajar temperatura",
        "disminuir temperatura",
        "menos temperatura"
    ]):
        comando = "AJUSTE_TERMICO_BAJAR"

    # HUMEDAD
    elif any(x in mensaje for x in [
        "subir humedad",
        "aumentar humedad"
    ]):
        comando = "HUMEDAD_SUBIR"

    elif any(x in mensaje for x in [
        "bajar humedad",
        "disminuir humedad"
    ]):
        comando = "HUMEDAD_BAJAR"

    # CONSULTAS LOCALES
    elif any(x in mensaje for x in [
        "cuantos centimetros",
        "distancia del agua",
        "distancia hay"
    ]):

        datos = st.session_state.telemetria

        if datos.get("lecturaAguaValida"):

            st.session_state.respuesta = (
                f"La distancia hasta el agua es de "
                f"{datos.get('distancia', 0):.1f} centímetros."
            )

        else:

            st.session_state.respuesta = (
                "Todavía no recibo una lectura válida del bebedero."
            )

        return

    elif any(x in mensaje for x in [
        "estado del bebedero",
        "nivel de agua",
        "como esta el bebedero",
        "como esta el agua"
    ]):

        datos = st.session_state.telemetria

        if datos.get("lecturaAguaValida"):

            st.session_state.respuesta = (
                f"El estado del bebedero es "
                f"{datos.get('estadoAgua', 'sin datos')}. "
                f"El nivel es {datos.get('nivelAgua', 0):.1f} "
                f"por ciento y la distancia es "
                f"{datos.get('distancia', 0):.1f} centímetros."
            )

        else:

            st.session_state.respuesta = (
                "No tengo una lectura válida del bebedero."
            )

        return

    elif any(x in mensaje for x in [
        "estado de la valvula",
        "esta abierta la valvula",
        "esta cerrada la valvula"
    ]):

        valvula = st.session_state.telemetria.get(
            "valvula",
            "desconocida"
        )

        st.session_state.respuesta = (
            f"La válvula está {valvula}."
        )

        return

    elif any(x in mensaje for x in [
        "temperatura actual",
        "cuanta temperatura",
        "temperatura del corral"
    ]):

        datos = st.session_state.telemetria

        if datos.get("lecturaDHTValida"):

            st.session_state.respuesta = (
                f"La temperatura actual es de "
                f"{datos.get('temperatura', 0):.1f} grados Celsius."
            )

        else:

            st.session_state.respuesta = (
                "No hay una lectura válida de temperatura."
            )

        return

    elif any(x in mensaje for x in [
        "humedad actual",
        "cuanta humedad",
        "humedad del corral"
    ]):

        datos = st.session_state.telemetria

        if datos.get("lecturaDHTValida"):

            st.session_state.respuesta = (
                f"La humedad actual es de "
                f"{datos.get('humedad', 0):.1f} por ciento."
            )

        else:

            st.session_state.respuesta = (
                "No hay una lectura válida de humedad."
            )

        return

    if comando:

        enviado = enviar_comando(comando)

        if enviado:

            st.session_state.historial.append({
                "usuario": texto,
                "asistente": (
                    f"Orden enviada: {comando}. "
                    "Estoy esperando la respuesta del dispositivo."
                )
            })

    else:

        st.session_state.respuesta = (
            "No reconocí esa orden. Puedes pedirme abrir o cerrar "
            "la válvula, llenar o vaciar el bebedero, o consultar "
            "el estado del agua."
        )


# =========================================================
# 9. ACTUALIZACIÓN AUTOMÁTICA
# =========================================================

st.autorefresh.st_autorefresh(
    interval=2000,
    key="actualizacion_bebedero"
)

# Procesar los mensajes recibidos durante el refresco
procesar_mensajes_recibidos()


# =========================================================
# 10. ENCABEZADO
# =========================================================

st.markdown(
    '<div class="titulo">🐔 GranjaConecta</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitulo">'
    'Control inteligente del bebedero mediante voz, texto y MQTT'
    '</div>',
    unsafe_allow_html=True
)

if cliente.is_connected():

    st.success("🟢 Conectado al servidor MQTT")

else:

    st.error("🔴 Sin conexión MQTT. Comprueba Wokwi y el broker.")


# =========================================================
# 11. DATOS RECIBIDOS
# =========================================================

datos = st.session_state.telemetria

lectura_valida = datos.get(
    "lecturaAguaValida",
    False
)

distancia = float(datos.get("distancia", 0) or 0)
nivel = float(datos.get("nivelAgua", 0) or 0)

estado_agua = datos.get(
    "estadoAgua",
    "ESPERANDO DATOS"
)

valvula = datos.get(
    "valvula",
    "desconocida"
)

vaciando = datos.get("vaciando", False)


# =========================================================
# 12. VISUALIZACIÓN
# =========================================================

columna_dibujo, columna_datos = st.columns(
    [1.1, 1],
    gap="large"
)

with columna_dibujo:

    st.markdown("### 🐔 Bebedero")

    if lectura_valida:

        altura = max(
            0,
            min(100, (nivel / 90) * 100)
        )

        etiqueta = f"{distancia:.1f} cm"

    else:

        altura = 0
        etiqueta = "Sin lectura"

    dibujo = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">

    <style>
    * {{
        box-sizing: border-box;
    }}

    body {{
        margin: 0;
        background: transparent;
        font-family: Arial, sans-serif;
    }}

    .zona {{
        height: 330px;
        display: flex;
        align-items: center;
        justify-content: center;
    }}

    .bebedero {{
        width: 210px;
        height: 270px;
        position: relative;
        overflow: hidden;
        border: 5px solid #17472D;
        border-radius: 18px 18px 35px 35px;
        background: #F8FFF6;
    }}

    .agua {{
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        height: {altura:.1f}%;
        background: linear-gradient(
            to top,
            #168477,
            #43BFA8,
            #8AE0C9
        );
        transition: height 0.8s ease;
    }}

    .etiqueta {{
        position: absolute;
        top: 20px;
        width: 100%;
        text-align: center;
        color: #17472D;
        font-size: 15px;
        font-weight: bold;
        z-index: 3;
    }}

    .nivel {{
        position: absolute;
        bottom: 15px;
        width: 100%;
        text-align: center;
        color: white;
        font-size: 15px;
        font-weight: bold;
        text-shadow: 0 1px 3px #17472D;
        z-index: 3;
    }}

    .borde {{
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 10px;
        background: #17472D;
        z-index: 4;
    }}
    </style>
    </head>

    <body>
        <div class="zona">
            <div class="bebedero">
                <div class="borde"></div>
                <div class="etiqueta">AGUA</div>
                <div class="agua"></div>
                <div class="nivel">{etiqueta}</div>
            </div>
        </div>
    </body>
    </html>
    """

    components.html(
        dibujo,
        height=335,
        scrolling=False
    )

    if lectura_valida:
        st.caption(
            "Visualización actualizada con la telemetría del ESP32."
        )
    else:
        st.warning(
            "Esperando la primera lectura de agua del ESP32."
        )


with columna_datos:

    st.markdown("### 📊 Monitoreo")

    if lectura_valida:

        st.metric(
            "Distancia hasta el agua",
            f"{distancia:.1f} cm"
        )

        st.metric(
            "Nivel de agua",
            f"{nivel:.1f} %"
        )

        st.metric(
            "Estado del agua",
            estado_agua
        )

        st.metric(
            "Estado de la válvula",
            valvula.upper()
        )

        if vaciando:
            st.info("💧 El bebedero se está vaciando.")
        elif valvula == "abierta":
            st.info("💧 El bebedero se está llenando.")
        else:
            st.success("🔒 Válvula cerrada.")

    else:

        st.info(
            "Los indicadores aparecerán cuando llegue "
            "la telemetría del ESP32."
        )


st.divider()


# =========================================================
# 13. ALERTAS
# =========================================================

st.markdown("### 🚨 Alertas del bebedero")

alertas_actuales = []

if not cliente.is_connected():

    alertas_actuales.append(
        ("error", "Sin conexión MQTT con el dispositivo.")
    )

if not lectura_valida:

    alertas_actuales.append(
        ("warning", "No se ha recibido una lectura válida del agua.")
    )

else:

    if distancia >= 30:

        alertas_actuales.append(
            ("error", "Bebedero vacío. Se recomienda llenarlo.")
        )

    elif distancia > 25:

        alertas_actuales.append(
            ("warning", "Nivel de agua bajo.")
        )

    elif distancia <= 10:

        alertas_actuales.append(
            ("success", "Bebedero lleno. Comprueba que la válvula esté cerrada.")
        )

    elif distancia < 10:

        alertas_actuales.append(
            ("error", "Lectura por debajo del límite de llenado.")
        )

    if valvula == "abierta" and nivel >= 90:

        alertas_actuales.append(
            ("warning", "La válvula sigue abierta con el nivel máximo.")
        )

if not datos.get("lecturaDHTValida", False):

    alertas_actuales.append(
        ("warning", "No hay lectura válida del sensor DHT22.")
    )

if datos.get("lecturaHCValida", False):

    distancia_fisica = float(
        datos.get("distanciaHC", 0) or 0
    )

    if distancia_fisica < 2 or distancia_fisica > 400:

        alertas_actuales.append(
            ("warning", "El sensor HC-SR04 presenta una lectura fuera de rango.")
        )

for tipo, mensaje in alertas_actuales:

    if tipo == "error":
        st.error("🔴 " + mensaje)

    elif tipo == "warning":
        st.warning("🟠 " + mensaje)

    else:
        st.success("🟢 " + mensaje)

if not alertas_actuales:

    st.success("🟢 No hay alertas activas.")


st.divider()


# =========================================================
# 14. CONTROL MANUAL
# =========================================================

st.markdown("### 🎛️ Control del bebedero")

b1, b2, b3, b4 = st.columns(4)

with b1:

    if st.button("💧 Abrir válvula"):

        enviar_comando("VALVULA_ABRIR")
        st.rerun()

with b2:

    if st.button("🔒 Cerrar válvula"):

        enviar_comando("VALVULA_CERRAR")
        st.rerun()

with b3:

    if st.button("⬆️ Llenar"):

        enviar_comando("BEBEDERO_LLENO")
        st.rerun()

with b4:

    if st.button("⬇️ Vaciar"):

        enviar_comando("BEBEDERO_VACIAR")
        st.rerun()


# =========================================================
# 15. CONTROL POR ESCRITURA
# =========================================================

st.divider()

st.markdown("### 💬 Habla con GranjaConecta")

with st.form("formulario_orden", clear_on_submit=True):

    texto = st.text_input(
        "Escribe tu orden",
        placeholder="Ejemplo: llena el bebedero"
    )

    enviar = st.form_submit_button(
        "Enviar orden",
        use_container_width=True
    )

if enviar and texto.strip():

    procesar_orden(texto)
    st.rerun()


# =========================================================
# 16. CONTROL POR VOZ
# =========================================================

if MICROFONO_DISPONIBLE:

    st.markdown("#### 🎙️ Control por voz")

    audio = mic_recorder(
        start_prompt="🎙️ Hablar",
        stop_prompt="⏹️ Detener",
        just_once=True,
        key="microfono_granjaconecta"
    )

    if audio and audio.get("bytes"):

        try:

            import hashlib

            huella = hashlib.md5(
                audio["bytes"]
            ).hexdigest()

            if st.session_state.ultimo_audio != huella:

                st.session_state.ultimo_audio = huella

                reconocedor = sr.Recognizer()

                with sr.AudioFile(
                    io.BytesIO(audio["bytes"])
                ) as fuente:

                    audio_grabado = reconocedor.record(
                        fuente
                    )

                texto_voz = reconocedor.recognize_google(
                    audio_grabado,
                    language="es-CO"
                )

                st.info(
                    f"Has dicho: {texto_voz}"
                )

                procesar_orden(texto_voz)

                st.rerun()

        except sr.UnknownValueError:

            st.warning(
                "No pude reconocer tu voz. Intenta nuevamente."
            )

        except sr.RequestError:

            st.error(
                "No se pudo conectar al servicio de reconocimiento de voz."
            )

        except Exception as error:

            st.error(
                f"Error procesando el audio: {error}"
            )

else:

    st.warning(
        "Para activar el micrófono instala "
        "streamlit-mic-recorder y SpeechRecognition."
    )


# =========================================================
# 17. RESPUESTA ESCRITA
# =========================================================

st.markdown("### 🤖 Respuesta de GranjaConecta")

st.markdown(
    f"""
    <div class="tarjeta">
        <div style="
            color:#17472D;
            font-size:15px;
            line-height:1.6;
        ">
            {st.session_state.respuesta}
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

if st.session_state.ultimo_mensaje_esp:

    st.caption(
        "Última confirmación recibida del ESP32: "
        + st.session_state.ultimo_mensaje_esp
    )


# =========================================================
# 18. HISTORIAL
# =========================================================

st.markdown("### 📝 Historial")

if st.session_state.historial:

    for elemento in reversed(
        st.session_state.historial[-15:]
    ):

        st.markdown(
            f"**👤 Tú:** {elemento['usuario']}"
        )

        st.markdown(
            f"**🐔 GranjaConecta:** {elemento['asistente']}"
        )

        st.divider()

else:

    st.caption("Todavía no hay órdenes registradas.")
