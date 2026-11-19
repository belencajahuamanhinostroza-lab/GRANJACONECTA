
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
# 3. ESTADOS DE STREAMLIT
# =========================================================

if "respuesta" not in st.session_state:
    st.session_state.respuesta = (
        "Hola. Soy GranjaConecta. Puedo controlar el "
        "bebedero y consultar el nivel de agua."
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
            "valvula": "cerrada",
            "vaciando": False,
            "lecturaAguaValida": False
        },
        "conectado": False,
        "respuesta_esp32": "",
        "lock": Lock()
    }

    def al_conectar(
        client, userdata, flags, reason_code, properties
    ):
        if reason_code == 0:
            estado["conectado"] = True
            client.subscribe(TOPIC)
            print("GranjaConecta: conexión MQTT activa")
        else:
            estado["conectado"] = False
            print("Error de conexión MQTT:", reason_code)

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

            tipo = recibido.get("tipo")

            if tipo == "telemetria":

                nuevos_datos = recibido.get(
                    "datos",
                    {}
                )

                with estado["lock"]:
                    estado["datos"].update(nuevos_datos)

            elif tipo == "respuesta":

                mensaje = recibido.get("message", "")

                with estado["lock"]:
                    estado["respuesta_esp32"] = mensaje

                print("Respuesta ESP32:", mensaje)

        except Exception as error:
            print("Error al recibir MQTT:", error)

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
        print("Error MQTT:", error)

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
        print("Error al enviar comando:", error)
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


def obtener_distancia():

    datos = obtener_datos()

    try:
        return float(datos.get("distancia", 0))
    except (ValueError, TypeError):
        return 0


def obtener_valvula():

    valor = str(
        obtener_datos().get("valvula", "cerrada")
    ).lower()

    if "abier" in valor or valor == "open":
        return "abierta"

    return "cerrada"


def esta_vaciando():

    valor = obtener_datos().get("vaciando", False)

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

    # Cerrar válvula
    if any(frase in texto for frase in [
        "cierra la valvula",
        "cierra valvula",
        "cerrar la valvula",
        "cierrala",
        "cierra el paso del agua"
    ]):
        return "VALVULA_CERRAR"

    # Vaciar bebedero
    if any(frase in texto for frase in [
        "vacia la valvula",
        "vaciar la valvula",
        "vacia el bebedero",
        "vaciar el bebedero",
        "vacia el agua",
        "vaciar el agua",
        "saca toda el agua"
    ]):
        return "BEBEDERO_VACIAR"

    # Llenar hasta 90 %
    if any(frase in texto for frase in [
        "dejala llena",
        "dejalo lleno",
        "deja el bebedero lleno",
        "llena completamente el bebedero",
        "llena el bebedero",
        "llenalo completamente"
    ]):
        return "BEBEDERO_LLENO"

    # Abrir válvula
    if any(frase in texto for frase in [
        "abre la valvula",
        "abrir la valvula",
        "abre valvula",
        "abre el paso del agua"
    ]):
        return "VALVULA_ABRIR"

    return None


# =========================================================
# 8. RESPONDER CONSULTAS
# =========================================================

def responder(pregunta):

    pregunta = normalizar(pregunta)

    nivel = obtener_nivel()
    distancia = obtener_distancia()

    if not lectura_valida():
        return (
            "Todavía estoy esperando los datos del bebedero. "
            "Comprueba que el ESP32 esté conectado."
        )

    # Consultar distancia
    if any(frase in pregunta for frase in [
        "distancia",
        "cuantos centimetros",
        "cuantos cm",
        "sensor ultrasonico",
        "sensor de distancia"
    ]):

        if distancia <= 0:
            return (
                "El sensor HC-SR04 todavía no está "
                "proporcionando una distancia válida."
            )

        return (
            f"El sensor HC-SR04 registra una distancia "
            f"de {distancia:.1f} centímetros."
        )

    # Consultar nivel de agua
    if any(frase in pregunta for frase in [
        "porcentaje",
        "cuanta agua",
        "nivel de agua",
        "cuanto tiene de agua",
        "como esta el bebedero",
        "cuanto esta lleno"
    ]):

        return (
            f"El bebedero tiene actualmente "
            f"{nivel:.0f}% de agua."
        )

    # Consultar cuándo llenar
    if any(frase in pregunta for frase in [
        "cuando debo llenarlo de nuevo",
        "cuando debo volver a llenarlo",
        "cuando lo lleno de nuevo",
        "cuando hay que llenarlo",
        "cuando debo llenar el bebedero"
    ]):

        if nivel <= NIVEL_BAJO:
            return (
                f"El bebedero tiene {nivel:.0f}% de agua. "
                "El nivel es bajo y debes volver a llenarlo ahora."
            )

        return (
            f"El bebedero tiene {nivel:.0f}% de agua. "
            f"Te recomiendo volver a llenarlo cuando llegue "
            f"al {NIVEL_BAJO}% o menos."
        )

    # Consultar estado de la válvula
    if "estado" in pregunta and "valvula" in pregunta:

        valvula = obtener_valvula()

        return (
            f"La válvula se encuentra actualmente {valvula}."
        )

    return (
        "No reconocí esa solicitud. Puedes pedirme que abra "
        "o cierre la válvula, que vacíe el bebedero, "
        "que lo deje lleno, o consultar el porcentaje "
        "de agua, la distancia y cuándo volver a llenarlo."
    )


