
import streamlit as st
import paho.mqtt.client as mqtt
import json
import io
import re
import unicodedata
import uuid
import speech_recognition as sr
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder
from threading import Lock

# =========================================================
# CONFIGURACIÓN
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
# DISEÑO
# =========================================================

st.markdown("""
<style>
.stApp {
    background-color: #EDF5E9;
}

html, body, [class*="css"] {
    color: #17472D !important;
}

h1, h2, h3, h4, h5, p, label,
span, li, strong, small {
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
    color: #FFFFFF !important;
    border: 2px solid #17472D !important;
    border-radius: 12px !important;
    font-weight: bold !important;
    min-height: 43px;
}

.stButton > button p,
.stButton > button span,
.stFormSubmitButton > button p,
.stFormSubmitButton > button span {
    color: #FFFFFF !important;
}

.stButton > button:hover,
.stFormSubmitButton > button:hover {
    background-color: #28663F !important;
    border-color: #28663F !important;
}

.stTextInput input,
.stTextArea textarea {
    color: #17472D !important;
    background-color: #FFFFFF !important;
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

::-webkit-scrollbar-thumb:hover {
    background: #28663F;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# ESTADOS INICIALES
# =========================================================

if "historial" not in st.session_state:
    st.session_state.historial = []

if "respuesta" not in st.session_state:
    st.session_state.respuesta = (
        "Hola, soy GranjaConecta. Puedes preguntarme "
        "por el nivel de agua o darme una orden para la válvula."
    )

if "texto_reconocido" not in st.session_state:
    st.session_state.texto_reconocido = ""

if "ultimo_audio" not in st.session_state:
    st.session_state.ultimo_audio = None

if "ultimo_comando" not in st.session_state:
    st.session_state.ultimo_comando = ""

if "aviso_auto_cierre" not in st.session_state:
    st.session_state.aviso_auto_cierre = False

# =========================================================
# MQTT
# =========================================================

@st.cache_resource
def crear_conexion_mqtt():

    estado = {
        "datos": {
            "agua": 0,
            "nivelAgua": 0,
            "valvula": "cerrada",
            "lecturaAguaValida": False
        },
        "conectado": False,
        "ultimo_mensaje": "",
        "lock": Lock()
    }

    def al_conectar(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            estado["conectado"] = True
            client.subscribe(TOPIC)
        else:
            estado["conectado"] = False

    def al_desconectar(client, userdata, disconnect_flags, reason_code, properties):
        estado["conectado"] = False

    def al_recibir(client, userdata, msg):
        try:
            recibido = json.loads(msg.payload.decode("utf-8"))

            tipo = recibido.get("tipo", "")

            if tipo == "telemetria":
                nuevos_datos = recibido.get("datos", recibido)

                with estado["lock"]:
                    estado["datos"].update(nuevos_datos)
                    estado["ultimo_mensaje"] = "telemetria"

            elif tipo == "respuesta":
                estado["ultimo_mensaje"] = recibido.get(
                    "message", "Respuesta recibida"
                )

        except Exception as error:
            print("Error procesando MQTT:", error)

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
        estado["conectado"] = False
        print("Error MQTT:", error)

    return cliente, estado


cliente, mqtt_estado = crear_conexion_mqtt()


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


# =========================================================
# FUNCIONES DE DATOS
# =========================================================

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

    if "abier" in valor:
        return "abierta"

    return "cerrada"


def lectura_valida():

    datos = obtener_datos()

    return datos.get("lecturaAguaValida", False)


# =========================================================
# NORMALIZAR TEXTO
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

    texto = re.sub(r"\s+", " ", texto)

    return texto


# =========================================================
# INTERPRETACIÓN DE ÓRDENES
# =========================================================

def interpretar(texto):

    texto = normalizar(texto)

    ordenes_abrir = [
        "abre la valvula",
        "abrir la valvula",
        "abre valvula",
        "llena el bebedero",
        "llenar el bebedero",
        "empieza a llenar",
        "comienza a llenar",
        "inicia el llenado",
        "quiero llenar el bebedero",
        "abre el agua",
        "deja entrar agua",
        "comienza el llenado"
    ]

    ordenes_cerrar = [
        "cierra la valvula",
        "cerrar la valvula",
        "cierra valvula",
        "deten el llenado",
        "detener el llenado",
        "para de llenar",
        "deja de llenar",
        "cierra el agua",
        "deten la valvula",
        "para el llenado",
        "deja de echar agua",
        "no llenes mas"
    ]

    if any(frase in texto for frase in ordenes_abrir):
        return "VALVULA_ABRIR"

    if any(frase in texto for frase in ordenes_cerrar):
        return "VALVULA_CERRAR"

    return None


# =========================================================
# RESPUESTAS A PREGUNTAS
# =========================================================

def responder(pregunta):

    pregunta = normalizar(pregunta)

    nivel = obtener_nivel()
    valvula = obtener_valvula()

    if not lectura_valida():
        return (
            "Todavía no tengo una lectura válida del sensor "
            "de agua. Comprueba la conexión con el ESP32."
        )

    if "cuanta agua" in pregunta or "nivel de agua" in pregunta:
        return f"El bebedero tiene un {nivel:.0f}% de agua."

    if "cuanto falta" in pregunta:
        restante = max(0, 100 - nivel)
        return (
            f"Falta un {restante:.0f}% para completar "
            "la capacidad del bebedero."
        )

    if "lleno" in pregunta or "nivel maximo" in pregunta:

        if nivel >= NIVEL_MAXIMO:
            return (
                "El bebedero alcanzó el nivel máximo. "
                "La válvula debe permanecer cerrada."
            )

        return (
            f"El bebedero tiene un {nivel:.0f}% de agua. "
            "Todavía no ha alcanzado el nivel máximo."
        )

    if "vacio" in pregunta:

        if nivel <= NIVEL_BAJO:
            return (
                "El nivel de agua es muy bajo. "
                "El bebedero necesita llenarse."
            )

        return (
            f"El bebedero no está vacío. "
            f"Tiene un {nivel:.0f}% de agua."
        )

    if "valvula" in pregunta:
        return f"La válvula está {valvula}."

    if "necesita agua" in pregunta:

        if nivel <= NIVEL_BAJO:
            return "Sí, el bebedero necesita agua."

        return "No, el nivel de agua es suficiente por ahora."

    if "debo cerrar" in pregunta:

        if nivel >= NIVEL_MAXIMO:
            return (
                "Sí. El bebedero alcanzó el nivel máximo. "
                "La válvula debe estar cerrada."
            )

        return (
            "Todavía no se ha alcanzado el nivel máximo. "
            f"El bebedero tiene un {nivel:.0f}% de agua."
        )

    if "como esta" in pregunta or "estado del bebedero" in pregunta:
        return (
            f"El bebedero tiene un {nivel:.0f}% de agua "
            f"y la válvula está {valvula}."
        )

    return (
        "No entendí la pregunta. Puedes preguntarme "
        "por el nivel de agua, el llenado o el estado de la válvula."
    )


# =========================================================
# PROCESAR MENSAJES
# =========================================================

def procesar_mensaje(texto):

    if not texto.strip():
        return

    st.session_state.historial.append({
        "tipo": "usuario",
        "texto": texto
    })

    comando = interpretar(texto)
    nivel = obtener_nivel()

    if comando == "VALVULA_ABRIR":

        if not lectura_valida():
            respuesta = (
                "No puedo abrir la válvula porque todavía "
                "no tengo una lectura válida del sensor."
            )

        elif nivel >= NIVEL_MAXIMO:
            respuesta = (
                "No puedo abrir la válvula. "
                "El bebedero ya alcanzó el nivel máximo."
            )

        elif enviar_comando(comando):
            respuesta = (
                "He enviado la orden para abrir la válvula. "
                "Estoy esperando que el ESP32 confirme el cambio."
            )
            st.session_state.ultimo_comando = comando

        else:
            respuesta = (
                "No pude enviar la orden. "
                "Comprueba la conexión con el ESP32."
            )

    elif comando == "VALVULA_CERRAR":

        if enviar_comando(comando):
            respuesta = (
                "He enviado la orden para cerrar la válvula. "
                "Estoy esperando la confirmación del ESP32."
            )
            st.session_state.ultimo_comando = comando

        else:
            respuesta = (
                "No pude enviar la orden. "
                "Comprueba la conexión con el ESP32."
            )

    else:
        respuesta = responder(texto)

    st.session_state.respuesta = respuesta

    st.session_state.historial.append({
        "tipo": "granja",
        "texto": respuesta
    })


# =========================================================
# GENERAR RESPUESTA DE VOZ
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
        st.error(f"No se pudo generar la voz: {error}")
        return None


# =========================================================
# ENCABEZADO
# =========================================================

st.title("🐔 GranjaConecta")
st.subheader("Asistente inteligente del bebedero")

st.write(
    "Habla o escribe para consultar el agua y controlar "
    "la válvula del bebedero."
)

st.divider()


# =========================================================
# ESTADO DE CONEXIÓN
# =========================================================

if mqtt_estado["conectado"]:
    st.success("Conexión MQTT activa.")
else:
    st.error(
        "No hay conexión MQTT. Comprueba el broker y el ESP32."
    )


# =========================================================
# DIBUJO Y TELEMETRÍA EN TIEMPO REAL
# =========================================================

@st.fragment(run_every="2s")
def mostrar_bebedero():

    nivel = obtener_nivel()
    valvula = obtener_valvula()
    valida = lectura_valida()

    # Protección adicional desde la aplicación.
    # El ESP32 también debe tener su propio cierre automático.

    if nivel >= NIVEL_MAXIMO and valvula == "abierta":

        if not st.session_state.aviso_auto_cierre:

            enviado = enviar_comando("VALVULA_CERRAR")

            if enviado:
                st.session_state.aviso_auto_cierre = True

    elif nivel < NIVEL_MAXIMO:
        st.session_state.aviso_auto_cierre = False

    st.subheader("🐔 Estado del bebedero")

    if not valida:
        st.warning(
            "Esperando una lectura válida del sensor ultrasónico."
        )

    elif nivel <= NIVEL_BAJO:
        st.warning(
            "Nivel bajo: el bebedero necesita agua."
        )

    elif nivel >= NIVEL_MAXIMO:
        st.error(
            "¡Nivel máximo! La válvula debe permanecer cerrada."
        )

    else:
        st.success(
            "El nivel de agua se encuentra dentro del rango normal."
        )

    columna_dibujo, columna_datos = st.columns([1.2, 1])

    # -----------------------------------------------------
    # DIBUJO DEL BEBEDERO
    # -----------------------------------------------------

    with columna_dibujo:

        estado_valvula = (
            "ABIERTA" if valvula == "abierta" else "CERRADA"
        )

        color_estado = (
            "#238A4B" if valvula == "abierta" else "#17472D"
        )

        altura = max(0, min(100, nivel))

        dibujo = f"""
        <div style="
            background:#DCEBD8;
            border:3px solid #17472D;
            border-radius:22px;
            padding:22px;
            text-align:center;
            width:100%;
            box-sizing:border-box;
        ">

            <h3 style="
                color:#17472D;
                margin:0 0 18px 0;
            ">
                🐔 Nivel de agua
            </h3>

            <div style="
                width:190px;
                height:230px;
                margin:10px auto;
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
                    transition:height 0.6s ease;
                ">
                </div>

            </div>

            <p style="
                color:#17472D;
                font-size:21px;
                font-weight:bold;
                margin:15px 0 5px 0;
            ">
                Bebedero
            </p>

            <p style="
                color:{color_estado};
                font-size:17px;
                font-weight:bold;
                margin:0;
            ">
                Válvula: {estado_valvula}
            </p>

        </div>
        """

        st.markdown(
            dibujo,
            unsafe_allow_html=True
        )

    # -----------------------------------------------------
    # LECTURAS DEL SISTEMA
    # -----------------------------------------------------

    with columna_datos:

        st.subheader("📊 Lecturas del sistema")

        st.metric(
            "Nivel de agua",
            f"{nivel:.0f}%"
        )

        st.progress(
            int(nivel),
            text=f"{nivel:.0f}% de llenado"
        )

        st.metric(
            "Estado de la válvula",
            valvula.capitalize()
        )

        if valida:
            st.caption(
                "Lectura recibida desde el sensor ultrasónico."
            )
        else:
            st.caption(
                "Sin lectura válida del sensor."
            )


mostrar_bebedero()

st.divider()


# =========================================================
# ASISTENTE DE VOZ
# =========================================================

st.subheader("🎙️ Habla con GranjaConecta")

st.write(
    "Pulsa el micrófono, di tu orden o pregunta y termina "
    "la grabación. La aplicación transcribirá y procesará "
    "lo que dijiste."
)

audio_voz = mic_recorder(
    start_prompt="🎙️ Hablar",
    stop_prompt="⏹️ Terminar",
    just_once=True,
    key="microfono_bebedero"
)

if audio_voz and audio_voz.get("bytes"):

    identificador = audio_voz.get("id")

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

            # Ejecutar automáticamente lo reconocido.
            procesar_mensaje(texto)

            st.success(
                "Tu mensaje fue reconocido y procesado."
            )

        except sr.UnknownValueError:

            st.warning(
                "No pude entender lo que dijiste. "
                "Habla un poco más cerca del micrófono."
            )

        except sr.RequestError:

            st.error(
                "No se pudo conectar con el servicio de "
                "reconocimiento de voz."
            )

        except Exception as error:

            st.error(
                f"No se pudo procesar el audio: {error}"
            )


if st.session_state.texto_reconocido:

    st.markdown("**🗣️ Esto fue lo que dijiste:**")

    st.info(
        st.session_state.texto_reconocido
    )


st.divider()


# =========================================================
# ASISTENTE DE TEXTO
# =========================================================

st.subheader("⌨️ También puedes escribir")

with st.form("formulario_mensaje", clear_on_submit=True):

    texto_usuario = st.text_input(
        "Escribe una pregunta u orden",
        placeholder="Ejemplo: Abre la válvula del bebedero"
    )

    enviar = st.form_submit_button(
        "Enviar mensaje",
        use_container_width=True
    )

    if enviar and texto_usuario.strip():

        procesar_mensaje(texto_usuario)

        st.rerun()


st.divider()


# =========================================================
# RESPUESTA DE LA GRANJA
# =========================================================

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


st.divider()


# =========================================================
# HISTORIAL
# =========================================================

st.subheader("📝 Conversación")

if not st.session_state.historial:
    st.caption("Todavía no hay mensajes.")

for mensaje in st.session_state.historial[-12:]:

    if mensaje["tipo"] == "usuario":

        st.markdown(
            f"**🧑 Tú:** {mensaje['texto']}"
        )

    else:

        st.markdown(
            f"**🐔 GranjaConecta:** {mensaje['texto']}"
        )


# =========================================================
# LISTA DE ÓRDENES Y PREGUNTAS
# =========================================================

st.divider()

with st.expander("📢 Ver todas las órdenes disponibles"):

    st.markdown("""
    **Órdenes para abrir la válvula:**

    - Abre la válvula.
    - Abrir la válvula.
    - Llena el bebedero.
    - Empieza a llenar.
    - Comienza a llenar.
    - Inicia el llenado.
    - Quiero llenar el bebedero.
    - Abre el agua.

    **Órdenes para cerrar la válvula:**

    - Cierra la válvula.
    - Cerrar la válvula.
    - Detén el llenado.
    - Para de llenar.
    - Deja de llenar.
    - Cierra el agua.
    - Deja de echar agua.
    - No llenes más.
    """)


with st.expander("❓ Ver preguntas que puedes hacer"):

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
