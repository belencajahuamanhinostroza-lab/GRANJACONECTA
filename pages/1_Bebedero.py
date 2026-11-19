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
        "Puedes preguntarme por el nivel de agua "
        "o darme una orden."
    )

if "texto_reconocido" not in st.session_state:
    st.session_state.texto_reconocido = ""

if "ultimo_audio" not in st.session_state:
    st.session_state.ultimo_audio = None

if "historial" not in st.session_state:
    st.session_state.historial = []

if "mensaje_stop" not in st.session_state:
    st.session_state.mensaje_stop = False


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
            print("Conectado a MQTT")
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
        client_id="GranjaConecta_Bebedero_" + uuid.uuid4().hex[:6]
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
        print("Error enviando comando:", error)
        return False


def obtener_datos():

    with mqtt_estado["lock"]:
        return dict(mqtt_estado["datos"])


def obtener_nivel():

    datos = obtener_datos()

    valor = datos.get("nivelAgua")

    if valor is None:
        valor = datos.get("agua", 0)

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


def lectura_valida():

    datos = obtener_datos()

    valor = datos.get(
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

    return re.sub(r"\s+", " ", texto)


# =========================================================
# 7. IDENTIFICAR ÓRDENES
# =========================================================

def interpretar(texto):

    texto = normalizar(texto)

    ordenes_cerrar = [
        "stop",
        "alto",
        "deten el llenado",
        "detener el llenado",
        "para de llenar",
        "deja de llenar",
        "cierra la valvula",
        "cerrar la valvula",
        "cierra valvula",
        "deten la valvula",
        "para el llenado",
        "deja de echar agua",
        "no llenes mas",
        "para el agua",
        "deten el agua",
        "detener el agua"
    ]

    ordenes_abrir = [
        "abre la valvula",
        "abrir la valvula",
        "abre valvula",
        "abrir valvula",
        "llena el bebedero",
        "llenar el bebedero",
        "empieza a llenar",
        "comienza a llenar",
        "inicia el llenado",
        "quiero llenar el bebedero",
        "abre el agua",
        "deja entrar agua",
        "comienza el llenado",
        "iniciar llenado",
        "abre el bebedero"
    ]

    if any(frase in texto for frase in ordenes_cerrar):
        return "VALVULA_CERRAR"

    if any(frase in texto for frase in ordenes_abrir):
        return "VALVULA_ABRIR"

    return None


# =========================================================
# 8. RESPONDER PREGUNTAS
# =========================================================

def responder(pregunta):

    pregunta = normalizar(pregunta)

    nivel = obtener_nivel()
    valvula = obtener_valvula()
    valida = lectura_valida()

    if "valvula" in pregunta:
        return f"La válvula está {valvula}."

    if not valida:
        return (
            "Todavía no tengo una lectura válida del sensor "
            "de agua. Comprueba la conexión con el ESP32."
        )

    if "cuanta agua" in pregunta or "nivel de agua" in pregunta:
        return f"El bebedero tiene un {nivel:.0f}% de agua."

    if "cuanto falta" in pregunta:
        restante = max(0, 100 - nivel)
        return f"Falta un {restante:.0f}% para completar el bebedero."

    if "lleno" in pregunta or "nivel maximo" in pregunta:
        if nivel >= NIVEL_MAXIMO:
            return "El bebedero alcanzó el nivel máximo."
        return f"El bebedero tiene {nivel:.0f}% de agua y todavía puede llenarse."

    if "vacio" in pregunta:
        if nivel <= NIVEL_BAJO:
            return "El nivel de agua está bajo. El bebedero necesita llenarse."
        return f"El bebedero no está vacío. Tiene {nivel:.0f}% de agua."

    if "necesita agua" in pregunta:
        if nivel <= NIVEL_BAJO:
            return "Sí. El bebedero necesita agua."
        return "No. El nivel de agua es suficiente por ahora."

    if "debo cerrar" in pregunta:
        if nivel >= NIVEL_MAXIMO:
            return "Sí. El nivel máximo fue alcanzado. La válvula debe estar cerrada."
        return f"El bebedero tiene {nivel:.0f}% de agua. Todavía no alcanzó el nivel máximo."

    if "como esta" in pregunta or "estado del bebedero" in pregunta:
        return (
            f"El bebedero tiene {nivel:.0f}% de agua "
            f"y la válvula está {valvula}."
        )

    return (
        "No entendí la pregunta. Puedes preguntarme "
        "cuánta agua tiene, si está lleno o cómo está la válvula."
    )


# =========================================================
# 9. PROCESAR MENSAJES
# =========================================================

def procesar_mensaje(texto):

    if not texto or not texto.strip():
        return

    st.session_state.historial.append(("Tú", texto))

    comando = interpretar(texto)
    nivel = obtener_nivel()

    if comando == "VALVULA_ABRIR":

        if not lectura_valida():
            respuesta = (
                "No puedo abrir la válvula porque no tengo "
                "una lectura válida del sensor."
            )

        elif nivel >= NIVEL_MAXIMO:
            respuesta = (
                "No puedo abrir la válvula. "
                "El bebedero ya alcanzó el nivel máximo."
            )

        elif enviar_comando(comando):
            respuesta = (
                "Orden enviada. Estoy abriendo la válvula "
                "para comenzar a llenar el bebedero."
            )
            st.session_state.mensaje_stop = False

        else:
            respuesta = (
                "No pude enviar la orden. "
                "Comprueba la conexión MQTT."
            )

    elif comando == "VALVULA_CERRAR":

        if enviar_comando(comando):
            respuesta = (
                "STOP: llenado detenido. "
                "Orden de cierre enviada."
            )
            st.session_state.mensaje_stop = True

        else:
            respuesta = (
                "No pude detener el llenado porque "
                "no hay conexión MQTT."
            )

    else:
        respuesta = responder(texto)

    st.session_state.respuesta = respuesta
    st.session_state.historial.append(
        ("GranjaConecta", respuesta)
    )


# =========================================================
# 10. AUDIO DE RESPUESTA
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
        st.error(f"No se pudo generar el audio: {error}")
        return None


# =========================================================
# 11. ENCABEZADO
# =========================================================

st.title("🐔 GranjaConecta")

st.subheader("Control inteligente del bebedero")

st.write(
    "Da órdenes por voz o escribe preguntas para conocer "
    "el nivel de agua y controlar el llenado."
)

if mqtt_estado["conectado"]:
    st.success("Conexión MQTT activa.")
else:
    st.error("Sin conexión MQTT con el ESP32.")


# =========================================================
# 12. DIBUJO Y ESTADO DEL BEBEDERO
# =========================================================

@st.fragment(run_every="2s")
def mostrar_estado_bebedero():

    nivel = obtener_nivel()
    valvula = obtener_valvula()
    valida = lectura_valida()

    columna_dibujo, columna_datos = st.columns([1.2, 1])

    # COLUMNA IZQUIERDA: BEBEDERO

    with columna_dibujo:

        st.markdown(
            "<h3 style='color:#17472D;'>🐔 Bebedero</h3>",
            unsafe_allow_html=True
        )

        altura = int(nivel)

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
                    #329B91,
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

    # COLUMNA DERECHA: DATOS

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
            nivel / 100,
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

        if not valida:
            st.warning("Esperando lectura válida del sensor.")

        elif nivel <= NIVEL_BAJO:
            st.warning("Nivel bajo de agua.")

        elif nivel >= NIVEL_MAXIMO:
            st.error("Nivel máximo alcanzado.")

        else:
            st.success("Nivel de agua normal.")

        if st.session_state.mensaje_stop:
            st.warning("STOP: llenado detenido.")

        elif valvula == "abierta":
            st.success("Estado de operación: LLENANDO")

        else:
            st.info("Estado de operación: EN ESPERA")


mostrar_estado_bebedero()


# =========================================================
# 13. CONTROL POR MICRÓFONO
# =========================================================

st.divider()

st.subheader("🎙️ Habla con GranjaConecta")

st.write(
    "Pulsa el micrófono, di una orden o formula una pregunta. "
    "Al terminar la grabación, el mensaje se procesará automáticamente."
)

audio_voz = mic_recorder(
    start_prompt="🎙️ Hablar",
    stop_prompt="⏹️ Terminar",
    just_once=True,
    key="microfono_bebedero"
)

if audio_voz and audio_voz.get("bytes"):

    identificador = audio_voz.get("id")

    if identificador is None:
        identificador = hashlib.md5(
            audio_voz["bytes"]
        ).hexdigest()

    if identificador != st.session_state.ultimo_audio:

        st.session_state.ultimo_audio = identificador

        try:
            reconocedor = sr.Recognizer()

            with sr.AudioFile(
                io.BytesIO(audio_voz["bytes"])
            ) as fuente:
                audio = reconocedor.record(fuente)

            texto = reconocedor.recognize_google(
                audio,
                language="es-ES"
            )

            st.session_state.texto_reconocido = texto
            procesar_mensaje(texto)

            st.success("Mensaje reconocido y procesado.")

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
            st.error(f"Error al procesar el audio: {error}")


if st.session_state.texto_reconocido:
    st.markdown("**🗣️ Lo que dijiste:**")
    st.info(st.session_state.texto_reconocido)


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
        placeholder="Ejemplo: Llena el bebedero o ¿cuánta agua tiene?"
    )

    enviar = st.form_submit_button(
        "Enviar",
        use_container_width=True
    )

    if enviar and texto_usuario.strip():
        procesar_mensaje(texto_usuario)


