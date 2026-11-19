
import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import re
import io
import speech_recognition as sr
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder

# --------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------

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

# --------------------------------------------
# DISEÑO
# --------------------------------------------

st.markdown("""
<style>
.stApp {
    background-color: #EDF5E9;
}

html, body, [class*="css"] {
    color: #17472D !important;
}

h1, h2, h3, h4, p, label, span {
    color: #17472D;
}

section[data-testid="stSidebar"] {
    background-color: #DCEBD8;
}

.stButton > button {
    background-color: #17472D !important;
    color: white !important;
    border: none !important;
    border-radius: 12px;
    font-weight: bold;
    min-height: 42px;
}

.stButton > button:hover {
    background-color: #28663F !important;
    color: white !important;
}

.stTextInput input {
    color: #17472D !important;
    background-color: white !important;
    border: 1px solid #A9C5A6 !important;
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

# --------------------------------------------
# ESTADO DE SESIÓN
# --------------------------------------------

if "datos" not in st.session_state:
    st.session_state.datos = {
        "agua": 0,
        "nivelAgua": 0,
        "valvula": "cerrada",
        "lecturaAguaValida": False
    }

if "historial" not in st.session_state:
    st.session_state.historial = []

if "respuesta" not in st.session_state:
    st.session_state.respuesta = "Hola, soy GranjaConecta. ¿En qué puedo ayudarte?"

if "orden" not in st.session_state:
    st.session_state.orden = ""

# --------------------------------------------
# MQTT
# --------------------------------------------

def al_conectar(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(TOPIC)

def al_recibir(client, userdata, msg):
    try:
        recibido = json.loads(msg.payload.decode("utf-8"))

        tipo = recibido.get("tipo", "")

        if tipo == "telemetria":
            datos = recibido.get("datos", recibido)
            st.session_state.datos.update(datos)

        elif "nivelAgua" in recibido or "valvula" in recibido:
            st.session_state.datos.update(recibido)

        elif tipo == "respuesta":
            st.session_state.respuesta = recibido.get(
                "message", "Orden recibida"
            )

    except Exception as e:
        print("Error MQTT:", e)

@st.cache_resource
def obtener_mqtt():
    cliente = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="GranjaConecta_Bebedero"
    )
    cliente.on_connect = al_conectar
    cliente.on_message = al_recibir

    try:
        cliente.connect(BROKER, PORT, 60)
        cliente.loop_start()
        return cliente
    except Exception as e:
        st.error(f"No se pudo conectar con Wokwi: {e}")
        return None

cliente = obtener_mqtt()

def enviar_comando(comando):
    if cliente is None:
        st.error("No hay conexión MQTT.")
        return False

    mensaje = {
        "tipo": "comando",
        "command": comando
    }

    try:
        cliente.publish(TOPIC, json.dumps(mensaje), qos=0)
        return True
    except Exception as e:
        st.error(f"Error enviando orden: {e}")
        return False

# --------------------------------------------
# DATOS DEL AGUA
# --------------------------------------------

def obtener_nivel():
    datos = st.session_state.datos

    nivel = datos.get("nivelAgua", datos.get("agua", 0))

    try:
        nivel = float(nivel)
    except (ValueError, TypeError):
        nivel = 0

    return max(0, min(100, nivel))

def estado_valvula():
    return str(
        st.session_state.datos.get("valvula", "cerrada")
    ).lower()

# --------------------------------------------
# INTERPRETACIÓN DE ÓRDENES
# --------------------------------------------

def interpretar(texto):
    texto = texto.lower().strip()

    abrir = [
        "abre la válvula",
        "abrir la válvula",
        "abre valvula",
        "llena el bebedero",
        "comienza a llenar",
        "inicia el llenado"
    ]

    cerrar = [
        "cierra la válvula",
        "cerrar la válvula",
        "cierra valvula",
        "detén el llenado",
        "detener llenado",
        "para el llenado",
        "detén la válvula"
    ]

    if any(x in texto for x in abrir):
        return "VALVULA_ABRIR"

    if any(x in texto for x in cerrar):
        return "VALVULA_CERRAR"

    return None

# --------------------------------------------
# RESPUESTAS
# --------------------------------------------

def responder(pregunta):
    pregunta = pregunta.lower()
    nivel = obtener_nivel()
    valvula = estado_valvula()

    if "cuánta agua" in pregunta or "porcentaje" in pregunta:
        return f"El bebedero tiene un {nivel:.0f}% de agua."

    if "lleno" in pregunta:
        if nivel >= NIVEL_MAXIMO:
            return "El bebedero alcanzó su nivel máximo."
        return f"El bebedero tiene un {nivel:.0f}% de agua y todavía puede llenarse."

    if "vacío" in pregunta or "vacio" in pregunta:
        return (
            "El bebedero está vacío."
            if nivel <= NIVEL_BAJO
            else f"El bebedero tiene un {nivel:.0f}% de agua."
        )

    if "válvula" in pregunta or "valvula" in pregunta:
        return f"La válvula está {valvula}."

    if nivel <= NIVEL_BAJO:
        return "El nivel de agua es bajo. Se recomienda llenar el bebedero."

    if nivel >= NIVEL_MAXIMO:
        return "El bebedero está en su nivel máximo. La válvula debe permanecer cerrada."

    return f"El nivel actual de agua es {nivel:.0f}%. Todo está funcionando."

# --------------------------------------------
# EJECUTAR ORDEN
# --------------------------------------------

def procesar_mensaje(texto):
    if not texto.strip():
        return

    st.session_state.historial.append(
        {"tipo": "usuario", "texto": texto}
    )

    comando = interpretar(texto)

    if comando == "VALVULA_ABRIR":
        nivel = obtener_nivel()

        if nivel >= NIVEL_MAXIMO:
            respuesta = "No puedo abrir la válvula porque el bebedero ya alcanzó el nivel máximo."
        else:
            if enviar_comando(comando):
                respuesta = "He enviado la orden para abrir la válvula. Estoy esperando la confirmación del sistema."
            else:
                respuesta = "No pude enviar la orden. Comprueba la conexión."

    elif comando == "VALVULA_CERRAR":
        if enviar_comando(comando):
            respuesta = "He enviado la orden para cerrar la válvula."
        else:
            respuesta = "No pude enviar la orden. Comprueba la conexión."

    else:
        respuesta = responder(texto)

    st.session_state.respuesta = respuesta
    st.session_state.historial.append(
        {"tipo": "granja", "texto": respuesta}
    )

# --------------------------------------------
# VOZ: RESPUESTA HABLADA
# --------------------------------------------

def reproducir_voz(texto):
    try:
        audio = gTTS(text=texto, lang="es")
        archivo = io.BytesIO()
        audio.write_to_fp(archivo)
        archivo.seek(0)

        st.audio(archivo, format="audio/mp3")

    except Exception as e:
        st.warning(f"No se pudo generar el audio: {e}")

# --------------------------------------------
# CABECERA
# --------------------------------------------

st.title("🐔 GranjaConecta")
st.subheader("Sistema inteligente de control del bebedero")

st.markdown(
    "Consulta el nivel del agua, controla la válvula y recibe alertas."
)

st.divider()

# --------------------------------------------
# ALERTAS
# --------------------------------------------

nivel = obtener_nivel()
valvula = estado_valvula()

if nivel <= NIVEL_BAJO:
    st.warning("⚠️ El nivel de agua está bajo. Se recomienda llenar el bebedero.")

elif nivel >= NIVEL_MAXIMO:
    st.error("🚨 ¡Nivel máximo alcanzado! La válvula debe cerrarse.")

else:
    st.success("✓ El nivel de agua se encuentra dentro del rango normal.")

# --------------------------------------------
# GRÁFICO Y DATOS
# --------------------------------------------

col1, col2 = st.columns([1.2, 1])

with col1:
    st.subheader("🐔 Estado del bebedero")

    altura = int(nivel)

    st.markdown(f"""
    <div style="
        background:#DCEBD8;
        border:3px solid #17472D;
        border-radius:25px;
        padding:20px;
        text-align:center;
    ">
        <div style="
            height:220px;
            width:180px;
            margin:auto;
            border:4px solid #17472D;
            border-radius:12px 12px 30px 30px;
            position:relative;
            overflow:hidden;
            background:#F8FFF6;
        ">
            <div style="
                position:absolute;
                bottom:0;
                width:100%;
                height:{altura}%;
                background:#55B9A0;
                transition:height 0.5s;
            "></div>
            <div style="
                position:absolute;
                top:45%;
                width:100%;
                text-align:center;
                font-size:27px;
                font-weight:bold;
                color:#17472D;
            ">{nivel:.0f}%</div>
        </div>

        <h3 style="color:#17472D;">Bebedero</h3>
        <p style="color:#17472D;">Válvula: {valvula.upper()}</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.subheader("📊 Lecturas del sistema")

    st.metric("Nivel de agua", f"{nivel:.0f}%")

    st.metric(
        "Estado de la válvula",
        valvula.capitalize()
    )

    lectura_valida = st.session_state.datos.get(
        "lecturaAguaValida", False
    )

    st.write(
        "🟢 Sensor ultrasónico conectado"
        if lectura_valida
        else "🟠 Esperando lectura válida del sensor"
    )

    if st.button("🔄 Actualizar datos", use_container_width=True):
        st.rerun()

st.divider()

# --------------------------------------------
# CONTROL MANUAL
# --------------------------------------------

st.subheader("🎛️ Control de la válvula")

c1, c2 = st.columns(2)

with c1:
    if st.button("🟢 ABRIR VÁLVULA", use_container_width=True):
        if nivel >= NIVEL_MAXIMO:
            st.error("El bebedero ya alcanzó el nivel máximo.")
        else:
            enviar_comando("VALVULA_ABRIR")
            st.success("Orden de apertura enviada.")

with c2:
    if st.button("🔴 CERRAR VÁLVULA", use_container_width=True):
        enviar_comando("VALVULA_CERRAR")
        st.success("Orden de cierre enviada.")

st.divider()

# --------------------------------------------
# ASISTENTE DE VOZ Y TEXTO
# --------------------------------------------

st.subheader("🎙️ Habla con GranjaConecta")

st.write(
    "Puedes hablar o escribir una pregunta u orden. "
    "La granja reconocerá tu solicitud."
)

audio_voz = mic_recorder(
    start_prompt="🎙️ Hablar",
    stop_prompt="⏹️ Terminar",
    key="microfono_bebedero",
    use_container_width=True
)

if audio_voz and audio_voz.get("bytes"):
    try:
        audio_bytes = audio_voz["bytes"]
        recognizer = sr.Recognizer()

        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio = recognizer.record(source)

        texto_reconocido = recognizer.recognize_google(
            audio,
            language="es-ES"
        )

        st.success("Texto reconocido:")
        st.write(texto_reconocido)

        if st.button("Enviar orden reconocida"):
            procesar_mensaje(texto_reconocido)
            st.rerun()

    except sr.UnknownValueError:
        st.warning("No pude entender lo que dijiste. Inténtalo otra vez.")

    except sr.RequestError:
        st.error("No se pudo conectar con el servicio de reconocimiento.")

texto = st.text_input(
    "Escribe tu pregunta u orden",
    placeholder="Ej. Abre la válvula del bebedero..."
)

if st.button("Enviar mensaje", use_container_width=True):
    if texto.strip():
        procesar_mensaje(texto)
        st.rerun()

# --------------------------------------------
# RESPUESTA
# --------------------------------------------

st.divider()

st.subheader("💬 Respuesta de GranjaConecta")

st.info(st.session_state.respuesta)

if st.button("🔊 Escuchar respuesta", use_container_width=True):
    reproducir_voz(st.session_state.respuesta)

# --------------------------------------------
# HISTORIAL
# --------------------------------------------

st.divider()

st.subheader("📝 Conversación")

for mensaje in st.session_state.historial[-10:]:
    if mensaje["tipo"] == "usuario":
        st.markdown(
            f"**🧑 Tú:** {mensaje['texto']}"
        )
    else:
        st.markdown(
            f"**🐔 GranjaConecta:** {mensaje['texto']}"
        )

