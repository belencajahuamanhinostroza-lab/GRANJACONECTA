
import streamlit as st
import paho.mqtt.client as mqtt
import json
import io
import re
import unicodedata
import queue
import hashlib
import speech_recognition as sr

from gtts import gTTS
from streamlit_mic_recorder import mic_recorder
from streamlit_autorefresh import st_autorefresh
from threading import Lock
from datetime import datetime


# =========================================================
# 1. CONFIGURACIÓN
# =========================================================

st.set_page_config(
    page_title="GranjaConecta | Bebedero",
    page_icon="🐔",
    layout="wide",
    initial_sidebar_state="collapsed"
)

BROKER = "broker.mqttdashboard.com"
PORT = 1883
TOPIC = "granjaconecta"
CLIENT_ID = "STREAMLIT_BEBEDERO"

COLOR_VERDE = "#17472D"
COLOR_VERDE_CLARO = "#EDF5E9"
COLOR_VERDE_MEDIO = "#DCEBD8"
COLOR_BLANCO = "#FFFFFF"
COLOR_ROJO = "#C0392B"
COLOR_AMARILLO = "#D99A18"
COLOR_AZUL = "#3198D4"


# =========================================================
# 2. ESTILOS
# =========================================================

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700;800;900&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Nunito', sans-serif;
    }}

    .stApp {{
        background: {COLOR_VERDE_CLARO};
        color: {COLOR_VERDE};
    }}

    [data-testid="stHeader"] {{
        background: transparent;
    }}

    [data-testid="stSidebar"] {{
        background: {COLOR_VERDE_MEDIO};
    }}

    h1, h2, h3, h4, p, label {{
        color: {COLOR_VERDE} !important;
    }}

    .titulo-principal {{
        color: {COLOR_VERDE};
        font-size: 35px;
        font-weight: 900;
        margin-bottom: 3px;
    }}

    .subtitulo {{
        color: #53745C;
        font-size: 15px;
        margin-bottom: 20px;
    }}

    .tarjeta {{
        background: white;
        padding: 20px;
        border-radius: 18px;
        border: 1px solid #D8E8D4;
        box-shadow: 0 3px 12px rgba(23,71,45,0.06);
        margin-bottom: 14px;
    }}

    .tarjeta-titulo {{
        color: {COLOR_VERDE};
        font-size: 18px;
        font-weight: 900;
        margin-bottom: 12px;
    }}

    .dato-grande {{
        font-size: 29px;
        font-weight: 900;
        color: {COLOR_VERDE};
    }}

    .dato-pequeno {{
        font-size: 13px;
        color: #64806A;
        font-weight: 700;
    }}

    .estado {{
        display: inline-block;
        padding: 7px 13px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 900;
    }}

    .estado-verde {{
        background: #DDF2DF;
        color: #17652D;
    }}

    .estado-rojo {{
        background: #FBE2DF;
        color: #A52A22;
    }}

    .estado-amarillo {{
        background: #FFF0C9;
        color: #8A5A00;
    }}

    .estado-gris {{
        background: #E9EEE9;
        color: #526354;
    }}

    div.stButton > button {{
        background: {COLOR_VERDE} !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        min-height: 45px;
        font-weight: 800 !important;
        width: 100%;
    }}

    div.stButton > button:hover {{
        background: #28613D !important;
        color: white !important;
        border: none !important;
    }}

    div[data-testid="stTextInput"] input {{
        border: 1px solid #B8D0B6;
        border-radius: 10px;
        color: {COLOR_VERDE};
    }}

    div[data-testid="stTextInput"] input:focus {{
        border-color: {COLOR_VERDE};
        box-shadow: 0 0 0 1px {COLOR_VERDE};
    }}

    div[data-testid="stMetric"] {{
        background: white;
        padding: 13px;
        border-radius: 14px;
        border: 1px solid #D8E8D4;
    }}

    div[data-testid="stMetricLabel"] p {{
        color: #64806A !important;
        font-weight: 800;
    }}

    div[data-testid="stMetricValue"] {{
        color: {COLOR_VERDE} !important;
        font-weight: 900;
    }}

    hr {{
        border-color: #D2E3CF;
    }}

    .mensaje {{
        background: #FFFFFF;
        border-left: 5px solid #4E8B5C;
        padding: 13px 16px;
        border-radius: 10px;
        color: {COLOR_VERDE};
        margin-bottom: 10px;
    }}

    .alerta {{
        background: #FFF0D8;
        border-left: 5px solid #D99A18;
        padding: 13px 16px;
        border-radius: 10px;
        color: #79530A;
        margin-bottom: 10px;
    }}

    .pie {{
        text-align: center;
        color: #77917B;
        font-size: 12px;
        margin-top: 25px;
    }}
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# 3. ESTADO DE LA APLICACIÓN
# =========================================================

