
import streamlit as st
import json
import time
from datetime import datetime
import streamlit.components.v1 as components

try:
    import paho.mqtt.publish as mqtt_publish
    import paho.mqtt.subscribe as mqtt_subscribe
    MQTT_DISPONIBLE = True
except ImportError:
    MQTT_DISPONIBLE = False


# --------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------

st.set_page_config(
    page_title="GranjaConecta | Corral",
    page_icon="🐄",
    layout="wide"
)

BROKER = "broker.hivemq.com"
PUERTO = 1883

TOPIC_COMANDOS = "granjaconecta/comandos"
TOPIC_TELEMETRIA = "granjaconecta/telemetria"
TOPIC_RESPUESTAS = "granjaconecta/respuestas"


# --------------------------------------------------
# ESTILOS
# --------------------------------------------------

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #f5fff8, #e9f7ed);
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #123d2b, #1d593b);
}

section[data-testid="stSidebar"] * {
    color: white !important;
}

h1, h2, h3 {
    color: #174b32;
}

p {
    color: #365b45;
}

div.stButton > button {
    background: #a7dc45;
    color: #153b26;
    border: none;
    border-radius: 10px;
    font-weight: bold;
    padding: 0.65rem 1rem;
}

div.stButton > button:hover {
    background: #8fc52e;
    color: #153b26;
    border: none;
}

div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #d8eadc;
    border-radius: 12px;
    padding: 15px;
}

.tarjeta {
    background: white;
    border: 1px solid #d8eadc;
    border-radius: 15px;
    padding: 20px;
    margin-bottom: 12px;
}

.subtitulo {
    color: #5d8068;
    font-size: 15px;
}
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# FUNCIONES MQTT
# --------------------------------------------------

def publicar_comando(datos):
    """Envía un comando al ESP32 mediante MQTT."""

    if not MQTT_DISPONIBLE:
        st.error("No está instalada la librería paho-mqtt.")
        return False

    try:
        mqtt_publish.single(
            TOPIC_COMANDOS,
            payload=json.dumps(datos),
            hostname=BROKER,
            port=PUERTO
        )
        return True

    except Exception as error:
        st.error(f"No se pudo enviar el comando: {error}")
        return False


def crear_mensaje(comando, valor, **otros):
    mensaje = {
        "seccion": "corral",
        "comando": comando,
        "valor": valor,
        "origen": "streamlit",
        "timestamp": datetime.now().isoformat()
    }

    mensaje.update(otros)
    return mensaje


def enviar_puerta(accion):
    angulo = 90 if accion == "abrir" else 0

    datos = crear_mensaje(
        "puerta",
        accion,
        angulo=angulo
    )

    if publicar_comando(datos):
        st.success(f"Comando enviado: puerta {accion}.")


def enviar_ventilacion(porcentaje):
    porcentaje = int(porcentaje)
    pwm = int(porcentaje * 255 / 100)

    datos = crear_mensaje(
        "ventilacion",
        porcentaje,
        porcentaje=porcentaje,
        pwm=pwm
    )

    if publicar_comando(datos):
        st.success(f"Ventilación ajustada al {porcentaje}%.")


def enviar_gesto(gesto, accion, **otros):
    datos = crear_mensaje(
        "gesto",
        gesto,
        accion=accion,
        **otros
    )

    if publicar_comando(datos):
        st.success("Comando del gesto enviado al ESP32.")


def recibir_telemetria(topic):
    """Lee el último mensaje disponible del tópico MQTT."""

    if not MQTT_DISPONIBLE:
        st.error("No está instalada la librería paho-mqtt.")
        return None

    try:
        mensaje = mqtt_subscribe.simple(
            topic,
            hostname=BROKER,
            port=PUERTO,
            timeout=5
        )

        contenido = mensaje.payload.decode("utf-8")
        return json.loads(contenido)

    except Exception as error:
        st.warning(
            "No se recibió información. "
            "Verifica que el ESP32 esté conectado y publicando datos."
        )
        return None


# --------------------------------------------------
# BARRA LATERAL
# --------------------------------------------------

