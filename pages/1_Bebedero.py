
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
# 2. ESTILOS GENERALES
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
    min-height: 42px;
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

/* Paneles del bebedero */

.panel-titulo {
    background: #DCEBD8;
    border-left: 5px solid #17472D;
    border-radius: 10px;
    padding: 12px 15px;
    margin: 15px 0 10px 0;
    color: #17472D;
    font-weight: 800;
    font-size: 14px;
}

/* Dibujo del bebedero */

.bebedero-zona {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 25px 10px 10px 10px;
}

.bebedero-estructura {
    width: 250px;
    height: 270px;
    position: relative;
    overflow: hidden;
    border: 6px solid #17472D;
    border-top: 10px solid #17472D;
    border-radius: 20px 20px 48px 48px;
    background: linear-gradient(
        180deg,
        #FFFFFF,
        #F4FAF1
    );
    box-shadow:
        0 8px 18px rgba(23,71,45,0.15),
        inset 0 0 12px rgba(23,71,45,0.07);
}

.bebedero-agua {
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    transition: height 1s ease;
    background: linear-gradient(
        180deg,
        #80DCCB 0%,
        #39B7A5 55%,
        #208D82 100%
    );
}

.bebedero-agua::before {
    content: "";
    position: absolute;
    top: -7px;
    left: -5%;
    width: 110%;
    height: 14px;
    background: rgba(255,255,255,0.45);
    border-radius: 50%;
}

.bebedero-etiqueta {
    position: absolute;
    z-index: 3;
    top: 12px;
    left: 0;
    width: 100%;
    text-align: center;
    color: #17472D;
    font-size: 12px;
    font-weight: 900;
    letter-spacing: 2px;
}

.bebedero-porcentaje {
    position: absolute;
    z-index: 4;
    top: 50%;
    left: 0;
    width: 100%;
    transform: translateY(-50%);
    text-align: center;
    color: #17472D;
    font-size: 32px;
    font-weight: 900;
    text-shadow: 0 1px 4px rgba(255,255,255,0.9);
}

.bebedero-marcas {
    position: absolute;
    z-index: 2;
    top: 0;
    right: 12px;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-around;
}

.bebedero-marca {
    width: 13px;
    height: 2px;
    background: rgba(23,71,45,0.65);
}

.bebedero-base {
    width: 185px;
    height: 12px;
    margin: 0 auto;
    background: #17472D;
    border-radius: 0 0 12px 12px;
}

.bebedero-pie {
    text-align: center;
    color: #55745D;
    font-size: 13px;
    font-weight: 600;
    margin-top: 13px;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# 3. ESTADOS DE LA APLICACIÓN
# =========================================================

if "respuesta" not in st.session_state:
    st.session_state.respuesta = (
        "Hola. Soy GranjaConecta. Puedo controlar "
        "el bebedero y consultar el nivel de agua."
    )

if "texto_reconocido" not in st.session_state:
    st.session_state.texto_reconocido = ""

if "ultimo_audio" not in st.session_state:
    st.session_state.ultimo_audio = None

if "historial" not in st.session_state:
    st.session_state.historial = []

if "audio_respuesta" not in st.session_state:
    st.session_state.audio_respuesta = None


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
        "lock": Lock()
    }

    def al_conectar(
        client,
        userdata,
        flags,
        reason_code,
        properties
    ):

        if reason_code == 0:

            with estado["lock"]:
                estado["conectado"] = True

            client.subscribe(TOPIC)

            print("GranjaConecta conectado a MQTT")

        else:

            with estado["lock"]:
                estado["conectado"] = False

            print("Error MQTT:", reason_code)

    def al_desconectar(
        client,
        userdata,
        disconnect_flags,
        reason_code,
        properties
    ):

        with estado["lock"]:
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

                print("Respuesta del ESP32:", mensaje)

        except Exception as error:

            print("Error al recibir MQTT:", error)

    cliente = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=(
            "GranjaConecta_Bebedero_"
            + uuid.uuid4().hex[:8]
        )
    )

    cliente.on_connect = al_conectar
    cliente.on_disconnect = al_desconectar
    cliente.on_message = al_recibir

    try:

        cliente.connect(
            BROKER,
            PORT,
            60
        )

        cliente.loop_start()

    except Exception as error:

        print("Error de conexión MQTT:", error)

    return cliente, estado


