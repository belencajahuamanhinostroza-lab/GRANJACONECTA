
import streamlit as st
import paho.mqtt.client as mqtt
import json
import io
import re
import unicodedata
import uuid
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

# Distancia medida desde el sensor hasta el agua
DISTANCIA_MINIMA = 10.0
DISTANCIA_MAXIMA = 30.0


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
            "distancia": 30,
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
        client,
        userdata,
        flags,
        reason_code,
        properties
    ):

        if reason_code == 0:

            estado["conectado"] = True

            client.subscribe(TOPIC)

            print("GranjaConecta conectado a MQTT")

        else:

            estado["conectado"] = False

            print("Error al conectar MQTT:", reason_code)

    def al_desconectar(
        client,
        userdata,
        disconnect_flags,
        reason_code,
        properties
    ):

        estado["conectado"] = False

        print("Desconectado de MQTT:", reason_code)

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

            print("Error al recibir MQTT:", error)

    cliente = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="GranjaConecta_Bebedero_" + uuid.uuid4().hex[:8]
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


# =========================================================
# 6. OBTENER DISTANCIA
# =========================================================

def obtener_distancia():

    datos = obtener_datos()

    valor = datos.get("distancia", 30)

    try:

        valor = float(valor)

    except (ValueError, TypeError):

        valor = 30.0

    # Se permite bajar de 10 cm para detectar
    # una posible condición de rebosamiento.

    return max(0.0, min(30.0, valor))


# =========================================================
# 7. ESTADOS DE LA VÁLVULA Y LECTURAS
# =========================================================

def obtener_valvula():

    datos = obtener_datos()

    valor = str(
        datos.get("valvula", "cerrada")
    ).lower()

    if "abier" in valor or valor == "open":

        return "abierta"

    return "cerrada"


def convertir_booleano(valor):

    if isinstance(valor, str):

        return valor.lower() in [
            "true",
            "1",
            "si",
            "sí",
            "verdadero"
        ]

    return bool(valor)


def esta_vaciando():

    valor = obtener_datos().get(
        "vaciando",
        False
    )

    return convertir_booleano(valor)


def lectura_valida():

    valor = obtener_datos().get(
        "lecturaAguaValida",
        False
    )

    return convertir_booleano(valor)


# =========================================================
# 8. CALCULAR ALTURA VISUAL DEL AGUA
# =========================================================

def obtener_altura_agua(distancia):

    # 30 cm = bebedero visualmente vacío
    # 10 cm = bebedero visualmente lleno

    altura = (
        (DISTANCIA_MAXIMA - distancia)
        /
        (DISTANCIA_MAXIMA - DISTANCIA_MINIMA)
    ) * 100

    return max(0.0, min(100.0, altura))


# =========================================================
# 9. ESTADO DEL AGUA
# =========================================================

def obtener_estado_agua(distancia):

    if distancia < 10:

        return "POSIBLE REBOSAMIENTO"

    elif distancia == 10:

        return "LLENO"

    elif distancia > 25:

        return "NIVEL BAJO"

    else:

        return "NORMAL"


# =========================================================
# 10. NORMALIZAR TEXTO
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
# 11. INTERPRETAR ÓRDENES
# =========================================================

def interpretar(texto):

    texto = normalizar(texto)

    # CERRAR VÁLVULA

    if any(frase in texto for frase in [
        "cierra la valvula",
        "cierra valvula",
        "cerrar la valvula",
        "cierrala",
        "deten el llenado",
        "detener llenado",
        "para el llenado"
    ]):

        return "VALVULA_CERRAR"

    # VACIAR BEBEDERO

    if any(frase in texto for frase in [
        "vacia la valvula",
        "vaciar la valvula",
        "vacia el bebedero",
        "vaciar el bebedero",
        "vacia el agua",
        "vaciar el agua"
    ]):

        return "BEBEDERO_VACIAR"

    # LLENAR COMPLETAMENTE

    if any(frase in texto for frase in [
        "dejala llena",
        "dejalo lleno",
        "deja el bebedero lleno",
        "llena completamente el bebedero",
        "llena el bebedero completamente",
        "llenalo completamente",
        "llenala completamente"
    ]):

        return "BEBEDERO_LLENO"

    # ABRIR VÁLVULA

    if any(frase in texto for frase in [
        "abre la valvula",
        "abrir la valvula",
        "abre valvula",
        "abrir valvula",
        "comienza a llenar",
        "comenzar a llenar",
        "empieza a llenar"
    ]):

        return "VALVULA_ABRIR"

    return None


