
import streamlit as st
import paho.mqtt.client as mqtt
import json
import re
import unicodedata
import uuid
import io
import hashlib
import speech_recognition as sr

from streamlit_mic_recorder import mic_recorder
from threading import Lock


# =========================================================
# 1. CONFIGURACIÓN
# =========================================================

st.set_page_config(
    page_title="GranjaConecta | Bebedero",
    page_icon="🐔",
    layout="wide"
)

BROKER = "broker.mqttdashboard.com"
PORT = 1883
TOPIC = "granjaconecta"

DISTANCIA_VACIO = 30.0
DISTANCIA_LLENO = 10.0


# =========================================================
# 2. ESTILOS
# =========================================================

st.markdown("""
<style>

.stApp {
    background-color: #EDF5E9;
}

html, body, [class*="css"] {
    color: #17472D !important;
}

h1, h2, h3, h4, p, label, span, li {
    color: #17472D;
}

[data-testid="stHeader"] {
    background-color: #EDF5E9;
}

section[data-testid="stSidebar"] {
    background-color: #DCEBD8;
}

.stButton > button,
.stFormSubmitButton > button {
    background-color: #17472D !important;
    color: white !important;
    border: 2px solid #17472D !important;
    border-radius: 12px !important;
    font-weight: bold !important;
}

.stButton > button p,
.stButton > button span,
.stFormSubmitButton > button p,
.stFormSubmitButton > button span {
    color: white !important;
}

.stTextInput input {
    color: #17472D !important;
    background: white !important;
    border: 1px solid #A9C5A6 !important;
    border-radius: 10px !important;
}

div[data-testid="stMetric"] {
    background: #DCEBD8;
    padding: 15px;
    border-radius: 12px;
}

div[data-testid="stMetric"] label,
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #17472D !important;
}

div[data-testid="stAlert"] p {
    color: #17472D !important;
}

.stProgress > div > div > div > div {
    background-color: #17472D !important;
}

::-webkit-scrollbar {
    width: 10px;
}

::-webkit-scrollbar-track {
    background: #DCEBD8;
}

::-webkit-scrollbar-thumb {
    background: #17472D;
    border-radius: 10px;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# 3. ESTADOS DE STREAMLIT
# =========================================================

if "respuesta" not in st.session_state:
    st.session_state.respuesta = (
        "Hola. Soy GranjaConecta. "
        "Puedo controlar el bebedero y consultar "
        "su nivel de agua."
    )

if "texto_reconocido" not in st.session_state:
    st.session_state.texto_reconocido = ""

if "ultimo_audio" not in st.session_state:
    st.session_state.ultimo_audio = None

if "historial" not in st.session_state:
    st.session_state.historial = []


# =========================================================
# 4. CONEXIÓN MQTT
# =========================================================

@st.cache_resource
def crear_conexion_mqtt():

    estado = {
        "datos": {
            "nivelAgua": 0,
            "agua": 0,
            "distancia": 0,
            "distanciaHC": 0,
            "valvula": "cerrada",
            "vaciando": False,
            "lecturaAguaValida": False,
            "lecturaHCValida": False,
            "estadoAgua": "ESPERANDO"
        },
        "conectado": False,
        "lock": Lock()
    }

    def al_conectar(
        client, userdata, flags, reason_code, properties
    ):

        if reason_code == 0:
            estado["conectado"] = True
            client.subscribe(TOPIC)
            print("Bebedero conectado a MQTT")
        else:
            estado["conectado"] = False

    def al_desconectar(
        client, userdata, disconnect_flags,
        reason_code, properties
    ):

        estado["conectado"] = False

    def al_recibir(client, userdata, msg):

        try:

            recibido = json.loads(
                msg.payload.decode("utf-8")
            )

            if recibido.get("tipo") == "telemetria":

                nuevos_datos = recibido.get(
                    "datos",
                    recibido
                )

                with estado["lock"]:
                    estado["datos"].update(nuevos_datos)

        except Exception as error:
            print("Error MQTT:", error)

    cliente = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="GranjaConecta_Bebedero_" + uuid.uuid4().hex[:8]
    )

    cliente.on_connect = al_conectar
    cliente.on_disconnect = al_desconectar
    cliente.on_message = al_recibir

    try:

        cliente.connect(BROKER, PORT, 60)
        cliente.loop_start()

    except Exception as error:
        print("Error de conexión MQTT:", error)

    return cliente, estado


cliente, mqtt_estado = crear_conexion_mqtt()


# =========================================================
# 5. FUNCIONES MQTT
# =========================================================

def enviar_comando(comando):

    if not mqtt_estado["conectado"]:
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

        return resultado.rc == mqtt.MQTT_ERR_SUCCESS

    except Exception as error:

        print("Error MQTT:", error)
        return False


def obtener_datos():

    with mqtt_estado["lock"]:
        return dict(mqtt_estado["datos"])


def obtener_distancia():

    datos = obtener_datos()

    try:

        valor = float(
            datos.get("distancia", 0)
        )

        return max(10.0, min(30.0, valor))

    except (ValueError, TypeError):
        return 0.0


def obtener_valvula():

    valor = str(
        obtener_datos().get(
            "valvula",
            "cerrada"
        )
    ).lower()

    if "abier" in valor or valor == "open":
        return "abierta"

    return "cerrada"


def esta_vaciando():

    valor = obtener_datos().get(
        "vaciando",
        False
    )

    if isinstance(valor, str):
        return valor.lower() in [
            "true", "1", "si", "sí"
        ]

    return bool(valor)


def lectura_valida():

    valor = obtener_datos().get(
        "lecturaAguaValida",
        False
    )

    if isinstance(valor, str):
        return valor.lower() in [
            "true", "1", "si", "sí"
        ]

    return bool(valor)


# =========================================================
# 6. ESTADO DEL AGUA
# =========================================================

def obtener_estado_agua(distancia):

    if distancia <= 0:
        return "ESPERANDO LECTURA"

    if distancia < 10:
        return "POSIBLE REBOSAMIENTO"

    if distancia <= 10:
        return "LLENO"

    if distancia > 25 and distancia < 30:
        return "NIVEL BAJO"

    if distancia >= 30:
        return "MUY POCA AGUA"

    return "NORMAL"


def obtener_altura_agua(distancia):

    if distancia <= 0:
        return 0

    altura = (
        (DISTANCIA_VACIO - distancia)
        /
        (DISTANCIA_VACIO - DISTANCIA_LLENO)
    ) * 100

    return max(0, min(100, altura))


# =========================================================
# 7. NORMALIZAR TEXTO
# =========================================================

def normalizar(texto):

    texto = texto.lower().strip()

    texto = unicodedata.normalize(
        "NFD",
        texto
    )

    texto = "".join(
        caracter for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )

    texto = re.sub(
        r"[¿?¡!.,;:]",
        "",
        texto
    )

    return re.sub(
        r"\s+",
        " ",
        texto
    )


# =========================================================
# 8. INTERPRETAR ÓRDENES
# =========================================================

def interpretar(texto):

    texto = normalizar(texto)

    if any(frase in texto for frase in [
        "cierra la valvula",
        "cierra valvula",
        "cerrar la valvula",
        "cierrala",
        "deten el llenado",
        "detener llenado",
        "para de llenar"
    ]):

        return "VALVULA_CERRAR"

    if any(frase in texto for frase in [
        "vacia la valvula",
        "vaciar la valvula",
        "vacia el bebedero",
        "vaciar el bebedero",
        "vacia el agua",
        "vaciar el agua"
    ]):

        return "BEBEDERO_VACIAR"

    if any(frase in texto for frase in [
        "dejala llena",
        "dejalo lleno",
        "deja el bebedero lleno",
        "llena completamente el bebedero",
        "llena el bebedero",
        "llenar el bebedero",
        "llenalo"
    ]):

        return "BEBEDERO_LLENO"

    if any(frase in texto for frase in [
        "abre la valvula",
        "abrir la valvula",
        "abre valvula",
        "comienza a llenar",
        "empieza a llenar"
    ]):

        return "VALVULA_ABRIR"

    return None


# =========================================================
# 9. RESPONDER CONSULTAS
# =========================================================

def responder(pregunta):

    pregunta = normalizar(pregunta)

    distancia = obtener_distancia()

    if not lectura_valida():

        return (
            "Todavía estoy esperando los datos del bebedero. "
            "Comprueba la conexión con el ESP32."
        )

    estado = obtener_estado_agua(distancia)

    if any(frase in pregunta for frase in [
        "distancia",
        "centimetros",
        "cuantos centimetros",
        "cuanto falta"
    ]):

        return (
            f"La distancia actual entre el sensor "
            f"y el agua es de {distancia:.1f} centímetros."
        )

    if any(frase in pregunta for frase in [
        "nivel de agua",
        "como esta el agua",
        "estado del agua",
        "cuanta agua hay"
    ]):

        return (
            f"El agua se encuentra a {distancia:.1f} centímetros "
            f"del sensor. El estado actual es: {estado.lower()}."
        )

    if any(frase in pregunta for frase in [
        "cuando debo llenarlo",
        "cuando debo volver a llenarlo",
        "cuando lo lleno de nuevo",
        "cuando hay que llenarlo"
    ]):

        if distancia >= 30:

            return (
                "El bebedero tiene muy poca agua. "
                "Debes llenarlo ahora."
            )

        if distancia > 25:

            return (
                f"La distancia es de {distancia:.1f} cm. "
                "El nivel está bajo. Es recomendable "
                "volver a llenar el bebedero."
            )

        if distancia <= 10:

            return (
                "El bebedero está lleno. "
                "No es necesario agregar más agua."
            )

        return (
            f"El nivel está normal, con una distancia "
            f"de {distancia:.1f} cm. "
            "Puedes mantenerlo así por ahora."
        )

    if "valvula" in pregunta:

        return (
            f"La válvula está actualmente {obtener_valvula()}."
        )

    if "esta llenando" in pregunta or "llenando" in pregunta:

        if obtener_valvula() == "abierta" and not esta_vaciando():
            return "Sí. El bebedero se está llenando."

        return "No. Actualmente el bebedero no está llenándose."

    if "esta vaciando" in pregunta or "vaciando" in pregunta:

        if esta_vaciando():
            return "Sí. El bebedero se está vaciando."

        return "No. Actualmente el bebedero no se está vaciando."

    return (
        "No reconocí esa consulta. Puedes preguntarme "
        "cuántos centímetros tiene el agua, cuál es su estado, "
        "cuándo debes llenarlo o cómo está la válvula."
    )


# =========================================================
# 10. PROCESAR MENSAJES
# =========================================================

def procesar_mensaje(texto):

    if not texto or not texto.strip():
        return

    st.session_state.historial.append(
        ("Tú", texto)
    )

    comando = interpretar(texto)

    if comando:

        mensajes = {

            "VALVULA_ABRIR": (
                "Estoy abriendo la válvula para comenzar "
                "a llenar el bebedero."
            ),

            "VALVULA_CERRAR": (
                "Estoy cerrando la válvula. "
                "El nivel de agua se conservará."
            ),

            "BEBEDERO_VACIAR": (
                "Estoy iniciando el vaciado del bebedero."
            ),

            "BEBEDERO_LLENO": (
                "Estoy llenando el bebedero hasta alcanzar "
                "el nivel máximo permitido."
            )
        }

        if enviar_comando(comando):

            respuesta = mensajes[comando]

        else:

            respuesta = (
                "No pude enviar la orden. "
                "Comprueba la conexión MQTT con el ESP32."
            )

    else:

        respuesta = responder(texto)

    st.session_state.respuesta = respuesta

    st.session_state.historial.append(
        ("GranjaConecta", respuesta)
    )


# =========================================================
# 11. ENCABEZADO
# =========================================================

st.title("🐔 GranjaConecta")

st.subheader("Control inteligente del bebedero")

st.write(
    "Controla el llenado, vaciado y válvula del bebedero. "
    "Consulta su distancia en centímetros mediante voz o texto."
)

if mqtt_estado["conectado"]:
    st.success("Conexión MQTT activa con el ESP32.")
else:
    st.error("Sin conexión MQTT con el ESP32.")


# =========================================================
# 12. VISUALIZACIÓN DEL BEBEDERO
# =========================================================

@st.fragment(run_every="1s")
def mostrar_estado_bebedero():

    datos = obtener_datos()

    distancia = obtener_distancia()
    valvula = obtener_valvula()
    vaciando = esta_vaciando()
    valida = lectura_valida()

    estado = obtener_estado_agua(distancia)
    altura = obtener_altura_agua(distancia)

    columna_dibujo, columna_datos = st.columns(
        [1.1, 1]
    )

    with columna_dibujo:

        st.markdown(
            "<h3 style='color:#17472D;'>🐔 Bebedero de las gallinas</h3>",
            unsafe_allow_html=True
        )

        dibujo = f"""
        <div style="
            width:210px;
            height:270px;
            margin:20px auto;
            border:5px solid #17472D;
            border-radius:18px 18px 35px 35px;
            position:relative;
            overflow:hidden;
            background:#F8FFF6;
            box-shadow:0 5px 12px rgba(23,71,45,0.12);
            box-sizing:border-box;
        ">

            <div style="
                position:absolute;
                top:0;
                left:0;
                width:100%;
                height:8px;
                background:#17472D;
                z-index:2;
            "></div>

            <div style="
                position:absolute;
                bottom:0;
                left:0;
                width:100%;
                height:{altura:.1f}%;
                background:linear-gradient(
                    to top,
                    #168C9B,
                    #76DCCB
                );
                transition:height 1s ease;
            "></div>

            <div style="
                position:absolute;
                top:10px;
                left:0;
                width:100%;
                text-align:center;
                color:#17472D;
                font-size:13px;
                font-weight:bold;
                z-index:3;
            ">
                AGUA
            </div>

            <div style="
                position:absolute;
                bottom:10px;
                width:100%;
                text-align:center;
                color:#17472D;
                font-size:14px;
                font-weight:bold;
                z-index:3;
            ">
                {altura:.0f}%
            </div>

        </div>
        """

        st.markdown(
            dibujo,
            unsafe_allow_html=True
        )

        st.caption(
            "Representación visual del nivel de agua simulado."
        )

    with columna_datos:

        st.markdown(
            "<h3 style='color:#17472D;'>📏 Distancia del agua</h3>",
            unsafe_allow_html=True
        )

        if valida:

            st.metric(
                "Distancia entre sensor y agua",
                f"{distancia:.1f} cm"
            )

        else:

            st.metric(
                "Distancia entre sensor y agua",
                "-- cm"
            )

        st.markdown(
            "<h3 style='color:#17472D;'>Estado del bebedero</h3>",
            unsafe_allow_html=True
        )

        if not valida:

            st.warning(
                "Esperando la primera lectura del ESP32."
            )

        elif distancia < 10:

            st.error(
                "🚨 POSIBLE REBOSAMIENTO. "
                "Se debe detener el llenado."
            )

        elif distancia <= 10:

            st.success(
                "🟢 BEBEDERO LLENO. "
                "La válvula debe permanecer cerrada."
            )

        elif distancia > 25:

            st.warning(
                "🟠 NIVEL BAJO. "
                "Es necesario llenar el bebedero."
            )

        else:

            st.success(
                "🟢 NIVEL NORMAL. "
                "El agua está dentro del rango adecuado."
            )

        st.markdown(
            "<h3 style='color:#17472D;'>Estado de la válvula</h3>",
            unsafe_allow_html=True
        )

        if valvula == "abierta":

            st.success("🟢 VÁLVULA ABIERTA")

        else:

            st.error("🔴 VÁLVULA CERRADA")

        if vaciando:

            st.warning("💧 VACIANDO EL BEBEDERO")

        elif valvula == "abierta":

            st.info("💧 LLENANDO EL BEBEDERO")

        else:

            st.info("Bebedero en espera.")

        st.caption(
            f"Estado general: {estado}"
        )

        # La lectura física se muestra por separado
        # para evitar confundirla con la simulación.
        lectura_hc = datos.get("distanciaHC", 0)
        hc_valido = datos.get("lecturaHCValida", False)

        if hc_valido:

            try:
                st.caption(
                    f"Lectura física HC-SR04: "
                    f"{float(lectura_hc):.1f} cm"
                )
            except (ValueError, TypeError):
                pass


mostrar_estado_bebedero()


# =========================================================
# 13. CONTROL POR VOZ
# =========================================================

st.divider()

st.subheader("🎙️ Habla con GranjaConecta")

st.write(
    "Pulsa el micrófono, di tu orden o pregunta "
    "y después termina la grabación."
)

audio_voz = mic_recorder(
    start_prompt="🎙️ Hablar",
    stop_prompt="⏹️ Terminar",
    just_once=True,
    format="wav",
    key="microfono_bebedero"
)

if audio_voz and audio_voz.get("bytes"):

    bytes_audio = audio_voz["bytes"]

    identificador = audio_voz.get("id")

    if identificador is None:

        identificador = hashlib.md5(
            bytes_audio
        ).hexdigest()

    if identificador != st.session_state.ultimo_audio:

        st.session_state.ultimo_audio = identificador

        try:

            if not bytes_audio.startswith(b"RIFF"):

                raise ValueError(
                    "La grabación no tiene un formato WAV válido."
                )

            reconocedor = sr.Recognizer()

            with sr.AudioFile(
                io.BytesIO(bytes_audio)
            ) as fuente:

                audio = reconocedor.record(fuente)

            texto = reconocedor.recognize_google(
                audio,
                language="es-CO"
            )

            st.session_state.texto_reconocido = texto

            procesar_mensaje(texto)

            st.success(
                "Mensaje reconocido y procesado."
            )

        except sr.UnknownValueError:

            st.warning(
                "No pude entender lo que dijiste. "
                "Inténtalo nuevamente."
            )

        except sr.RequestError:

            st.error(
                "No se pudo conectar con el reconocimiento de voz."
            )

        except Exception as error:

            st.error(
                f"Error al procesar el audio: {error}"
            )


if st.session_state.texto_reconocido:

    st.markdown("**🗣️ Lo que dijiste:**")

    st.info(
        st.session_state.texto_reconocido
    )


# =========================================================
# 14. CONTROL POR TEXTO
# =========================================================

st.divider()

st.subheader("⌨️ Escribe una orden o pregunta")

with st.form(
    "formulario_bebedero",
    clear_on_submit=True
):

    texto_usuario = st.text_input(
        "Mensaje",
        placeholder="Ejemplo: Abre la válvula"
    )

    enviar = st.form_submit_button(
        "Enviar",
        use_container_width=True
    )

    if enviar and texto_usuario.strip():

        procesar_mensaje(texto_usuario)


# =========================================================
# 15. RESPUESTA DE TEXTO
# =========================================================

st.divider()

st.subheader("💬 Respuesta de GranjaConecta")

st.info(
    st.session_state.respuesta
)


# =========================================================
# 16. HISTORIAL
# =========================================================

st.divider()

st.subheader("📝 Conversación")

if not st.session_state.historial:

    st.caption(
        "Todavía no hay mensajes."
    )

for remitente, mensaje in st.session_state.historial[-10:]:

    if remitente == "Tú":

        st.markdown(
            f"**🧑 Tú:** {mensaje}"
        )

    else:

        st.markdown(
            f"**🐔 GranjaConecta:** {mensaje}"
        )


# =========================================================
# 17. ÓRDENES Y CONSULTAS
# =========================================================

st.divider()

with st.expander("📢 Órdenes y preguntas disponibles"):

    st.markdown("""
    **Órdenes por voz o texto**

    - Abre la válvula.
    - Cierra la válvula.
    - Vacía el bebedero.
    - Llena el bebedero.
    - Detén el llenado.

    **Preguntas**

    - ¿Cuántos centímetros tiene el agua?
    - ¿Cómo está el nivel de agua?
    - ¿Cuándo debo llenarlo de nuevo?
    - ¿La válvula está abierta?
    - ¿Está llenando el bebedero?
    - ¿Está vaciando el bebedero?
    """)