cliente, mqtt_estado = crear_conexion_mqtt()


# =========================================================
# 5. FUNCIONES MQTT
# =========================================================

def mqtt_conectado():

    with mqtt_estado["lock"]:
        return mqtt_estado["conectado"]


def enviar_comando(comando):

    if not mqtt_conectado():
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

        return (
            resultado.rc == mqtt.MQTT_ERR_SUCCESS
        )

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
        valor = 0.0

    return max(0.0, min(100.0, valor))


def obtener_distancia():

    datos = obtener_datos()

    try:
        return float(datos.get("distancia", 0))
    except (ValueError, TypeError):
        return 0.0


def obtener_valvula():

    datos = obtener_datos()

    valor = str(
        datos.get("valvula", "cerrada")
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
            "true",
            "1",
            "si",
            "sí"
        ]

    return bool(valor)


def lectura_valida():

    valor = obtener_datos().get(
        "lecturaAguaValida",
        False
    )

    if isinstance(valor, str):

        return valor.lower() in [
            "true",
            "1",
            "si",
            "sí"
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
        caracter
        for caracter in texto
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
# 7. INTERPRETAR ÓRDENES
# =========================================================

def interpretar(texto):

    texto = normalizar(texto)

    # CERRAR VÁLVULA
    if any(frase in texto for frase in [
        "cierra la valvula",
        "cierra valvula",
        "cerrar la valvula",
        "cierrala",
        "cierra el paso del agua"
    ]):

        return "VALVULA_CERRAR"

    # VACIAR BEBEDERO
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

    # LLENAR HASTA EL 90 %
    if any(frase in texto for frase in [
        "dejala llena",
        "dejalo lleno",
        "deja el bebedero lleno",
        "llena completamente el bebedero",
        "llena el bebedero",
        "llenalo completamente"
    ]):

        return "BEBEDERO_LLENO"

    # ABRIR VÁLVULA
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

    # CONSULTAR DISTANCIA
    if any(frase in pregunta for frase in [
        "distancia",
        "cuantos centimetros",
        "cuantos cm",
        "sensor ultrasonico",
        "sensor de distancia"
    ]):

        if distancia <= 0:

            return (
                "El sensor HC-SR04 todavía no proporciona "
                "una distancia válida."
            )

        return (
            f"El sensor HC-SR04 registra una distancia "
            f"de {distancia:.1f} centímetros."
        )

    # CONSULTAR VÁLVULA
    if (
        "valvula" in pregunta
        and (
            "estado" in pregunta
            or "abierta" in pregunta
            or "cerrada" in pregunta
        )
    ):

        return (
            f"La válvula se encuentra actualmente "
            f"{obtener_valvula()}."
        )

    # CONSULTAR NIVEL DE AGUA
    if any(frase in pregunta for frase in [
        "porcentaje",
        "cuanta agua",
        "nivel de agua",
        "cuanto tiene de agua",
        "como esta el bebedero",
        "cuanto esta lleno",
        "porcentaje de la valvula"
    ]):

        return (
            f"El bebedero tiene actualmente "
            f"{nivel:.0f}% de agua."
        )

    # CONSULTAR CUÁNDO LLENAR
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
                "El nivel es bajo. Debes volver a llenarlo ahora."
            )

        return (
            f"El bebedero tiene {nivel:.0f}% de agua. "
            f"Te recomiendo volver a llenarlo cuando llegue "
            f"al {NIVEL_BAJO}% o menos."
        )

    return (
        "No reconocí esa solicitud. Puedes pedirme que abra "
        "o cierre la válvula, que vacíe el bebedero, "
        "que lo deje lleno, o consultar el porcentaje "
        "de agua, la distancia y cuándo volver a llenarlo."
    )


# =========================================================
# 9. PROCESAR MENSAJES
# =========================================================

def procesar_mensaje(texto):

    if not texto or not texto.strip():
        return

    st.session_state.audio_respuesta = None

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
    "Da órdenes por voz o texto y consulta "
    "el nivel de agua de tus gallinas."
)