# =========================================================
# 9. PROCESAR MENSAJES DE VOZ Y TEXTO
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
                "He cerrado la válvula. El llenado se "
                "detendrá y conservará el nivel actual."
            ),
            "BEBEDERO_VACIAR": (
                "Estoy iniciando el vaciado del bebedero."
            ),
            "BEBEDERO_LLENO": (
                "Estoy llenando el bebedero hasta alcanzar "
                "el 90%. Después cerraré la válvula automáticamente."
            )
        }

        if enviar_comando(comando):
            respuesta = mensajes[comando]
        else:
            respuesta = (
                "No pude enviar la orden. Comprueba que "
                "el ESP32 esté conectado al servidor MQTT."
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
            lang="es",
            slow=False
        )

        voz.write_to_fp(archivo)

        contenido = archivo.getvalue()

        if not contenido:
            raise RuntimeError(
                "El servicio no devolvió contenido de audio."
            )

        return contenido

    except Exception as error:

        st.error(
            "No se pudo generar el audio. "
            "Comprueba la conexión a internet de la aplicación. "
            f"Detalle: {error}"
        )

        return None


# =========================================================
# 11. ENCABEZADO
# =========================================================

st.title("🐔 GranjaConecta")

st.subheader("Control inteligente del bebedero")

st.write(
    "Da órdenes por voz o texto y consulta el nivel "
    "de agua de tus gallinas."
)

if mqtt_estado["conectado"]:
    st.success("🟢 Conexión MQTT activa con el ESP32.")
else:
    st.error("🔴 Sin conexión MQTT con el ESP32.")


# =========================================================
# 12. GRÁFICO Y ESTADO DEL BEBEDERO
# =========================================================

@st.fragment(run_every="1s")
def mostrar_estado_bebedero():

    nivel = obtener_nivel()
    distancia = obtener_distancia()
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

            <div style="
                position:absolute;
                top:8px;
                left:0;
                width:100%;
                text-align:center;
                color:#17472D;
                font-size:14px;
                font-weight:bold;
                z-index:2;
            ">
                AGUA
            </div>
        </div>
        """

        st.markdown(
            dibujo,
            unsafe_allow_html=True
        )

        st.markdown(
            f"<h3 style='text-align:center;color:#17472D;'>{nivel:.0f}%</h3>",
            unsafe_allow_html=True
        )

    with columna_datos:

        st.markdown(
            "<h3 style='color:#17472D;'>📊 Datos del bebedero</h3>",
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

        if distancia > 0:
            st.metric(
                "Distancia HC-SR04",
                f"{distancia:.1f} cm"
            )
        else:
            st.metric(
                "Distancia HC-SR04",
                "Sin lectura"
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
            st.info("Bebedero detenido.")

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
            format="audio/mpeg"
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
# 17. ÓRDENES DISPONIBLES
# =========================================================

st.divider()

with st.expander("📢 Órdenes y preguntas disponibles"):

    st.markdown("""
    **Órdenes:**

    - Abre la válvula.
    - Cierra la válvula.
    - Vacía el bebedero.
    - Déjala llena.

    **Preguntas:**

    - Dame el porcentaje de agua.
    - ¿Cuándo debo llenarlo de nuevo?
    - ¿Cuál es la distancia del sensor?
    - ¿Cuál es el estado de la válvula?
    """)
