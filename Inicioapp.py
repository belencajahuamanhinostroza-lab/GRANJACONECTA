
import base64
import json
import queue
import threading
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


# =========================================================
# 1. CONFIGURACIÓN GENERAL
# =========================================================

st.set_page_config(
    page_title="GranjaConecta",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

CARPETA = Path(__file__).parent
IMAGEN_FONDO = CARPETA / "fondogranja.jpg"

MQTT_BROKER = "broker.mqttdashboard.com"
MQTT_PORT = 1883
MQTT_TOPIC = "granjaconecta"


# =========================================================
# 2. ESTILOS GENERALES
# =========================================================

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700;800;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Nunito', sans-serif;
}

.stApp {
    background: #f5f8f1;
    color: #294332;
}

header[data-testid="stHeader"] {
    background: transparent;
}

[data-testid="stSidebar"] {
    background: #e5efdc;
    border-right: 1px solid #d2dfc9;
}

[data-testid="stSidebar"] * {
    color: #294332;
}

h1, h2, h3 {
    color: #315b3d;
    font-weight: 900;
}

p {
    color: #526b56;
}

.hero {
    padding: 65px 45px;
    border-radius: 25px;
    background:
        linear-gradient(
            90deg,
            rgba(20, 54, 34, 0.85),
            rgba(20, 54, 34, 0.30)
        ),
        var(--hero-image);
    background-size: cover;
    background-position: center;
    min-height: 310px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    color: white;
    box-shadow: 0 8px 25px rgba(35, 70, 40, 0.12);
}

.hero h1 {
    color: white !important;
    font-size: 48px;
    margin-bottom: 8px;
}

.hero p {
    color: white !important;
    font-size: 18px;
    max-width: 650px;
}

.subtitulo {
    color: #78916e;
    font-size: 13px;
    font-weight: 900;
    letter-spacing: 2px;
    text-transform: uppercase;
}

.tarjeta {
    background: white;
    border: 1px solid #e3ebdf;
    border-radius: 20px;
    padding: 25px;
    min-height: 205px;
    box-shadow: 0 5px 18px rgba(43, 76, 47, 0.06);
}

.tarjeta h3 {
    margin-top: 5px;
}

.tarjeta p {
    font-size: 15px;
}

.stButton > button {
    background: #4c8053;
    color: white !important;
    border: none;
    border-radius: 12px;
    padding: 10px 20px;
    font-weight: 800;
    transition: 0.2s;
}

.stButton > button:hover {
    background: #315e3a;
    color: white !important;
    border: none;
}

.metrica {
    background: white;
    border: 1px solid #e3ebdf;
    padding: 20px;
    border-radius: 18px;
    text-align: center;
    min-height: 125px;
}

.metrica-titulo {
    font-size: 14px;
    font-weight: 800;
    color: #71866c;
}

.metrica-valor {
    font-size: 32px;
    font-weight: 900;
    color: #315b3d;
}

.estado {
    font-size: 13px;
    font-weight: 900;
    margin-top: 3px;
}