with st.sidebar:
    st.markdown("## 🌱 GranjaConecta")
    st.caption("Tecnología para el campo")

    st.markdown("---")

    st.markdown("### Navegación")

    st.page_link("Inicioapp.py", label="🏠 Inicio")
    st.page_link("pages/1_Bebedero.py", label="💧 Bebedero")
    st.page_link("pages/2_Corral.py", label="🐄 Corral")

    st.markdown("---")

    st.markdown("### Conexión")
    st.caption(f"Broker: {BROKER}")
    st.caption(f"Puerto: {PUERTO}")

    if MQTT_DISPONIBLE:
        st.success("Librería MQTT disponible")
    else:
        st.error("Falta instalar paho-mqtt")


# --------------------------------------------------
# ENCABEZADO
# --------------------------------------------------

st.markdown("""
<div style="
    background: linear-gradient(110deg, #164b32, #287447);
    padding: 28px;
    border-radius: 18px;
    color: white;
    margin-bottom: 22px;
">
    <div style="
        color: #b7e85b;
        font-size: 13px;
        font-weight: bold;
        letter-spacing: 2px;
    ">
        GRANJACONECTA
    </div>

    <h1 style="color:white; margin-bottom:5px;">
        🐄 Control inteligente del corral
    </h1>

    <p style="color:#e4f4e8; margin-bottom:0;">
        Supervisa y controla las condiciones del corral
        mediante tecnología IoT.
    </p>
</div>
""", unsafe_allow_html=True)


# --------------------------------------------------
# INDICADORES
# --------------------------------------------------

st.markdown("### Panel de control")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("🚪 Puerta", "Control servo")

with col2:
    st.metric("🌬️ Ventilación", "Control PWM")

with col3:
    st.metric("📡 Comunicación", "MQTT")


st.markdown("---")


# --------------------------------------------------
# PESTAÑAS
# --------------------------------------------------

tab_puerta, tab_ventilacion, tab_gestos, tab_telemetria = st.tabs([
    "🚪 Puerta",
    "🌬️ Ventilación",
    "🖐️ Gestos",
    "📊 Telemetría"
])


# --------------------------------------------------
# PESTAÑA PUERTA
# --------------------------------------------------

with tab_puerta:

    st.markdown("### Control de la puerta")
    st.write(
        "Controla la apertura y el cierre de la puerta "
        "del corral mediante un servomotor."
    )

    izquierda, derecha = st.columns(2)

    with izquierda:
        st.markdown("""
        <div class="tarjeta">
            <h3>🔓 Abrir puerta</h3>
            <p class="subtitulo">
                Envía la orden para llevar el servo a 90°.
            </p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Abrir puerta", key="abrir_puerta",
                     use_container_width=True):
            enviar_puerta("abrir")

    with derecha:
        st.markdown("""
        <div class="tarjeta">
            <h3>🔒 Cerrar puerta</h3>
            <p class="subtitulo">
                Envía la orden para llevar el servo a 0°.
            </p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Cerrar puerta", key="cerrar_puerta",
                     use_container_width=True):
            enviar_puerta("cerrar")

    st.info(
        "El servo de la puerta está conectado al GPIO 19 del ESP32. "
        "0° corresponde a cerrada y 90° a abierta."
    )


# --------------------------------------------------
# PESTAÑA VENTILACIÓN
# --------------------------------------------------

with tab_ventilacion:

    st.markdown("### Control de ventilación")

    st.write(
        "Ajusta el nivel de ventilación del corral. "
        "El sistema utiliza una señal PWM."
    )

    porcentaje = st.select_slider(
        "Selecciona el nivel de ventilación",
        options=[0, 25, 50, 75, 100],
        value=50,
        format_func=lambda x: f"{x}%"
    )

    pwm = int(porcentaje * 255 / 100)

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Ventilación", f"{porcentaje}%")

    with col2:
        st.metric("Valor PWM", pwm)

    st.progress(porcentaje / 100)

    if st.button(
        "Aplicar ventilación",
        key="aplicar_ventilacion",
        use_container_width=True
    ):
        enviar_ventilacion(porcentaje)

    st.caption(
        "El control PWM utiliza el GPIO 25 del ESP32. "
        "El valor va de 0 a 255."
    )


# --------------------------------------------------
# PESTAÑA GESTOS
# --------------------------------------------------