# =========================================================
# 12. RESPONDER CONSULTAS
# =========================================================

def responder(pregunta):

    pregunta = normalizar(pregunta)

    distancia = obtener_distancia()

    valvula = obtener_valvula()

    vaciando = esta_vaciando()

    valida = lectura_valida()

    estado = obtener_estado_agua(distancia)

    if not valida:

        return (
            "Todavía estoy esperando los datos del bebedero. "
            "Comprueba la conexión con el ESP32."
        )

    # CONSULTAR DISTANCIA

    if any(frase in pregunta for frase in [
        "distancia",
        "cuantos centimetros",
        "cuantos cm",
        "medicion del agua",
        "medida del agua"
    ]):

        return (
            f"La distancia entre el sensor y el agua "
            f"es de {distancia:.1f} centímetros. "
            f"El estado del bebedero es: {estado}."
        )

    # CONSULTAR NIVEL DE AGUA

    if any(frase in pregunta for frase in [
        "nivel de agua",
        "como esta el agua",
        "estado del agua",
        "cuanta agua tiene",
        "cuanta agua hay",
        "esta lleno",
        "esta vacio"
    ]):

        return (
            f"El bebedero presenta una distancia de "
            f"{distancia:.1f} centímetros entre el sensor "
            f"y la superficie del agua. "
            f"El nivel se encuentra en estado: {estado}."
        )

    # CONSULTAR VÁLVULA

    if any(frase in pregunta for frase in [
        "estado de la valvula",
        "valvula",
        "esta abierta",
        "esta cerrada"
    ]):

        return (
            f"La válvula está {valvula}."
        )

    # CONSULTAR LLENADO

    if any(frase in pregunta for frase in [
        "esta llenando",
        "esta vaciando",
        "que esta haciendo",
        "proceso actual"
    ]):

        if vaciando:

            return "El bebedero se está vaciando."

        elif valvula == "abierta":

            return "El bebedero se está llenando."

        else:

            return (
                "El bebedero está en espera. "
                "La válvula se encuentra cerrada."
            )

    # CUÁNDO LLENAR

    if any(frase in pregunta for frase in [
        "cuando debo llenarlo",
        "cuando debo volver a llenarlo",
        "cuando lo lleno de nuevo",
        "cuando hay que llenarlo",
        "necesita agua",
        "debo llenarlo"
    ]):

        if distancia >= 30:

            return (
                "El bebedero está prácticamente vacío. "
                "Debes llenarlo ahora."
            )

        elif distancia > 25:

            return (
                "El nivel de agua está bajo. "
                "Te recomiendo llenar el bebedero."
            )

        elif distancia <= 10:

            return (
                "El bebedero está lleno. "
                "No necesita más agua."
            )

        else:

            return (
                "El nivel de agua es normal. "
                "Puedes volver a llenarlo cuando "
                "la distancia supere los 25 centímetros."
            )

    return (
        "No reconocí esa consulta. Puedes preguntarme "
        "por la distancia del agua, el estado del bebedero, "
        "la válvula o cuándo debes volver a llenarlo."
    )


# =========================================================
# 13. PROCESAR MENSAJES
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
                "El llenado se detendrá."
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
# 14. ENCABEZADO
# =========================================================

st.title("🐔 GranjaConecta")

st.subheader("Control inteligente del bebedero")

st.write(
    "Da órdenes por voz o texto y consulta "
    "el nivel de agua de tus gallinas."
)

if mqtt_estado["conectado"]:

    st.success("🟢 Conexión MQTT activa.")