if mqtt_conectado():

    st.success(
        "🟢 Conexión MQTT activa con el ESP32."
    )

else:

    st.error(
        "🔴 Sin conexión MQTT con el ESP32."
    )


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

    altura = max(
        0,
        min(100, nivel)
    )

    columna_dibujo, columna_datos = st.columns(
        [1.1, 1],
        gap="large"
    )

    # ---------------------------------------------
    # DIBUJO DEL BEBEDERO
    # ---------------------------------------------

    with columna_dibujo:

        st.markdown(
            "### 🐔 Bebedero de las gallinas"
        )

        st.caption(
            "Representación visual del nivel de agua"
        )

        dibujo = f"""
        <div class="bebedero-zona">
            <div>
                <div class="bebedero-estructura">

                    <div class="bebedero-etiqueta">
                        NIVEL DE AGUA
                    </div>

                    <div class="bebedero-marcas">
                        <div class="bebedero-marca"></div>
                        <div class="bebedero-marca"></div>
                        <div class="bebedero-marca"></div>
                        <div class="bebedero-marca"></div>
                        <div class="bebedero-marca"></div>
                    </div>

                    <div
                        class="bebedero-agua"
                        style="height:{altura:.1f}%;">
                    </div>

                    <div class="bebedero-porcentaje">
                        {nivel:.0f}%
                    </div>

                </div>

                <div class="bebedero-base"></div>

                <div class="bebedero-pie">
                    Nivel actual del bebedero
                </div>
            </div>
        </div>
        """

        st.markdown(
            dibujo,
            unsafe_allow_html=True
        )

    # ---------------------------------------------
    # PANEL DE INFORMACIÓN
    # ---------------------------------------------

    with columna_datos:

        st.markdown(
            "### 📊 Panel de monitoreo"
        )

        st.markdown(
            '<div class="panel-titulo">💧 NIVEL DE AGUA</div>',
            unsafe_allow_html=True
        )

        st.metric(
            "Porcentaje actual",
            f"{nivel:.0f}%"
        )

        st.progress(
            altura / 100,
            text=f"{nivel:.0f}% de llenado"
        )

        st.markdown(
            '<div class="panel-titulo">📡 SENSOR HC-SR04</div>',
            unsafe_allow_html=True
        )

        if distancia > 0:

            st.metric(
                "Distancia registrada",
                f"{distancia:.1f} cm"
            )

        else:

            st.metric(
                "Distancia registrada",
                "Sin lectura"
            )

        st.markdown(
            '<div class="panel-titulo">⚙️ ESTADO DE LA VÁLVULA</div>',
            unsafe_allow_html=True
        )

        if valvula == "abierta":

            st.success(
                "🟢 Válvula abierta"
            )

        else:

            st.error(
                "🔴 Válvula cerrada"
            )

        st.markdown(
            '<div class="panel-titulo">🔄 PROCESO DEL BEBEDERO</div>',
            unsafe_allow_html=True
        )

        if vaciando:

            st.warning(
                "💧 Vaciando el bebedero"
            )

        elif valvula == "abierta":

            st.success(
                "💧 Llenando el bebedero"
            )

        else:

            st.info(
                "⏸️ Proceso detenido"
            )

        # -----------------------------------------
        # AVISOS DEL NIVEL
        # -----------------------------------------

        if not valida:

            st.warning(
                "Esperando los datos del ESP32."
            )

        elif nivel <= NIVEL_BAJO:

            st.warning(
                "⚠️ Nivel bajo. Es necesario rellenar el bebedero."
            )

        elif nivel >= NIVEL_MAXIMO:

            st.success(
                "✅ Nivel máximo alcanzado."
            )

        else:

            st.success(
                "✅ El nivel de agua es suficiente."
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

    st.markdown(
        "**🗣️ Lo que dijiste:**"
    )

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

        procesar_mensaje(
            texto_usuario
        )


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

    audio_generado = generar_audio(
        st.session_state.respuesta
    )

    if audio_generado:

        st.session_state.audio_respuesta = audio_generado


if st.session_state.audio_respuesta:

    st.audio(
        st.session_state.audio_respuesta,
        format="audio/mpeg"
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
