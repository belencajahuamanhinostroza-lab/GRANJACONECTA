import json
import time
import queue
from io import BytesIO

import streamlit as st
import paho.mqtt.client as mqtt
from gtts import gTTS
from streamlit_mic_recorder import speech_to_text


# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================
st.set_page_config(
    page_title="GranjaConecta | Bebedero",
    page_icon="🐔",
    layout="wide"
)

BROKER = "broker.mqttdashboard.com"
PUERTO = 1883
TOPIC = "granjaconecta"

# Umbrales iniciales para interpretar el nivel de agua.
# Puedes ajustarlos según las necesidades de tu prototipo.
NIVEL_BAJO = 20
NIVEL_SUFICIENTE = 40
NIVEL_LLENO = 90

st.markdown("""
<style>
.stApp {
    background: #edf5e9;
}
h1, h2, h3, h4, p, label, .stMarkdown {
    color: #17472d;
}
.titulo {
    color: #17472d;
    font-size: 2rem;
    font-weight: 800;
}
.tarjeta {
    background: #ffffff;
    border: 1px solid #d5e5d2;
    border-radius: 16px;
    padding: 16px;
    color: #17472d;
}
.estado {
    font-size: 1.55rem;
    font-weight: 800;
    color: #17472d;
}
.mensaje {
    background: #ffffff;
    border-left: 5px solid #398653;
    padding: 12px 15px;
    border-radius: 10px;
    margin: 8px 0;
    color: #17472d;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# MQTT: CONEXIÓN Y RECEPCIÓN DE TELEMETRÍA
# =========================================================
@st.cache_resource
def iniciar_mqtt():
    estado = {
        "conectado": False,
        "telemetria": {},
        "ultima_respuesta": "",
        "ultimo_mensaje": 0,
        "error": ""
    }

    def al_conectar(client, userdata, flags, rc):
        if rc == 0:
            estado["conectado"] = True
            estado["error"] = ""
            client.subscribe(TOPIC)
        else:
            estado["conectado"] = False
            estado["error"] = f"No se pudo conectar al broker. Código: {rc}"

    def al_desconectar(client, userdata, rc):
        estado["conectado"] = False

    def al_recibir(client, userdata, msg):
        try:
            contenido = json.loads(msg.payload.decode("utf-8"))
            tipo = contenido.get("tipo", "")

            if tipo == "telemetria":
                datos = contenido.get("datos", contenido)
                estado["telemetria"] = datos
                estado["ultimo_mensaje"] = time.time()

            elif tipo == "respuesta":
                estado["ultima_respuesta"] = contenido.get(
                    "message",
                    contenido.get("status", "Respuesta recibida")
                )
                estado["ultimo_mensaje"] = time.time()

        except Exception as error:
            estado["error"] = f"Mensaje MQTT no válido: {error}"

    try:
        cliente = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
            client_id=f"GranjaConecta-Bebedero-{int(time.time())}"
        )
        cliente.on_connect = al_conectar
        cliente.on_disconnect = al_desconectar
        cliente.on_message = al_recibir
        cliente.connect(BROKER, PUERTO, 60)
        cliente.loop_start()
        return cliente, estado

    except Exception as error:
        estado["error"] = str(error)
        return None, estado


cliente_mqtt, estado_mqtt = iniciar_mqtt()


def publicar_comando(comando):
    """Envía únicamente órdenes relacionadas con la válvula."""
    if cliente_mqtt is None or not estado_mqtt["conectado"]:
        return False

    mensaje = {
        "tipo": "comando",
        "command": comando
    }

    resultado = cliente_mqtt.publish(TOPIC, json.dumps(mensaje))
    return resultado.rc == mqtt.MQTT_ERR_SUCCESS


# =========================================================
# FUNCIONES PARA LEER LA TELEMETRÍA
# =========================================================
def obtener_nivel(datos):
    valor = datos.get("nivelAgua", datos.get("agua", None))
    if valor is None:
        return None

    try:
        valor = float(valor)
        # El firmware debe enviar nivelAgua/agua como porcentaje 0-100.
        return max(0, min(100, valor))
    except (TypeError, ValueError):
        return None


def obtener_valvula(datos):
    valor = str(datos.get("valvula", "desconocida")).strip().lower()
    if valor in ["abierta", "abierto", "open", "1", "true"]:
        return "Abierta"
    if valor in ["cerrada", "cerrado", "closed", "0", "false"]:
        return "Cerrada"
    return "Sin información"


# =========================================================
# RESPUESTAS A PREGUNTAS
# =========================================================
def responder_pregunta(texto):
    datos = estado_mqtt["telemetria"]
    pregunta = texto.lower().strip()
    nivel = obtener_nivel(datos)
    valvula = obtener_valvula(datos)

    if not datos:
        return (
            "Todavía no recibo información del bebedero. "
            "Verifica que el ESP32 esté conectado al Wi-Fi y al broker MQTT."
        )

    if any(p in pregunta for p in [
        "cuánta agua", "cuanta agua", "nivel de agua", "porcentaje de agua"
    ]):
        if nivel is None:
            return "Todavía no tengo una lectura válida del nivel de agua."
        return f"El bebedero tiene aproximadamente {nivel:.0f} por ciento de agua."

    if "está lleno" in pregunta or "esta lleno" in pregunta or "lleno" == pregunta:
        if nivel is None:
            return "No puedo confirmar si está lleno porque no tengo el nivel de agua."
        if nivel >= NIVEL_LLENO:
            return f"Sí. El bebedero está prácticamente lleno, tiene {nivel:.0f} por ciento."
        return f"No. El bebedero tiene {nivel:.0f} por ciento de agua y todavía puede llenarse."

    if "suficiente" in pregunta or "para las gallinas" in pregunta:
        if nivel is None:
            return "No puedo determinarlo porque no tengo una lectura del nivel de agua."
        if nivel >= NIVEL_SUFICIENTE:
            return f"Sí. El nivel actual es {nivel:.0f} por ciento y supera el mínimo configurado."
        return f"No. El nivel está en {nivel:.0f} por ciento. Es recomendable revisar el suministro."

    if "vacío" in pregunta or "vacio" in pregunta:
        if nivel is None:
            return "No puedo confirmar si está vacío porque no tengo una lectura del nivel."
        if nivel <= NIVEL_BAJO:
            return f"El bebedero está casi vacío. Tiene {nivel:.0f} por ciento de agua."
        return f"No está vacío. Tiene {nivel:.0f} por ciento de agua."

    if "válvula" in pregunta or "valvula" in pregunta:
        if valvula == "Sin información":
            return "Todavía no recibo el estado de la válvula."
        return f"La válvula está {valvula.lower()}."

    if "necesita agua" in pregunta or "hace falta agua" in pregunta:
        if nivel is None:
            return "No puedo saber si necesita agua porque no tengo una lectura del nivel."
        if nivel < NIVEL_SUFICIENTE:
            return f"Sí. El bebedero tiene {nivel:.0f} por ciento de agua y necesita llenarse."
        return f"No. El bebedero tiene {nivel:.0f} por ciento de agua."

    return (
        "Puedo ayudarte con el nivel de agua, saber si el bebedero está lleno "
        "o vacío, consultar si hay suficiente agua y conocer el estado de la válvula."
    )


# =========================================================
# IDENTIFICAR ÓRDENES DE VÁLVULA
# =========================================================
def procesar_entrada(texto):
    texto_limpio = texto.lower().strip()

    ordenes_abrir = [
        "abre la válvula", "abre la valvula", "abrir válvula",
        "abrir valvula", "llena el bebedero", "comienza a llenar",
        "inicia el llenado", "enciende el llenado"
    ]
    ordenes_cerrar = [
        "cierra la válvula", "cierra la valvula", "cerrar válvula",
        "cerrar valvula", "detén el llenado", "deten el llenado",
        "para el llenado", "detén el suministro", "deten el suministro"
    ]

    if any(frase in texto_limpio for frase in ordenes_abrir):
        if publicar_comando("VALVULA_ABRIR"):
            return "Orden enviada: se solicitó abrir la válvula. Estoy esperando la confirmación del ESP32."
        return "No pude enviar la orden. Comprueba la conexión MQTT del ESP32 y de la aplicación."

    if any(frase in texto_limpio for frase in ordenes_cerrar):
        if publicar_comando("VALVULA_CERRAR"):
            return "Orden enviada: se solicitó cerrar la válvula. Estoy esperando la confirmación del ESP32."
        return "No pude enviar la orden. Comprueba la conexión MQTT del ESP32 y de la aplicación."

    return responder_pregunta(texto)


def hablar_respuesta(texto):
    try:
        audio = BytesIO()
        tts = gTTS(text=texto, lang="es")
        tts.write_to_fp(audio)
        audio.seek(0)
        st.audio(audio, format="audio/mp3")
    except Exception:
        st.warning("No se pudo generar el audio. Puedes leer la respuesta en pantalla.")


def mostrar_respuesta(texto):
    st.session_state["ultima_respuesta_usuario"] = texto
    st.session_state["historial"].append({
        "tipo": "GranjaConecta",
        "texto": texto
    })


# =========================================================
# INTERFAZ
# =========================================================
if "historial" not in st.session_state:
    st.session_state["historial"] = []

if "ultima_respuesta_usuario" not in st.session_state:
    st.session_state["ultima_respuesta_usuario"] = ""

st.markdown('<div class="titulo">🐔 GranjaConecta · Bebedero inteligente</div>', unsafe_allow_html=True)
st.write("Consulta el nivel de agua y controla la válvula mediante voz o texto.")

if estado_mqtt["conectado"]:
    st.success("Conectado al sistema MQTT")
else:
    st.warning("Conectando con el ESP32...")
    if estado_mqtt["error"]:
        st.caption(estado_mqtt["error"])

@st.fragment(run_every="2s")
def mostrar_estado_bebedero():
    datos = estado_mqtt["telemetria"]
    nivel = obtener_nivel(datos)
    valvula = obtener_valvula(datos)

    col_grafico, col_estado = st.columns([1.5, 1])

    with col_grafico:
        st.subheader("💧 Estado del bebedero")

        if nivel is None:
            st.info("Esperando la primera lectura del sensor de nivel de agua.")
            porcentaje = 0
        else:
            porcentaje = int(nivel)

        # Gráfico ilustrativo del nivel del agua.
        st.markdown(f"""
        <div style="
            height:230px; width:100%; position:relative; overflow:hidden;
            background:#f8fcff; border:4px solid #6c9eae; border-radius:18px;
            display:flex; align-items:flex-end;">
            <div style="
                width:100%; height:{porcentaje}%;
                background:linear-gradient(180deg,#80d8ed,#2196c7);
                transition:height .5s;">
            </div>
            <div style="
                position:absolute; top:12px; left:0; width:100%;
                text-align:center; color:#17472d; font-size:25px;
                font-weight:800; text-shadow:0 1px 2px white;">
                {porcentaje if nivel is not None else "—"}%
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_estado:
        st.subheader("📊 Datos del sensor")
        st.metric("Nivel de agua", f"{nivel:.0f} %" if nivel is not None else "Sin lectura")
        st.metric("Estado de la válvula", valvula)
        if nivel is not None:
            if nivel <= NIVEL_BAJO:
                st.error("Nivel bajo: revisar el suministro de agua.")
            elif nivel >= NIVEL_LLENO:
                st.success("Bebedero lleno.")
            else:
                st.info("Nivel de agua registrado.")

mostrar_estado_bebedero()

st.divider()
st.subheader("🎙️ Habla o escribe a GranjaConecta")
st.write("Puedes hacer preguntas sobre el bebedero o dar órdenes para abrir y cerrar la válvula.")

col_voz, col_texto = st.columns(2)

with col_voz:
    st.markdown("#### 🎤 Hablar")
    texto_voz = speech_to_text(
        language="es",
        start_prompt="Iniciar grabación",
        stop_prompt="Detener grabación",
        just_once=True,
        key="microfono_bebedero"
    )
    if texto_voz:
        st.write("**Reconocí:**", texto_voz)
        respuesta = procesar_entrada(texto_voz)
        mostrar_respuesta(respuesta)
        hablar_respuesta(respuesta)

with col_texto:
    st.markdown("#### ⌨️ Escribir")
    with st.form("formulario_bebedero", clear_on_submit=True):
        texto_escrito = st.text_input(
            "Escribe una pregunta u orden",
            placeholder="Ej. ¿Cuánta agua tiene el bebedero?"
        )
        enviar = st.form_submit_button("Enviar mensaje", use_container_width=True)

    if enviar and texto_escrito.strip():
        respuesta = procesar_entrada(texto_escrito)
        mostrar_respuesta(respuesta)
        st.success("Mensaje procesado.")
        st.markdown(f'<div class="mensaje">{respuesta}</div>', unsafe_allow_html=True)
        hablar_respuesta(respuesta)

if st.session_state["ultima_respuesta_usuario"]:
    st.markdown("### 💬 Última respuesta de GranjaConecta")
    st.markdown(
        f'<div class="mensaje">{st.session_state["ultima_respuesta_usuario"]}</div>',
        unsafe_allow_html=True
    )

with st.expander("📖 Preguntas y órdenes disponibles"):
    st.markdown("""
    **Preguntas**
    - ¿Cuánta agua tiene el bebedero?
    - ¿El bebedero está lleno?
    - ¿Hay suficiente agua para las gallinas?
    - ¿El bebedero está vacío?
    - ¿La válvula está abierta?
    - ¿La válvula está cerrada?
    - ¿Necesita agua el bebedero?

    **Órdenes**
    - Abre la válvula.
    - Cierra la válvula.
    - Llena el bebedero.
    - Detén el llenado.
    """)

with st.expander("🗨️ Historial de conversación"):
    if not st.session_state["historial"]:
        st.caption("Todavía no hay mensajes.")
    else:
        for mensaje in st.session_state["historial"][-12:]:
            st.markdown(f"**{mensaje['tipo']}:** {mensaje['texto']}")

st.caption(
    "GranjaConecta controla únicamente la válvula del bebedero. "
    "Las respuestas sobre el nivel y el estado dependen de la telemetría recibida del ESP32."
)