if "telemetria" not in st.session_state:
    st.session_state.telemetria = {
        "temperatura": None,
        "humedad": None,
        "agua": 50.0,
        "nivelAgua": 50.0,
        "distancia": None,
        "distanciaHC": None,
        "lecturaDHTValida": False,
        "lecturaHCValida": False,
        "lecturaAguaValida": False,
        "estadoAgua": "SIN DATOS",
        "puerta": "desconocida",
        "valvula": "desconocida",
        "vaciando": False,
        "ventilacion": 50,
        "ajusteTermico": 50,
        "humedadVisual": 50
    }

if "historial" not in st.session_state:
    st.session_state.historial = []

if "respuesta" not in st.session_state:
    st.session_state.respuesta = (
        "Hola. Soy el asistente de GranjaConecta. "
        "Puedes darme una orden por voz o escribirla."
    )

if "ultima_orden" not in st.session_state:
    st.session_state.ultima_orden = "Ninguna orden enviada"

if "ultimo_audio" not in st.session_state:
    st.session_state.ultimo_audio = None

if "mensajes_procesados" not in st.session_state:
    st.session_state.mensajes_procesados = 0

if "mqtt_ultima_respuesta" not in st.session_state:
    st.session_state.mqtt_ultima_respuesta = "Esperando respuesta del ESP32"


# =========================================================
# 4. CLIENTE MQTT
# =========================================================

@st.cache_resource
def crear_cliente_mqtt():

    cola_mensajes = queue.Queue()
    estado = {
        "conectado": False,
        "error": None
    }

    def al_conectar(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            estado["conectado"] = True
            estado["error"] = None
            client.subscribe(TOPIC)
        else:
            estado["conectado"] = False
            estado["error"] = f"Error MQTT: {reason_code}"

    def al_desconectar(client, userdata, disconnect_flags, reason_code, properties):
        estado["conectado"] = False

    def al_recibir(client, userdata, msg):
        try:
            contenido = json.loads(msg.payload.decode("utf-8"))
            cola_mensajes.put(contenido)
        except Exception:
            pass

    cliente = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=CLIENT_ID,
        protocol=mqtt.MQTTv311
    )

    cliente.on_connect = al_conectar
    cliente.on_disconnect = al_desconectar
    cliente.on_message = al_recibir

    try:
        cliente.connect(BROKER, PORT, keepalive=60)
        cliente.loop_start()
    except Exception as e:
        estado["conectado"] = False
        estado["error"] = str(e)

    return cliente, cola_mensajes, estado


cliente, cola_mensajes, estado_mqtt = crear_cliente_mqtt()


# =========================================================
# 5. FUNCIONES GENERALES
# =========================================================

def normalizar(texto):
    texto = str(texto).lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )
    texto = re.sub(r"\s+", " ", texto)
    return texto


def guardar_historial(tipo, mensaje):
    hora = datetime.now().strftime("%H:%M:%S")

    st.session_state.historial.insert(
        0,
        {
            "hora": hora,
            "tipo": tipo,
            "mensaje": mensaje
        }
    )

    st.session_state.historial = (
        st.session_state.historial[:30]
    )