with tab_gestos:

    st.markdown("### Reconocimiento de gestos")

    st.write(
        "Estos botones permiten probar las acciones que "
        "posteriormente se podrán activar mediante reconocimiento "
        "automático de la mano."
    )

    st.warning(
        "Por ahora son botones de prueba. "
        "Todavía no se encuentra implementada la detección "
        "automática mediante cámara."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="tarjeta">
            <h3>✋ Mano abierta</h3>
            <p class="subtitulo">
                Acción: abrir la puerta del corral.
            </p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Probar mano abierta",
                     key="gesto_mano_abierta",
                     use_container_width=True):

            enviar_gesto(
                "mano_abierta",
                "abrir_puerta",
                angulo=90
            )

        st.markdown("""
        <div class="tarjeta">
            <h3>👍 Pulgar arriba</h3>
            <p class="subtitulo">
                Acción: aumentar la ventilación.
            </p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Probar pulgar arriba",
                     key="gesto_pulgar_arriba",
                     use_container_width=True):

            nuevo = min(
                st.session_state.get("nivel_ventilacion", 50) + 25,
                100
            )

            st.session_state.nivel_ventilacion = nuevo

            enviar_gesto(
                "pulgar_arriba",
                "aumentar_ventilacion",
                porcentaje=nuevo,
                pwm=int(nuevo * 255 / 100)
            )

    with col2:
        st.markdown("""
        <div class="tarjeta">
            <h3>✊ Puño cerrado</h3>
            <p class="subtitulo">
                Acción: cerrar la puerta del corral.
            </p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Probar puño cerrado",
                     key="gesto_puno",
                     use_container_width=True):

            enviar_gesto(
                "puno_cerrado",
                "cerrar_puerta",
                angulo=0
            )

        st.markdown("""
        <div class="tarjeta">
            <h3>👎 Pulgar abajo</h3>
            <p class="subtitulo">
                Acción: disminuir la ventilación.
            </p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Probar pulgar abajo",
                     key="gesto_pulgar_abajo",
                     use_container_width=True):

            nuevo = max(
                st.session_state.get("nivel_ventilacion", 50) - 25,
                0
            )

            st.session_state.nivel_ventilacion = nuevo

            enviar_gesto(
                "pulgar_abajo",
                "disminuir_ventilacion",
                porcentaje=nuevo,
                pwm=int(nuevo * 255 / 100)
            )


# --------------------------------------------------
# PESTAÑA TELEMETRÍA
# --------------------------------------------------

with tab_telemetria:

    st.markdown("### Información del corral")

    st.write(
        "Consulta los datos que el ESP32 envía al sistema "
        "mediante MQTT."
    )

    st.markdown("#### Datos recibidos")

    if st.button(
        "🔄 Consultar telemetría",
        key="consultar_telemetria",
        use_container_width=True
    ):

        datos = recibir_telemetria(TOPIC_TELEMETRIA)

        if datos is not None:

            st.session_state["telemetria_corral"] = datos
            st.success("Telemetría recibida correctamente.")

    datos_guardados = st.session_state.get(
        "telemetria_corral"
    )

    if datos_guardados:

        st.json(datos_guardados)

        # Mostrar algunos valores si vienen en el JSON.
        col1, col2, col3 = st.columns(3)

        with col1:
            temperatura = datos_guardados.get("temperatura", "N/D")
            st.metric("🌡️ Temperatura", temperatura)

        with col2:
            humedad = datos_guardados.get("humedad", "N/D")
            st.metric("💧 Humedad", humedad)

        with col3:
            nivel = datos_guardados.get("nivel_agua", "N/D")
            st.metric("📊 Nivel de agua", nivel)

    else:
        st.info(
            "Todavía no hay datos guardados. "
            "Presiona 'Consultar telemetría' para recibir información."
        )

    st.caption(f"Tópico: {TOPIC_TELEMETRIA}")


# --------------------------------------------------
# PIE DE PÁGINA
# --------------------------------------------------

st.markdown("---")

st.markdown("""
<div style="text-align:center; padding:15px;">
    <p style="color:#64836d; font-size:13px;">
        GranjaConecta | Tecnología para el campo 🌱
    </p>
</div>
""", unsafe_allow_html=True)