else:

    st.error("🔴 Sin conexión MQTT con el ESP32.")


# =========================================================
# 15. DIBUJO Y ESTADO DEL BEBEDERO
# =========================================================

@st.fragment(run_every="1s")
def mostrar_estado_bebedero():

    datos = obtener_datos()

    distancia = obtener_distancia()

    valvula = obtener_valvula()

    vaciando = esta_vaciando()

    valida = lectura_valida()

    altura = obtener_altura_agua(distancia)

    estado = obtener_estado_agua(distancia)

    columna_dibujo, columna_datos = st.columns([1.2, 1])

    # -----------------------------------------------------
    # DIBUJO DEL BEBEDERO
    # -----------------------------------------------------

    with columna_dibujo:

        st.markdown(
            "<h3 style='color:#17472D;'>🐔 Bebedero</h3>",
            unsafe_allow_html=True
        )

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
                    #238A80,
                    #75D6C0
                );
                transition:height 0.8s ease;
                z-index:1;
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
                {f"{distancia:.1f} cm" if valida else "-- cm"}
            </div>

        </div>
        """

        st.markdown(
            dibujo,
            unsafe_allow_html=True
        )

    # -----------------------------------------------------
    # INFORMACIÓN DEL BEBEDERO
    # -----------------------------------------------------

    with columna_datos:

        st.markdown(
            "<h3 style='color:#17472D;'>📏 Nivel de agua</h3>",
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
                "🚨 POSIBLE REBOSAMIENTO"
            )

        elif distancia == 10:

            st.success(
                "🟢 BEBEDERO LLENO"
            )

        elif distancia > 25:

            st.warning(
                "🟠 NIVEL BAJO. ES NECESARIO LLENAR."
            )

        else:

            st.success(
                "🟢 NIVEL NORMAL"
            )

        # -------------------------------------------------
        # VÁLVULA
        # -------------------------------------------------

        st.markdown(
            "<h3 style='color:#17472D;'>Estado de la válvula</h3>",
            unsafe_allow_html=True
        )

        if valvula == "abierta":

            st.success("🟢 VÁLVULA ABIERTA")

        else:

            st.error("🔴 VÁLVULA CERRADA")

        # -------------------------------------------------
        # PROCESO ACTUAL
        # -------------------------------------------------

        if vaciando:

            st.warning("💧 VACIANDO EL BEBEDERO")

        elif valvula == "abierta":

            st.success("💧 LLENANDO EL BEBEDERO")

        else:

            st.info("Bebedero en espera.")

        # -------------------------------------------------
        # SENSOR FÍSICO HC-SR04
        # -------------------------------------------------

        hc_valido = convertir_booleano(
            datos.get("lecturaHCValida", False)
        )

        distancia_hc = datos.get(
            "distanciaHC",
            0
        )

        if hc_valido:

            try:

                st.caption(
                    "Lectura física HC-SR04: "
                    f"{float(distancia_hc):.1f} cm"
                )

            except (ValueError, TypeError):

                pass


mostrar_estado_bebedero()


# =========================================================
# 16. CONTROL POR VOZ
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
# 17. CONTROL POR TEXTO
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
# 18. RESPUESTA DE GRANJACONECTA
# =========================================================

st.divider()

st.subheader("💬 Respuesta de GranjaConecta")

st.info(
    st.session_state.respuesta
)


# =========================================================
# 19. HISTORIAL
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
# 20. COMANDOS DISPONIBLES
# =========================================================

st.divider()

with st.expander("📢 Órdenes y preguntas disponibles"):

    st.markdown("""
    **Órdenes por voz o texto:**

    - Abre la válvula.
    - Cierra la válvula.
    - Vacía el bebedero.
    - Déjalo lleno.

    **Preguntas por voz o texto:**

    - ¿Cuál es la distancia del agua?
    - ¿Cómo está el nivel de agua?
    - ¿Está abierta la válvula?
    - ¿Está llenando el bebedero?
    - ¿Cuándo debo llenarlo de nuevo?
    """)