def publicar_comando(comando, descripcion):

    if not estado_mqtt["conectado"]:
        st.session_state.respuesta = (
            "No puedo enviar la orden porque no hay conexión MQTT. "
            "Verifica que el ESP32 esté conectado."
        )
        guardar_historial("ERROR", descripcion)
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

        if resultado.rc == mqtt.MQTT_ERR_SUCCESS:
            st.session_state.ultima_orden = descripcion
            st.session_state.respuesta = (
                f"Orden enviada: {descripcion}. "
                "Estoy esperando la actualización del ESP32."
            )
            guardar_historial("ORDEN", descripcion)
            return True

        st.session_state.respuesta = (
            "No se pudo enviar la orden por MQTT."
        )
        guardar_historial("ERROR", descripcion)
        return False

    except Exception as e:
        st.session_state.respuesta = (
            f"Error al enviar la orden: {e}"
        )
        guardar_historial("ERROR", descripcion)
        return False


# =========================================================
# 6. RECEPCIÓN DE TELEMETRÍA
# =========================================================

def actualizar_telemetria():

    while True:
        try:
            mensaje = cola_mensajes.get_nowait()
        except queue.Empty:
            break

        tipo = mensaje.get("tipo", "")

        if tipo == "telemetria":

            datos = mensaje.get("datos", {})

            for clave in st.session_state.telemetria:
                if clave in datos:
                    st.session_state.telemetria[clave] = datos[clave]

            st.session_state.mensajes_procesados += 1

        elif tipo == "respuesta":

            status = mensaje.get("status", "")
            message = mensaje.get("message", "")

            if message:
                st.session_state.mqtt_ultima_respuesta = message
                st.session_state.respuesta = message

            if status:
                guardar_historial(
                    "ESP32",
                    f"{status}: {message}"
                )


actualizar_telemetria()


# =========================================================
# 7. INTERPRETACIÓN DE ÓRDENES
# =========================================================