# =========================================================
# 15. RESPUESTA
# =========================================================

st.divider()

st.subheader("💬 Respuesta de GranjaConecta")

st.info(st.session_state.respuesta)

if st.button(
    "🔊 Escuchar respuesta",
    use_container_width=True
):

    audio = generar_audio(st.session_state.respuesta)

    if audio:
        st.audio(audio, format="audio/mp3")


# =========================================================
# 16. HISTORIAL
# =========================================================

st.divider()

st.subheader("📝 Conversación")

if not st.session_state.historial:
    st.caption("Todavía no hay mensajes.")

for remitente, mensaje in st.session_state.historial[-10:]:

    if remitente == "Tú":
        st.markdown(f"**🧑 Tú:** {mensaje}")
    else:
        st.markdown(f"**🐔 GranjaConecta:** {mensaje}")


# =========================================================
# 17. ÓRDENES DISPONIBLES
# =========================================================

st.divider()

with st.expander("📢 Órdenes que puedes decir"):

    st.markdown("""
    **Para abrir y llenar:**

    - Abre la válvula.
    - Llena el bebedero.
    - Empieza a llenar.
    - Comienza el llenado.
    - Abre el agua.

    **Para detener y cerrar:**

    - STOP.
    - Detén el llenado.
    - Para de llenar.
    - Cierra la válvula.
    - Deja de llenar.
    - Detén el agua.
    """)


with st.expander("❓ Preguntas que puedes hacer"):

    st.markdown("""
    - ¿Cuánta agua tiene el bebedero?
    - ¿Cuál es el nivel de agua?
    - ¿Cuánto falta para llenarse?
    - ¿Está lleno el bebedero?
    - ¿Está vacío?
    - ¿La válvula está abierta?
    - ¿La válvula está cerrada?
    - ¿Necesita agua?
    - ¿El agua está en el nivel máximo?
    - ¿Debo cerrar la válvula?
    - ¿Cómo está el bebedero?
    """)