.pie {
    text-align: center;
    color: #82947c;
    padding: 30px 10px;
    font-size: 13px;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# 3. IMAGEN DE FONDO
# =========================================================

imagen_base64 = ""

if IMAGEN_FONDO.exists():
    with open(IMAGEN_FONDO, "rb") as archivo:
        imagen_base64 = base64.b64encode(
            archivo.read()
        ).decode()

if imagen_base64:
    imagen_css = f"url('data:image/jpeg;base64,{imagen_base64}')"
else:
    imagen_css = "linear-gradient(120deg, #719b68, #b9cf9e)"

st.markdown(
    f"""
    <style>
    .hero {{
        --hero-image: {imagen_css};
    }}
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# 4. CONEXIÓN MQTT
# =========================================================

@st.cache_resource
def iniciar_mqtt():

    mensajes = queue.Queue()
    estado_conexion = {
        "conectado": False,
        "error": ""
    }

    try:
        import paho.mqtt.client as mqtt

        def al_conectar(
            cliente,
            userdata,
            flags,
            reason_code,
            properties
        ):
            if reason_code == 0:
                estado_conexion["conectado"] = True
                estado_conexion["error"] = ""

                cliente.subscribe(MQTT_TOPIC)

            else:
                estado_conexion["conectado"] = False
                estado_conexion["error"] = (
                    f"Error de conexión MQTT: {reason_code}"
                )

        def al_desconectar(
            cliente,
            userdata,
            disconnect_flags,
            reason_code,
            properties
        ):
            estado_conexion["conectado"] = False

        def al_recibir(cliente, userdata, mensaje):

            try:
                contenido = mensaje.payload.decode("utf-8")
                mensajes.put(contenido)

            except Exception:
                pass

        cliente = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="GRANJACONECTA-INICIO",
            protocol=mqtt.MQTTv311,
            clean_session=True
        )

        cliente.on_connect = al_conectar
        cliente.on_disconnect = al_desconectar
        cliente.on_message = al_recibir

        cliente.connect_async(
            MQTT_BROKER,
            MQTT_PORT,
            keepalive=60
        )

        cliente.loop_start()

        return cliente, mensajes, estado_conexion

    except Exception as error:

        estado_conexion["conectado"] = False
        estado_conexion["error"] = str(error)

        return None, mensajes, estado_conexion


cliente_mqtt, cola_mqtt, conexion_mqtt = iniciar_mqtt()


# =========================================================
# 5. VARIABLES DE SESIÓN
# =========================================================

if "telemetria_granja" not in st.session_state:
    st.session_state.telemetria_granja = {
        "temperatura": None,
        "humedad": None
    }


if "ultimo_mensaje_granja" not in st.session_state:
    st.session_state.ultimo_mensaje_granja = ""


def procesar_mensajes():

    while True:

        try:
            mensaje = cola_mqtt.get_nowait()

        except queue.Empty:
            break

        try:
            paquete = json.loads(mensaje)

            if paquete.get("tipo") != "telemetria":
                continue

            datos = paquete.get("datos", paquete)

            temperatura = datos.get("temperatura")
            humedad = datos.get("humedad")

            if temperatura is not None:
                st.session_state.telemetria_granja[
                    "temperatura"
                ] = float(temperatura)

            if humedad is not None:
                st.session_state.telemetria_granja[
                    "humedad"
                ] = float(humedad)

            st.session_state.ultimo_mensaje_granja = mensaje

        except (ValueError, TypeError, json.JSONDecodeError):
            continue


# =========================================================
# 6. CLASIFICACIÓN DE LOS VALORES
# =========================================================

def clasificar_valor(valor):

    if valor is None:
        return "SIN DATOS"

    if valor < 20:
        return "BAJA"

    elif valor >= 35:
        return "ALTA"

    return "NORMAL"


def obtener_estado_granja(temperatura, humedad):

    if temperatura is None and humedad is None:
        return "espera"

    valores = [
        valor
        for valor in [temperatura, humedad]
        if valor is not None
    ]

    # Si algún valor es alto, se prioriza el estado amarillo.
    if any(valor >= 35 for valor in valores):
        return "alto"

    # Si algún valor es bajo, se muestra el estado azul.
    if any(valor < 20 for valor in valores):
        return "bajo"

    return "normal"


# =========================================================
# 7. ILUSTRACIÓN DE LA GRANJA
# =========================================================

def crear_ilustracion(estado):

    configuracion = {
        "normal": {
            "clase": "normal",
            "titulo": "AMBIENTE ESTABLE",
            "descripcion": "Las lecturas se encuentran dentro del rango normal.",
            "emoji": "🌿"
        },
        "bajo": {
            "clase": "bajo",
            "titulo": "VALOR BAJO DETECTADO",
            "descripcion": "La temperatura o humedad presenta un valor bajo.",
            "emoji": "❄️"
        },
        "alto": {
            "clase": "alto",
            "titulo": "VALOR ALTO DETECTADO",
            "descripcion": "La temperatura o humedad presenta un valor alto.",
            "emoji": "☀️"
        },
        "espera": {
            "clase": "espera",
            "titulo": "ESPERANDO DATOS DEL ESP32",
            "descripcion": "Conecta Wokwi para visualizar el estado de la granja.",
            "emoji": "📡"
        }
    }

    datos = configuracion[estado]

    return f"""
    <html>
    <head>
    <meta charset="UTF-8">

    <style>

    * {{
        box-sizing: border-box;
    }}

    body {{
        margin: 0;
        padding: 0;
        font-family: Arial, sans-serif;
        background: transparent;
    }}

    .escena {{
        width: 100%;
        height: 430px;
        overflow: hidden;
        border-radius: 22px;
        position: relative;
        background: #dcebd3;
        border: 2px solid rgba(80, 110, 70, 0.15);
    }}

    .paisaje {{
        width: 100%;
        height: 100%;
        display: block;
    }}

    .normal {{
        --cielo1: #8fd5ee;
        --cielo2: #d8f1ec;
        --montana: #8eae83;
        --pasto: #78b76d;
        --pasto2: #a5d17d;
        --granero: #c95e48;
        --techo: #853c35;
        --camino: #d8bf91;
        --arbol: #4d8e50;
        --sol: #ffe58b;
    }}

    .bajo {{
        --cielo1: #4f9cc8;
        --cielo2: #b5d8ed;
        --montana: #6d91b0;
        --pasto: #76a9b4;
        --pasto2: #a6cbd2;
        --granero: #527f9e;
        --techo: #345c7d;
        --camino: #b4c9d0;
        --arbol: #598b91;
        --sol: #d7ecf5;
    }}

    .alto {{
        --cielo1: #f3c05d;
        --cielo2: #ffe7a5;
        --montana: #d9ad68;
        --pasto: #c8a64d;
        --pasto2: #e5c76c;
        --granero: #c87936;
        --techo: #98502b;
        --camino: #e5c17d;
        --arbol: #a5a34c;
        --sol: #fff3a0;
    }}

    .espera {{
        --cielo1: #b9c7c0;
        --cielo2: #e2e9df;
        --montana: #9eae9a;
        --pasto: #9eaf8d;
        --pasto2: #b9c6a4;
        --granero: #9d8d77;
        --techo: #716657;
        --camino: #c8b99b;
        --arbol: #788d68;
        --sol: #e5dfb6;
    }}

    .cielo {{
        fill: url(#gradienteCielo);
    }}

    .montana {{
        fill: var(--montana);
    }}

    .pasto {{
        fill: var(--pasto);
    }}

    .pasto2 {{
        fill: var(--pasto2);
    }}

    .granero {{
        fill: var(--granero);
        stroke: #603e35;
        stroke-width: 3;
    }}

    .techo {{
        fill: var(--techo);
        stroke: #603e35;
        stroke-width: 3;
    }}

    .camino {{
        fill: var(--camino);
    }}

    .arbol {{
        fill: var(--arbol);
    }}

    .sol {{
        fill: var(--sol);
    }}

    .nube {{
        fill: rgba(255,255,255,0.8);
    }}

    .ventana {{
        fill: #f8e9b5;
        stroke: #603e35;
        stroke-width: 3;
    }}

    .puerta {{
        fill: #744737;
        stroke: #50352e;
        stroke-width: 3;
    }}

    .cerca {{
        stroke: #f4e5c5;
        stroke-width: 8;
        stroke-linecap: round;
        fill: none;
    }}

    .etiqueta {{
        position: absolute;
        top: 15px;
        left: 15px;
        right: 15px;
        padding: 12px 15px;
        border-radius: 13px;
        background: rgba(255,255,255,0.87);
        color: #34513b;
        font-weight: 900;
        font-size: 14px;
        text-align: center;
        letter-spacing: 0.5px;
    }}

    .descripcion {{
        font-size: 12px;
        font-weight: 600;
        display: block;
        margin-top: 4px;
        color: #657665;
    }}

    .animales {{
        font-size: 35px;
    }}

    </style>
    </head>

    <body>

    <div class="escena {datos['clase']}">

        <div class="etiqueta">
            {datos['emoji']} {datos['titulo']}
            <span class="descripcion">{datos['descripcion']}</span>
        </div>

        <svg class="paisaje" viewBox="0 0 1000 430"
             preserveAspectRatio="xMidYMid slice">

            <defs>
                <linearGradient id="gradienteCielo"
                    x1="0" y1="0" x2="0" y2="1">

                    <stop offset="0%" stop-color="var(--cielo1)"/>
                    <stop offset="100%" stop-color="var(--cielo2)"/>

                </linearGradient>
            </defs>

            <!-- CIELO -->
            <rect width="1000" height="430" class="cielo"/>

            <!-- SOL -->
            <circle cx="830" cy="105" r="48" class="sol"/>

            <!-- NUBES -->
            <g class="nube">
                <ellipse cx="180" cy="105" rx="65" ry="22"/>
                <ellipse cx="220" cy="90" rx="35" ry="28"/>
                <ellipse cx="255" cy="108" rx="45" ry="20"/>

                <ellipse cx="560" cy="125" rx="60" ry="20"/>
                <ellipse cx="595" cy="110" rx="35" ry="25"/>
                <ellipse cx="630" cy="127" rx="42" ry="18"/>
            </g>

            <!-- MONTAÑAS -->
            <path d="
                M0 250
                L130 145
                L240 235
                L365 125
                L520 245
                L680 150
                L830 250
                L930 165
                L1000 220
                L1000 430
                L0 430 Z"
                class="montana"/>

            <!-- PASTO DEL FONDO -->
            <path d="
                M0 260
                Q200 220 390 265
                Q650 215 1000 260
                L1000 430
                L0 430 Z"
                class="pasto"/>

            <!-- CAMINO -->
            <path d="
                M390 430
                Q450 335 510 315
                Q560 290 610 260
                Q570 350 620 430 Z"
                class="camino"/>

            <!-- COLINAS -->
            <path d="
                M0 315
                Q180 255 350 310
                Q570 360 760 300
                Q890 260 1000 310
                L1000 430 L0 430 Z"
                class="pasto2"/>

            <!-- ÁRBOLES IZQUIERDOS -->
            <g>
                <rect x="75" y="235" width="18" height="80" fill="#79543b"/>
                <circle cx="84" cy="215" r="42" class="arbol"/>
                <circle cx="58" cy="235" r="28" class="arbol"/>
                <circle cx="108" cy="237" r="28" class="arbol"/>

                <rect x="920" y="235" width="18" height="80" fill="#79543b"/>
                <circle cx="929" cy="215" r="42" class="arbol"/>
                <circle cx="900" cy="238" r="28" class="arbol"/>
                <circle cx="955" cy="237" r="28" class="arbol"/>
            </g>

            <!-- GRANERO GRANDE -->
            <g>
                <rect x="330" y="190" width="220" height="145"
                    rx="4" class="granero"/>

                <path d="
                    M300 195
                    L440 105
                    L580 195 Z"
                    class="techo"/>

                <rect x="410" y="255" width="62" height="80"
                    rx="3" class="puerta"/>

                <rect x="355" y="220" width="38" height="38"
                    class="ventana"/>

                <rect x="485" y="220" width="38" height="38"
                    class="ventana"/>

                <path d="M440 255 V335" stroke="#d8ad77" stroke-width="4"/>
                <path d="M410 280 H472" stroke="#d8ad77" stroke-width="4"/>
            </g>

            <!-- GRANERO PEQUEÑO IZQUIERDO -->
            <g>
                <rect x="125" y="245" width="130" height="90"
                    class="granero"/>

                <path d="M105 250 L190 190 L275 250 Z"
                    class="techo"/>

                <rect x="175" y="285" width="35" height="50"
                    class="puerta"/>

                <rect x="140" y="265" width="24" height="24"
                    class="ventana"/>
            </g>

            <!-- GRANERO PEQUEÑO DERECHO -->
            <g>
                <rect x="690" y="245" width="135" height="90"
                    class="granero"/>

                <path d="M670 250 L757 190 L845 250 Z"
                    class="techo"/>

                <rect x="740" y="285" width="35" height="50"
                    class="puerta"/>

                <rect x="710" y="265" width="24" height="24"
                    class="ventana"/>
            </g>

            <!-- CERCA -->
            <path d="
                M0 355 H1000
                M0 380 H1000"
                class="cerca"/>

            <g stroke="#e8d8b5" stroke-width="9">
                <path d="M100 340 V400"/>
                <path d="M240 340 V400"/>
                <path d="M380 340 V400"/>
                <path d="M520 340 V400"/>
                <path d="M660 340 V400"/>
                <path d="M800 340 V400"/>
                <path d="M940 340 V400"/>
            </g>

            <!-- ANIMALES -->
            <g class="animales">

                <text x="265" y="355">🐄</text>
                <text x="560" y="355">🐑</text>
                <text x="620" y="385">🐔</text>
                <text x="840" y="355">🐄</text>
                <text x="170" y="395">🐓</text>

            </g>

            <!-- FLORES -->
            <g font-size="22">
                <text x="35" y="330">🌼</text>
                <text x="285" y="410">🌸</text>
                <text x="680" y="420">🌼</text>
                <text x="970" y="330">🌻</text>
            </g>

        </svg>

    </div>

    </body>
    </html>
    """


# =========================================================
# 8. MENÚ LATERAL
# =========================================================

with st.sidebar:

    st.markdown(
        "<h2>🌾 GranjaConecta</h2>",
        unsafe_allow_html=True
    )

    st.markdown("---")

    st.markdown("### Menú principal")

    if st.button("🏡 Inicio", use_container_width=True):
        st.switch_page("Inicioapp.py")

    if st.button("🐄 Corral inteligente", use_container_width=True):
        st.switch_page("pages/2_Corral.py")

    if st.button("💧 Bebedero inteligente", use_container_width=True):
        st.switch_page("pages/1_Bebedero.py")

    st.markdown("---")

    if conexion_mqtt["conectado"]:
        st.success("MQTT conectado")
    else:
        st.warning("Conectando con MQTT...")

    st.caption(f"Servidor: {MQTT_BROKER}")
    st.caption(f"Tópico: {MQTT_TOPIC}")


# =========================================================
# 9. PORTADA
# =========================================================

st.markdown("""
<div class="hero">

    <div class="subtitulo" style="color:#e3f2d8;">
        TECNOLOGÍA PARA EL CAMPO
    </div>

    <h1>GranjaConecta 🌾</h1>

    <p>
        Una granja inteligente que conecta tecnología,
        monitoreo y automatización para facilitar el
        cuidado de los animales y sus espacios.
    </p>

</div>
""", unsafe_allow_html=True)


st.write("")


# =========================================================
# 10. PRESENTACIÓN
# =========================================================

st.markdown(
    '<div class="subtitulo">BIENVENIDO A TU GRANJA</div>',
    unsafe_allow_html=True
)

st.markdown("## Una granja más conectada e inteligente")

st.markdown("""
GranjaConecta permite visualizar y supervisar diferentes
espacios de una granja desde una sola plataforma.

Consulta las condiciones ambientales, revisa el estado
del corral y controla el funcionamiento del bebedero.
""")


st.write("")


# =========================================================
# 11. MONITOREO AMBIENTAL DE LA GRANJA
# =========================================================

@st.fragment(run_every="2s")
def mostrar_monitoreo():

    procesar_mensajes()

    temperatura = st.session_state.telemetria_granja[
        "temperatura"
    ]

    humedad = st.session_state.telemetria_granja[
        "humedad"
    ]

    estado = obtener_estado_granja(
        temperatura,
        humedad
    )

    st.markdown(
        '<div class="subtitulo">MONITOREO EN TIEMPO REAL</div>',
        unsafe_allow_html=True
    )

    st.markdown("## 🌤️ Así se encuentra tu granja")

    st.markdown("""
    La ilustración cambia de apariencia según las lecturas
    de temperatura y humedad recibidas desde el sensor.
    """)

    # ESTADO DE CONEXIÓN

    if conexion_mqtt["conectado"]:
        st.success("🟢 Conexión MQTT activa. Recibiendo información del ESP32.")
    else:
        st.warning("🟡 Esperando conexión con el ESP32 de Wokwi.")

        if conexion_mqtt["error"]:
            st.caption(conexion_mqtt["error"])

    # ILUSTRACIÓN

    html_granja = crear_ilustracion(estado)

    components.html(
        html_granja,
        height=440,
        scrolling=False
    )

    st.write("")

    # INDICADORES

    col1, col2 = st.columns(2)

    estado_temperatura = clasificar_valor(temperatura)
    estado_humedad = clasificar_valor(humedad)

    with col1:

        if temperatura is None:
            valor_temperatura = "--"
        else:
            valor_temperatura = f"{temperatura:.1f} °C"

        st.markdown(
            f"""
            <div class="metrica">
                <div class="metrica-titulo">🌡️ TEMPERATURA</div>
                <div class="metrica-valor">{valor_temperatura}</div>
                <div class="estado">{estado_temperatura}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:

        if humedad is None:
            valor_humedad = "--"
        else:
            valor_humedad = f"{humedad:.1f} %"

        st.markdown(
            f"""
            <div class="metrica">
                <div class="metrica-titulo">💧 HUMEDAD</div>
                <div class="metrica-valor">{valor_humedad}</div>
                <div class="estado">{estado_humedad}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.write("")

    if estado == "espera":
        st.info(
            "Todavía no se han recibido lecturas. "
            "Inicia la simulación en Wokwi y espera los datos."
        )

    elif estado == "bajo":
        st.info(
            "La granja muestra tonos azules porque al menos "
            "una de las lecturas está por debajo de 20."
        )

    elif estado == "alto":
        st.warning(
            "La granja muestra tonos amarillos porque al menos "
            "una de las lecturas es igual o superior a 35."
        )

    else:
        st.success(
            "La granja muestra tonos verdes porque las lecturas "
            "recibidas se encuentran entre 20 y menos de 35."
        )


mostrar_monitoreo()


st.write("")
st.markdown("---")


# =========================================================
# 12. TARJETAS DE FUNCIONALIDADES
# =========================================================

st.markdown(
    '<div class="subtitulo">EXPLORA LA PLATAFORMA</div>',
    unsafe_allow_html=True
)

st.markdown("## Conoce los espacios de GranjaConecta")

col1, col2 = st.columns(2, gap="large")


with col1:

    st.markdown("""
    <div class="tarjeta">

        <div style="font-size:42px;">🐄</div>

        <h3>Corral inteligente</h3>

        <p>
            Supervisa las condiciones del corral, consulta
            información ambiental y utiliza las funciones
            de monitoreo y control disponibles.
        </p>

    </div>
    """, unsafe_allow_html=True)

    if st.button(
        "Ingresar al corral →",
        key="ir_corral",
        use_container_width=True
    ):
        st.switch_page("pages/2_Corral.py")


with col2:

    st.markdown("""
    <div class="tarjeta">

        <div style="font-size:42px;">💧</div>

        <h3>Bebedero inteligente</h3>

        <p>
            Consulta el nivel de agua, identifica cuándo
            necesita llenarse y utiliza las funciones
            de apertura y cierre de la válvula.
        </p>

    </div>
    """, unsafe_allow_html=True)

    if st.button(
        "Ingresar al bebedero →",
        key="ir_bebedero",
        use_container_width=True
    ):
        st.switch_page("pages/1_Bebedero.py")


# =========================================================
# 13. PIE DE PÁGINA
# =========================================================

st.write("")
st.write("")

st.markdown("""
<div class="pie">

    🌾 <b>GranjaConecta</b>

    <br><br>

    Tecnología y monitoreo para una granja inteligente.

    <br>

    © 2026 GranjaConecta

</div>
""", unsafe_allow_html=True)
