
import streamlit as st
import paho.mqtt.client as mqtt
import json
import io
import re
import unicodedata
import uuid
import hashlib
import speech_recognition as sr

from gtts import gTTS
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

NIVEL_BAJO = 20
NIVEL_MAXIMO = 90


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

.stProgress > div > div > div > div {
    background-color: #17472D !important;
}

div[data-testid="stAlert"] p {
    color: #17472D !important;
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
# 3. ESTADOS
# =========================================================

if "respuesta" not in st.session_state:
    st.session_state.respuesta = (
        "Hola. Soy GranjaConecta. "
        "Puedo controlar el bebedero y consultar "
        "el nivel de agua."
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
            "valvula": "cerrada",
            "vaciando": False,
            "lecturaAguaValida": False
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


def obtener_nivel():

    datos = obtener_datos()

    valor = datos.get(
        "nivelAgua",
        datos.get("agua", 0)
    )

    try:
        valor = float(valor)
    except (ValueError, TypeError):
        valor = 0

    return max(0, min(100, valor))


def obtener_valvula():

    datos = obtener_datos()

    valor = str(
        datos.get("valvula", "cerrada")
    ).lower()

    if "abier" in valor or valor == "open":
        return "abierta"

    return "cerrada"


def esta_vaciando():

    valor = obtener_datos().get("vaciando", False)

    if isinstance(valor, str):
        return valor.lower() in ["true", "1", "si", "sí"]

    return bool(valor)


def lectura_valida():

    valor = obtener_datos().get(
        "lecturaAguaValida",
        False
    )

    if isinstance(valor, str):
        return valor.lower() in ["true", "1", "si", "sí"]

    return bool(valor)


# =========================================================
# 6. NORMALIZAR TEXTO
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

    texto = re.sub(r"[¿?¡!.,;:]", "", texto)

    return re.sub(r"\s+", " ", texto)


# =========================================================
# 7. INTERPRETAR ÓRDENES
# =========================================================

def interpretar(texto):

    texto = normalizar(texto)

    if any(frase in texto for frase in [
        "cierra la valvula",
        "cierra valvula",
        "cerrar la valvula",
        "cierrala"
    ]):
        return "VALVULA_CERRAR"

    if any(frase in texto for frase in [
        "vacia la valvula",
        "vaciar la valvula",
        "vacia el bebedero",
        "vaciar el bebedero",
        "vacia el agua"
    ]):
        return "BEBEDERO_VACIAR"

    if any(frase in texto for frase in [
        "dejala llena",
        "dejalo lleno",
        "deja el bebedero lleno",
        "llena completamente el bebedero"
    ]):
        return "BEBEDERO_LLENO"

    if any(frase in texto for frase in [
        "abre la valvula",
        "abrir la valvula",
        "abre valvula"
    ]):
        return "VALVULA_ABRIR"

    return None


# =========================================================
# 8. RESPONDER CONSULTAS
# =========================================================

def responder(pregunta):

    pregunta = normalizar(pregunta)
    nivel = obtener_nivel()

    if (
        "porcentaje" in pregunta
        or "cuanta agua" in pregunta
        or "nivel de agua" in pregunta
    ):

        if not lectura_valida():
            return (
                "Todavía estoy esperando los datos del bebedero. "
                "Comprueba la conexión con el ESP32."
            )

        return (
            f"El bebedero tiene actualmente "
            f"{nivel:.0f}% de agua."
        )

    if (
        "cuando debo llenarlo de nuevo" in pregunta
        or "cuando debo volver a llenarlo" in pregunta
        or "cuando lo lleno de nuevo" in pregunta
        or "cuando hay que llenarlo" in pregunta
    ):

        if not lectura_valida():
            return (
                "Todavía no tengo una lectura del nivel de agua. "
                "Comprueba la conexión con el ESP32."
            )

        if nivel <= NIVEL_BAJO:
            return (
                f"El bebedero tiene {nivel:.0f}% de agua. "
                "Debes volver a llenarlo ahora."
            )

        return (
            f"El bebedero tiene {nivel:.0f}% de agua. "
            f"Debes volver a llenarlo cuando llegue al "
            f"{NIVEL_BAJO}% o menos."
        )

    return (
        "No reconocí esa solicitud. Puedes pedirme que abra "
        "o cierre la válvula, que vacíe el bebedero, "
        "que lo deje lleno, o consultar el porcentaje "
        "de agua y cuándo llenarlo."
    )


# =========================================================
# 9. RESPUESTAS Y PROCESAMIENTO
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
                "He cerrado la válvula. El llenado "
                "se detendrá en el nivel actual."
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
# 10. GENERAR AUDIO
# =========================================================

def generar_audio(texto):

    try:
        archivo = io.BytesIO()

        voz = gTTS(
            text=texto,
            lang="es"
        )

        voz.write_to_fp(archivo)
        archivo.seek(0)

        return archivo

    except Exception as error:
        st.error(
            f"No se pudo generar el audio: {error}"
        )
        return None


# =========================================================
# 11. ENCABEZADO
# =========================================================

st.title("🐔 GranjaConecta")

st.subheader("Control inteligente del bebedero")

st.write(
    "Da órdenes por voz o texto y consulta "
    "el nivel de agua de tus gallinas."
)

if mqtt_estado["conectado"]:
    st.success("Conexión MQTT activa.")
else:
    st.error("Sin conexión MQTT con el ESP32.")


# =========================================================
# 12. DIBUJO Y ESTADO DEL BEBEDERO
# =========================================================

@st.fragment(run_every="1s")
def mostrar_estado_bebedero():

    nivel = obtener_nivel()
    valvula = obtener_valvula()
    vaciando = esta_vaciando()
    valida = lectura_valida()

    columna_dibujo, columna_datos = st.columns([1.2, 1])

    with columna_dibujo:

        st.markdown(
            "<h3 style='color:#17472D;'>🐔 Bebedero</h3>",
            unsafe_allow_html=True
        )

        altura = max(0, min(100, nivel))

        dibujo = f"""
        <div style="
            width:190px;
            height:250px;
            margin:20px auto;
            border:4px solid #17472D;
            border-radius:15px 15px 30px 30px;
            position:relative;
            overflow:hidden;
            background:#F8FFF6;
            box-sizing:border-box;
        ">
            <div style="
                position:absolute;
                bottom:0;
                left:0;
                width:100%;
                height:{altura}%;
                background:linear-gradient(
                    to top,
                    #238A80,
                    #75D6C0
                );
                transition:height 0.8s ease;
            "></div>
        </div>
        """

        st.markdown(
            dibujo,
            unsafe_allow_html=True
        )

    with columna_datos:

        st.markdown(
            "<h3 style='color:#17472D;'>📊 Nivel de agua</h3>",
            unsafe_allow_html=True
        )

        st.metric(
            "Porcentaje de agua",
            f"{nivel:.0f}%"
        )

        st.progress(
            max(0.0, min(1.0, nivel / 100)),
            text=f"{nivel:.0f}% de llenado"
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
            st.success("💧 LLENANDO EL BEBEDERO")

        else:
            st.info("Bebedero en espera.")

        if not valida:
            st.warning(
                "Esperando la primera lectura del ESP32."
            )

        elif nivel <= NIVEL_BAJO:
            st.warning(
                "Nivel bajo. Es necesario volver a llenarlo."
            )

        elif nivel >= NIVEL_MAXIMO:
            st.success(
                "Nivel máximo alcanzado."
            )

        else:
            st.success(
                "Nivel de agua suficiente."
            )


mostrar_estado_bebedero()


# =========================================================
# 13. CONTROL POR VOZ
# =========================================================

st.divider()

st.subheader("🎙️ Habla con GranjaConecta")

st.write(
    "Pulsa el micrófono, di tu orden o pregunta "
    "y termina la grabación."
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
                    "El micrófono no entregó un WAV válido. "
                    "Vuelve a grabar."
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
# 15. RESPUESTA DE TEXTO Y AUDIO
# =========================================================

st.divider()

st.subheader("💬 Respuesta de GranjaConecta")

st.info(
    st.session_state.respuesta
)

if st.button(
    "🔊 Escuchar respuesta",
    use_container_width=True
):

    audio = generar_audio(
        st.session_state.respuesta
    )

    if audio:
        st.audio(
            audio,
            format="audio/mp3"
        )


# =========================================================
# 16. HISTORIAL
# =========================================================

st.divider()

st.subheader("📝 Conversación")

if not st.session_state.historial:
    st.caption("Todavía no hay mensajes.")

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
# 17. COMANDOS DISPONIBLES
# =========================================================

st.divider()

with st.expander("📢 Órdenes y preguntas disponibles"):

    st.markdown("""
    **Órdenes:**

    - Abre la válvula.
    - Cierra la válvula.
    - Vacía la válvula.
    - Déjala llena.

    **Preguntas:**

    - Dame el porcentaje de agua.
    - ¿Cuándo debo llenarlo de nuevo?
    """)