def procesar_orden(texto):

    orden = normalizar(texto)

    if not orden:
        st.session_state.respuesta = (
            "No recibí ninguna orden. Intenta nuevamente."
        )
        return

    # -------------------------------
    # ABRIR VÁLVULA
    # -------------------------------

    if (
        "abrir valvula" in orden
        or "abre valvula" in orden
        or "activar valvula" in orden
        or "llenar bebedero" in orden
        or "llenar el bebedero" in orden
        or "agregar agua" in orden
    ):
        publicar_comando(
            "VALVULA_ABRIR",
            "Abrir válvula del bebedero"
        )
        return

    # -------------------------------
    # CERRAR VÁLVULA
    # -------------------------------

    if (
        "cerrar valvula" in orden
        or "cierra valvula" in orden
        or "detener valvula" in orden
        or "detener llenado" in orden
        or "detener el agua" in orden
        or "parar el agua" in orden
    ):
        publicar_comando(
            "VALVULA_CERRAR",
            "Cerrar válvula del bebedero"
        )
        return

    # -------------------------------
    # VACIAR BEBEDERO
    # -------------------------------

    if (
        "vaciar bebedero" in orden
        or "vaciar el bebedero" in orden
        or "sacar toda el agua" in orden
        or "drenar bebedero" in orden
    ):
        publicar_comando(
            "BEBEDERO_VACIAR",
            "Vaciar bebedero"
        )
        return

    # -------------------------------
    # LLENAR COMPLETAMENTE
    # -------------------------------

    if (
        "llenar completamente" in orden
        or "llenar hasta arriba" in orden
        or "llenar al maximo" in orden
        or "bebedero lleno" in orden
        or "llenar por completo" in orden
    ):
        publicar_comando(
            "BEBEDERO_LLENO",
            "Llenar completamente el bebedero"
        )
        return

    # -------------------------------
    # CONSULTAR NIVEL DE AGUA
    # -------------------------------

    if (
        "nivel de agua" in orden
        or "cuanta agua" in orden
        or "cuanto agua" in orden
        or "porcentaje de agua" in orden
        or "estado del agua" in orden
    ):
        datos = st.session_state.telemetria
        nivel = datos.get("nivelAgua", 0)

        if nivel is not None:
            st.session_state.respuesta = (
                f"El bebedero tiene aproximadamente "
                f"{float(nivel):.1f}% de agua."
            )
        else:
            st.session_state.respuesta = (
                "Todavía no tengo una lectura del nivel de agua."
            )

        guardar_historial(
            "CONSULTA",
            "Consulta del nivel de agua"
        )
        return

    # -------------------------------
    # CONSULTAR VÁLVULA
    # -------------------------------

    if (
        "estado de la valvula" in orden
        or "valvula esta abierta" in orden
        or "valvula esta cerrada" in orden
        or "como esta la valvula" in orden
    ):
        valvula = st.session_state.telemetria.get(
            "valvula",
            "desconocida"
        )

        st.session_state.respuesta = (
            f"El estado actual de la válvula es: {valvula}."
        )

        guardar_historial("CONSULTA", "Consulta del estado de la válvula")
        return

    # -------------------------------
    # CONSULTA GENERAL
    # -------------------------------

    if (
        "estado del bebedero" in orden
        or "como esta el bebedero" in orden
        or "informacion del bebedero" in orden
    ):
        datos = st.session_state.telemetria
        nivel = datos.get("nivelAgua", 0)
        valvula = datos.get("valvula", "desconocida")

        st.session_state.respuesta = (
            f"El nivel de agua es {float(nivel):.1f}%. "
            f"La válvula está {valvula}."
        )

        guardar_historial("CONSULTA", "Consulta general del bebedero")
        return

    # -------------------------------
    # ORDEN NO RECONOCIDA
    # -------------------------------

    st.session_state.respuesta = (
        "No reconocí esa orden. Puedes decir: abrir válvula, "
        "cerrar válvula, llenar bebedero, vaciar bebedero "
        "o consultar el nivel de agua."
    )

    guardar_historial("AVISO", f"Orden no reconocida: {texto}")


# =========================================================
# 8. RECONOCIMIENTO DE VOZ
# =========================================================

def reconocer_audio(audio_bytes):

    try:
        reconocedor = sr.Recognizer()

        with sr.AudioFile(io.BytesIO(audio_bytes)) as fuente:
            audio = reconocedor.record(fuente)

        texto = reconocedor.recognize_google(
            audio,
            language="es-CO"
        )

        return texto

    except sr.UnknownValueError:
        return None

    except sr.RequestError:
        st.session_state.respuesta = (
            "No fue posible conectarse al servicio de reconocimiento "
            "de voz. Revisa tu conexión a internet."
        )
        return None

    except Exception as e:
        st.session_state.respuesta = (
            f"No pude procesar el audio: {e}"
        )
        return None


# =========================================================
# 9. ACTUALIZACIÓN AUTOMÁTICA
# =========================================================

st_autorefresh(
    interval=2000,
    key="actualizacion_bebedero"
)


# =========================================================
# 10. ENCABEZADO
# =========================================================

st.markdown(
    """
    <div class="titulo-principal">🐔 GranjaConecta</div>
    <div class="subtitulo">
        Control inteligente del bebedero · Monitoreo y gestión del agua
    </div>
    """,
    unsafe_allow_html=True
)

if estado_mqtt["conectado"]:
    st.markdown(
        '<span class="estado estado-verde">● MQTT CONECTADO</span>',
        unsafe_allow_html=True
    )
else:
    st.markdown(
        '<span class="estado estado-rojo">● MQTT DESCONECTADO</span>',
        unsafe_allow_html=True
    )

st.write("")


# =========================================================
# 11. DATOS ACTUALES
# =========================================================

datos = st.session_state.telemetria

nivel = datos.get("nivelAgua", 0)

try:
    nivel = float(nivel)
except (ValueError, TypeError):
    nivel = 0.0

nivel = max(0.0, min(100.0, nivel))

valvula = str(datos.get("valvula", "desconocida")).lower()
vaciando = bool(datos.get("vaciando", False))

if valvula == "abierta":
    estado_valvula = "ABIERTA"
    clase_valvula = "estado-verde"
elif valvula == "cerrada":
    estado_valvula = "CERRADA"
    clase_valvula = "estado-gris"
else:
    estado_valvula = "SIN DATOS"
    clase_valvula = "estado-amarillo"


# =========================================================
# 12. GRÁFICO DEL BEBEDERO
# =========================================================

col_grafico, col_datos = st.columns([1.15, 1])

with col_grafico:

    st.markdown(
        '<div class="tarjeta">',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="tarjeta-titulo">💧 Nivel de agua del bebedero</div>',
        unsafe_allow_html=True
    )

    if nivel <= 20:
        color_agua = "#E9A23B"
    else:
        color_agua = "#42A5D5"

    altura_agua = nivel

    st.markdown(
        f"""
        <div style="
            display:flex;
            justify-content:center;
            align-items:center;
            gap:35px;
            padding:12px 5px 20px 5px;
        ">

            <div style="
                position:relative;
                width:190px;
                height:245px;
                border:7px solid #78917C;
                border-top:12px solid #78917C;
                border-radius:20px 20px 32px 32px;
                background:#F5FAF3;
                overflow:hidden;
                box-shadow:inset 0 0 12px rgba(0,0,0,0.08);
            ">

                <div style="
                    position:absolute;
                    top:0;
                    left:0;
                    width:100%;
                    height:100%;
                    background:
                    repeating-linear-gradient(
                        to bottom,
                        transparent 0px,
                        transparent 47px,
                        rgba(23,71,45,0.10) 48px,
                        transparent 49px
                    );
                    z-index:2;
                    pointer-events:none;
                "></div>

                <div style="
                    position:absolute;
                    bottom:0;
                    left:0;
                    width:100%;
                    height:{altura_agua}%;
                    background:{color_agua};
                    transition:height 0.8s ease;
                    border-radius:0 0 20px 20px;
                    opacity:0.9;
                "></div>

                <div style="
                    position:absolute;
                    top:8px;
                    left:0;
                    width:100%;
                    text-align:center;
                    color:#17472D;
                    font-size:14px;
                    font-weight:900;
                    z-index:3;
                ">
                    AGUA
                </div>

                <div style="
                    position:absolute;
                    bottom:10px;
                    left:0;
                    width:100%;
                    text-align:center;
                    color:#17472D;
                    font-size:21px;
                    font-weight:900;
                    z-index:4;
                    text-shadow:0 1px 3px rgba(255,255,255,0.65);
                ">
                    {nivel:.0f}%
                </div>
            </div>

            <div style="
                display:flex;
                flex-direction:column;
                justify-content:space-between;
                height:225px;
                color:#17472D;
                font-weight:800;
                font-size:14px;
            ">
                <div>100% ─────</div>
                <div>75% ─────</div>
                <div>50% ─────</div>
                <div>25% ─────</div>
                <div>0% ─────</div>
            </div>
        </div>

        <div style="
            text-align:center;
            color:#53745C;
            font-size:13px;
            font-weight:800;
        ">
            Representación visual del nivel de agua recibido desde el ESP32
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# 13. INFORMACIÓN DEL BEBEDERO
# =========================================================

with col_datos:

    st.markdown(
        '<div class="tarjeta">',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="tarjeta-titulo">📊 Información actual</div>',
        unsafe_allow_html=True
    )

    st.metric(
        "Porcentaje de agua",
        f"{nivel:.1f}%"
    )

    st.markdown(
        f"""
        <div style="margin:12px 0 18px 0;">
            <div class="dato-pequeno">ESTADO DE LA VÁLVULA</div>
            <span class="estado {clase_valvula}">
                {estado_valvula}
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    if vaciando:
        estado_agua = "VACIANDO"
        clase_agua = "estado-amarillo"
    elif nivel <= 10:
        estado_agua = "NIVEL MUY BAJO"
        clase_agua = "estado-rojo"
    elif nivel <= 30:
        estado_agua = "NIVEL BAJO"
        clase_agua = "estado-amarillo"
    elif nivel >= 90:
        estado_agua = "LLENO"
        clase_agua = "estado-verde"
    else:
        estado_agua = "NIVEL NORMAL"
        clase_agua = "estado-verde"

    st.markdown(
        f"""
        <div style="margin-bottom:15px;">
            <div class="dato-pequeno">ESTADO DEL AGUA</div>
            <span class="estado {clase_agua}">
                {estado_agua}
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    distancia = datos.get("distancia")

    if distancia is not None:
        st.write(f"**Distancia del sensor de agua:** {distancia} cm")
    else:
        st.write("**Distancia del sensor de agua:** Sin lectura")

    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# 14. ALERTAS
# =========================================================

st.markdown("### 🔔 Alertas del bebedero")

alertas = []

if not estado_mqtt["conectado"]:
    alertas.append(
        "No hay conexión con el sistema MQTT. "
        "No se pueden enviar órdenes al bebedero."
    )

if not datos.get("lecturaAguaValida", False):
    alertas.append(
        "No se ha recibido una lectura válida del nivel de agua."
    )
else:
    if nivel <= 10:
        alertas.append("El bebedero está casi vacío. Se necesita agua.")
    elif nivel <= 30:
        alertas.append("El nivel de agua está bajo.")

    if nivel >= 90:
        alertas.append("El bebedero alcanzó su nivel máximo.")

if not datos.get("lecturaDHTValida", False):
    alertas.append(
        "El sensor de temperatura y humedad no está enviando una lectura válida."
    )

if not datos.get("lecturaHCValida", False):
    alertas.append(
        "El sensor ultrasónico HC-SR04 no tiene una lectura válida."
    )

if alertas:
    for alerta in alertas:
        st.markdown(
            f'<div class="alerta">⚠️ {alerta}</div>',
            unsafe_allow_html=True
        )
else:
    st.markdown(
        """
        <div class="mensaje">
            ✓ No hay alertas activas en el bebedero.
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# 15. CONTROLES MANUALES
# =========================================================

st.divider()
st.markdown("### 🎛️ Control del bebedero")

st.write(
    "Selecciona una acción para enviar una orden al ESP32."
)

c1, c2, c3, c4 = st.columns(4)

with c1:
    if st.button("💧 Abrir válvula"):
        publicar_comando(
            "VALVULA_ABRIR",
            "Abrir válvula del bebedero"
        )
        st.rerun()

with c2:
    if st.button("⛔ Cerrar válvula"):
        publicar_comando(
            "VALVULA_CERRAR",
            "Cerrar válvula del bebedero"
        )
        st.rerun()

with c3:
    if st.button("🪣 Llenar bebedero"):
        publicar_comando(
            "BEBEDERO_LLENO",
            "Llenar completamente el bebedero"
        )
        st.rerun()

with c4:
    if st.button("🚰 Vaciar bebedero"):
        publicar_comando(
            "BEBEDERO_VACIAR",
            "Vaciar bebedero"
        )
        st.rerun()


# =========================================================
# 16. ASISTENTE POR VOZ
# =========================================================

st.divider()
st.markdown("### 🎙️ Asistente por voz")

st.write(
    "Pulsa el botón para grabar una orden. "
    "El sistema reconocerá tu voz y enviará la instrucción al bebedero."
)

audio = mic_recorder(
    start_prompt="🎙️ Hablar con el bebedero",
    stop_prompt="⏹️ Detener grabación",
    just_once=True,
    use_container_width=True,
    key="microfono_bebedero"
)

if audio and audio.get("bytes"):

    audio_bytes = audio["bytes"]
    identificador_audio = hashlib.md5(audio_bytes).hexdigest()

    if identificador_audio != st.session_state.ultimo_audio:

        st.session_state.ultimo_audio = identificador_audio

        with st.spinner("Reconociendo tu voz..."):

            texto_reconocido = reconocer_audio(audio_bytes)

        if texto_reconocido:
            st.success(f"Has dicho: **{texto_reconocido}**")
            procesar_orden(texto_reconocido)
            st.rerun()
        else:
            st.warning(
                "No pude reconocer la voz. "
                "Intenta hablar más claro y cerca del micrófono."
            )


# =========================================================
# 17. ASISTENTE POR TEXTO
# =========================================================

st.divider()
st.markdown("### 💬 Escribe una orden")

st.write(
    "También puedes escribir una instrucción o consultar el estado del bebedero."
)

with st.form("formulario_orden_bebedero", clear_on_submit=True):

    texto_orden = st.text_input(
        "Escribe tu orden",
        placeholder="Ejemplo: llenar el bebedero"
    )

    enviar = st.form_submit_button(
        "Enviar orden"
    )

    if enviar:
        if texto_orden.strip():
            procesar_orden(texto_orden)
        else:
            st.session_state.respuesta = (
                "Primero escribe una orden o consulta."
            )


# =========================================================
# 18. RESPUESTA ESCRITA DEL ASISTENTE
# =========================================================

st.markdown("### 🤖 Respuesta del asistente")

st.markdown(
    f"""
    <div class="mensaje">
        <strong>GranjaConecta:</strong><br>
        {st.session_state.respuesta}
    </div>
    """,
    unsafe_allow_html=True
)

st.caption(
    "El asistente responde por escrito. "
    "Las órdenes se envían al ESP32 mediante MQTT."
)


# =========================================================
# 19. HISTORIAL
# =========================================================

st.divider()
st.markdown("### 📋 Historial de actividad")

if st.session_state.historial:

    for elemento in st.session_state.historial:

        st.markdown(
            f"""
            <div class="tarjeta" style="padding:12px 16px;">
                <div style="
                    display:flex;
                    justify-content:space-between;
                    gap:10px;
                ">
                    <strong style="color:#17472D;">
                        {elemento["tipo"]}
                    </strong>
                    <span style="
                        color:#77917B;
                        font-size:12px;
                    ">
                        {elemento["hora"]}
                    </span>
                </div>
                <div style="
                    color:#49684F;
                    margin-top:5px;
                ">
                    {elemento["mensaje"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

else:
    st.info("Todavía no hay actividad registrada.")


if st.button("🗑️ Limpiar historial"):
    st.session_state.historial = []
    st.rerun()


# =========================================================
# 20. INFORMACIÓN DE CONEXIÓN
# =========================================================

with st.expander("ℹ️ Información de conexión"):

    st.write(f"**Broker:** {BROKER}")
    st.write(f"**Puerto:** {PORT}")
    st.write(f"**Tópico MQTT:** {TOPIC}")
    st.write(f"**Cliente:** {CLIENT_ID}")

    st.write(
        f"**Mensajes de telemetría recibidos:** "
        f"{st.session_state.mensajes_procesados}"
    )

    st.write(
        f"**Última respuesta del ESP32:** "
        f"{st.session_state.mqtt_ultima_respuesta}"
    )


# =========================================================
# 21. PIE DE PÁGINA
# =========================================================

st.markdown(
    """
    <div class="pie">
        GranjaConecta · Sistema inteligente de monitoreo y control
        <br>
        Comunicación mediante ESP32 · Wokwi · MQTT
    </div>
    """,
    unsafe_allow_html=True
)
