
import base64
import json
import queue
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


# ==================================================
# CONFIGURACIÓN
# ==================================================

st.set_page_config(
    page_title="GranjaConecta",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

CARPETA = Path(__file__).resolve().parent
RUTA_IMAGEN = CARPETA / "fondogranja.jpg"

# MQTT: conexión con Wokwi
MQTT_BROKER = "broker.mqttdashboard.com"
MQTT_PORT = 1883
MQTT_TOPIC = "granjaconecta"


# ==================================================
# CARGAR IMAGEN
# ==================================================

def cargar_imagen(ruta):
    if not ruta.exists():
        return None

    extension = ruta.suffix.lower()
    tipos = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }

    tipo = tipos.get(extension)
    if tipo is None:
        return None

    with open(ruta, "rb") as archivo:
        contenido = base64.b64encode(archivo.read()).decode("utf-8")

    return f"data:{tipo};base64,{contenido}"


imagen_portada = cargar_imagen(RUTA_IMAGEN)


# ==================================================
# ESTILOS GENERALES DE STREAMLIT
# ==================================================

st.markdown(
    """
    <style>
    .stApp {
        background-color: #f4faf5;
        color: #183d2b;
    }

    [data-testid="stHeader"] {
        background-color: transparent;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1250px;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #123d2b 0%, #1c5638 100%);
    }

    [data-testid="stSidebar"] * {
        color: white;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: white;
    }

    .section-title {
        color: #17452e;
        font-size: 27px;
        font-weight: 800;
        margin-bottom: 8px;
    }

    .section-description {
        color: #61776a;
        font-size: 15px;
        line-height: 1.6;
        margin-bottom: 25px;
    }

    /* COLOR VERDE OSCURO PARA LOS INDICADORES */
    [data-testid="stMetric"] label,
    [data-testid="stMetric"] [data-testid="stMetricLabel"],
    [data-testid="stMetric"] [data-testid="stMetricValue"],
    [data-testid="stMetric"] [data-testid="stMetricDelta"],
    [data-testid="stMetric"] p {
        color: #17452e !important;
    }

    div.stButton > button {
        background-color: #c6f36a;
        color: #173d29;
        border: none;
        border-radius: 10px;
        padding: 11px 20px;
        font-weight: 800;
        min-height: 45px;
        transition: 0.2s ease;
    }

    div.stButton > button:hover {
        background-color: #d8ff8a;
        color: #123d29;
        border: none;
        transform: translateY(-2px);
    }

    .footer-line {
        height: 1px;
        background-color: #d8e8dc;
        margin-top: 45px;
        margin-bottom: 20px;
    }

    .footer-text {
        text-align: center;
        color: #789080;
        font-size: 12px;
        padding-bottom: 10px;
    }

    @media (max-width: 700px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ==================================================
# MENÚ LATERAL
# ==================================================

with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center; padding:20px 5px 25px 5px;">
            <div style="font-size:42px;">🌱</div>
            <div style="font-size:23px; font-weight:800; color:white;">
                GranjaConecta
            </div>
            <div style="font-size:11px; letter-spacing:2px; color:#c6f36a; margin-top:5px;">
                TECNOLOGÍA PARA EL CAMPO
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")
    st.markdown("### Navegación")

    st.page_link("Inicioapp.py", label="🏠 Inicio")
    st.page_link("pages/1_Bebedero.py", label="💧 Bebedero")
    st.page_link("pages/2_Corral.py", label="🐄 Corral")

    st.markdown("---")
    st.caption("Sistema inteligente para el cuidado animal")


# ==================================================
# PORTADA: HTML EN COMPONENTE INDEPENDIENTE
# ==================================================

if imagen_portada:
    fondo_css = f"background-image: linear-gradient(90deg, rgba(8,39,25,.88) 0%, rgba(12,54,33,.65) 55%, rgba(12,54,33,.10) 100%), url('{imagen_portada}');"
else:
    fondo_css = "background: linear-gradient(135deg, #174a32, #246642);"

html_portada = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
* {{ box-sizing: border-box; }}
html, body {{
    margin: 0;
    padding: 0;
    width: 100%;
    font-family: Arial, Helvetica, sans-serif;
}}
.hero {{
    width: 100%;
    min-height: 390px;
    border-radius: 22px;
    overflow: hidden;
    display: flex;
    align-items: center;
    background-color: #1b5638;
    background-size: cover;
    background-position: center;
    {fondo_css}
}}
.hero-content {{
    padding: 55px;
    max-width: 700px;
}}
.hero-label {{
    color: #c6f36a;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 3px;
    margin-bottom: 18px;
}}
.hero-title {{
    color: white;
    font-size: clamp(38px, 6vw, 65px);
    font-weight: 800;
    line-height: 1.05;
    margin: 0 0 20px 0;
}}
.hero-description {{
    color: #f1f8f1;
    font-size: 17px;
    line-height: 1.7;
    max-width: 570px;
}}
.hero-line {{
    width: 85px;
    height: 5px;
    background-color: #c6f36a;
    border-radius: 10px;
    margin-top: 25px;
}}
@media (max-width: 700px) {{
    .hero {{ min-height: 360px; }}
    .hero-content {{ padding: 28px; }}
    .hero-description {{ font-size: 15px; }}
}}
</style>
</head>
<body>
    <div class="hero">
        <div class="hero-content">
            <div class="hero-label">TECNOLOGÍA PARA EL CAMPO</div>
            <h1 class="hero-title">GranjaConecta</h1>
            <div class="hero-description">
                Conectamos la tecnología con el bienestar animal.
                Una granja inteligente donde el monitoreo y la
                automatización facilitan el cuidado diario.
            </div>
            <div class="hero-line"></div>
        </div>
    </div>
</body>
</html>
"""

components.html(html_portada, height=410, scrolling=False)

if not imagen_portada:
    st.warning(
        "No se encontró fondogranja.jpg. "
        "Coloca la imagen en la misma carpeta que Inicioapp.py."
    )


# ==================================================
# PRESENTACIÓN
# ==================================================

st.markdown(
    """
    <div class="section-title">Bienvenido a GranjaConecta</div>
    <div class="section-description">
        Una solución tecnológica diseñada para facilitar
        el monitoreo y la automatización de las actividades
        de una granja, conectando sensores, dispositivos
        y herramientas digitales en un solo lugar.
    </div>
    """,
    unsafe_allow_html=True
)


# ==================================================
# CONEXIÓN MQTT CON WOKWI
# ==================================================

@st.cache_resource
def iniciar_conexion_mqtt():

    mensajes = queue.Queue()

    estado = {
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
                estado["conectado"] = True
                estado["error"] = ""
                cliente.subscribe(MQTT_TOPIC)
            else:
                estado["conectado"] = False
                estado["error"] = str(reason_code)

        def al_desconectar(
            cliente,
            userdata,
            disconnect_flags,
            reason_code,
            properties
        ):
            estado["conectado"] = False

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

        return cliente, mensajes, estado

    except Exception as error:
        estado["error"] = str(error)
        return None, mensajes, estado


cliente_mqtt, cola_mensajes, estado_mqtt = iniciar_conexion_mqtt()


# ==================================================
# DATOS RECIBIDOS DESDE WOKWI
# ==================================================

if "datos_ambientales" not in st.session_state:
    st.session_state.datos_ambientales = {
        "temperatura": None,
        "humedad": None
    }


def leer_datos_mqtt():

    while True:

        try:
            mensaje = cola_mensajes.get_nowait()
        except queue.Empty:
            break

        try:
            paquete = json.loads(mensaje)

            # Acepta mensajes de telemetría
            # y mensajes que envían los datos directamente.
            if paquete.get("tipo") not in (None, "telemetria"):
                continue

            datos = paquete.get("datos", paquete)

            # Comprobar que la lectura del DHT sea válida.
            lectura_dht_valida = datos.get(
                "lecturaDHTValida",
                True
            )

            if not lectura_dht_valida:
                continue

            temperatura = datos.get(
                "temperatura",
                datos.get("temp")
            )

            humedad = datos.get(
                "humedad",
                datos.get("hum")
            )

            if temperatura is not None:
                st.session_state.datos_ambientales[
                    "temperatura"
                ] = float(temperatura)

            if humedad is not None:
                st.session_state.datos_ambientales[
                    "humedad"
                ] = float(humedad)

        except (ValueError, TypeError, json.JSONDecodeError):
            continue


# ==================================================
# CLASIFICAR ESTADO AMBIENTAL
# ==================================================

def obtener_estado(temperatura, humedad):

    estados = []

    # Rangos de temperatura
    if temperatura is not None:

        if temperatura < 20:
            estados.append("bajo")

        elif temperatura >= 35:
            estados.append("alto")

    # Rangos de humedad
    if humedad is not None:

        if humedad < 30:
            estados.append("bajo")

        elif humedad > 70:
            estados.append("alto")

    if not estados:
        if temperatura is None and humedad is None:
            return "espera"

        return "normal"

    # Si existe una condición alta, tiene prioridad visual.
    if "alto" in estados:
        return "alto"

    if "bajo" in estados:
        return "bajo"

    return "normal"


def clasificar_sensor(valor, tipo):

    if valor is None:
        return "Sin datos"

    if tipo == "temperatura":

        if valor < 20:
            return "BAJA"

        if valor >= 35:
            return "ALTA"

        return "NORMAL"

    elif tipo == "humedad":

        if valor < 30:
            return "BAJA"

        if valor > 70:
            return "ALTA"

        return "NORMAL"

    return "Sin datos"


# ==================================================
# ILUSTRACIÓN DE LA GRANJA
# ==================================================

def ilustracion_granja(estado):

    estados = {
        "normal": {
            "clase": "normal",
            "titulo": "AMBIENTE ESTABLE",
            "mensaje": "Las lecturas se encuentran dentro de los rangos establecidos.",
            "emoji": "🌿"
        },
        "bajo": {
            "clase": "bajo",
            "titulo": "VALOR BAJO DETECTADO",
            "mensaje": "La temperatura o humedad presenta un valor inferior a su rango establecido.",
            "emoji": "❄️"
        },
        "alto": {
            "clase": "alto",
            "titulo": "VALOR ALTO DETECTADO",
            "mensaje": "La temperatura o humedad supera su rango establecido.",
            "emoji": "☀️"
        },
        "espera": {
            "clase": "espera",
            "titulo": "ESPERANDO DATOS DE WOKWI",
            "mensaje": "Inicia la simulación para visualizar tu granja.",
            "emoji": "📡"
        }
    }

    datos = estados[estado]

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">

<style>

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    font-family: Arial, sans-serif;
}}

.granja {{
    height: 430px;
    width: 100%;
    overflow: hidden;
    position: relative;
    border-radius: 20px;
    border: 2px solid rgba(40,80,50,.12);
}}

.normal {{
    --cielo1: #75c9ec;
    --cielo2: #d8f3ed;
    --montana: #83a77c;
    --pasto: #64a958;
    --pasto2: #9bce77;
    --granero: #c95d48;
    --techo: #843b32;
    --camino: #d8bd8b;
    --arbol: #42854a;
    --sol: #ffe88e;
}}

.bajo {{
    --cielo1: #438bbd;
    --cielo2: #b9d9ee;
    --montana: #688eaa;
    --pasto: #6d9fae;
    --pasto2: #a5c8d1;
    --granero: #527e9c;
    --techo: #345873;
    --camino: #b5cbd2;
    --arbol: #54858b;
    --sol: #d9eaf3;
}}

.alto {{
    --cielo1: #efb44d;
    --cielo2: #ffe4a0;
    --montana: #d1a15f;
    --pasto: #c1a047;
    --pasto2: #e4c66d;
    --granero: #c87935;
    --techo: #914c29;
    --camino: #e5c17b;
    --arbol: #969b43;
    --sol: #fff39a;
}}

.espera {{
    --cielo1: #aabeb9;
    --cielo2: #e2e9df;
    --montana: #91a28e;
    --pasto: #91a77e;
    --pasto2: #b9c69e;
    --granero: #968875;
    --techo: #716657;
    --camino: #c8b99b;
    --arbol: #748b68;
    --sol: #e5dfb6;
}}

.granja {{
    background: linear-gradient(
        to bottom,
        var(--cielo1),
        var(--cielo2)
    );
}}

.estado {{
    position: absolute;
    top: 14px;
    left: 14px;
    right: 14px;
    z-index: 5;
    background: rgba(255,255,255,.88);
    padding: 12px;
    text-align: center;
    border-radius: 12px;
    color: #31553b;
    font-weight: 900;
    font-size: 14px;
}}

.estado small {{
    display: block;
    font-size: 11px;
    font-weight: 600;
    margin-top: 4px;
    color: #61776a;
}}

svg {{
    width: 100%;
    height: 100%;
    display: block;
}}

.cielo {{
    fill: transparent;
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
    stroke: #684235;
    stroke-width: 3;
}}

.techo {{
    fill: var(--techo);
    stroke: #684235;
    stroke-width: 3;
}}

.puerta {{
    fill: #744737;
    stroke: #50352e;
    stroke-width: 3;
}}

.ventana {{
    fill: #f8e9b5;
    stroke: #603e35;
    stroke-width: 3;
}}

.arbol {{
    fill: var(--arbol);
}}

.camino {{
    fill: var(--camino);
}}

.sol {{
    fill: var(--sol);
}}

.nube {{
    fill: rgba(255,255,255,.8);
}}

.cerca {{
    stroke: #f4e5c5;
    stroke-width: 8;
    stroke-linecap: round;
    fill: none;
}}

</style>
</head>

<body>

<div class="granja {datos['clase']}">

    <div class="estado">
        {datos['emoji']} {datos['titulo']}
        <small>{datos['mensaje']}</small>
    </div>

    <svg viewBox="0 0 1000 430"
         preserveAspectRatio="xMidYMid slice">

        <!-- CIELO -->
        <rect width="1000" height="430" class="cielo"/>

        <!-- SOL -->
        <circle cx="830" cy="110" r="48" class="sol"/>

        <!-- NUBES -->
        <g class="nube">
            <ellipse cx="160" cy="110" rx="60" ry="20"/>
            <ellipse cx="195" cy="95" rx="38" ry="27"/>
            <ellipse cx="230" cy="112" rx="40" ry="19"/>

            <ellipse cx="550" cy="125" rx="58" ry="19"/>
            <ellipse cx="585" cy="110" rx="35" ry="24"/>
            <ellipse cx="620" cy="128" rx="42" ry="18"/>
        </g>

        <!-- MONTAÑAS -->
        <path d="
            M0 255
            L130 150
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

        <!-- TERRENO -->
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

        <!-- PASTO DELANTERO -->
        <path d="
            M0 315
            Q180 255 350 310
            Q570 360 760 300
            Q890 260 1000 310
            L1000 430 L0 430 Z"
            class="pasto2"/>

        <!-- ÁRBOLES -->
        <g>
            <rect x="75" y="235" width="18" height="80"
                  fill="#79543b"/>
            <circle cx="84" cy="215" r="42" class="arbol"/>
            <circle cx="58" cy="235" r="28" class="arbol"/>
            <circle cx="108" cy="237" r="28" class="arbol"/>

            <rect x="920" y="235" width="18" height="80"
                  fill="#79543b"/>
            <circle cx="929" cy="215" r="42" class="arbol"/>
            <circle cx="900" cy="238" r="28" class="arbol"/>
            <circle cx="955" cy="237" r="28" class="arbol"/>
        </g>

        <!-- GRANERO PRINCIPAL -->
        <g>
            <rect x="330" y="190" width="220" height="145"
                  class="granero"/>

            <path d="M300 195 L440 105 L580 195 Z"
                  class="techo"/>

            <rect x="410" y="255" width="62" height="80"
                  class="puerta"/>

            <rect x="355" y="220" width="38" height="38"
                  class="ventana"/>

            <rect x="485" y="220" width="38" height="38"
                  class="ventana"/>

            <path d="M440 255 V335"
                  stroke="#d8ad77" stroke-width="4"/>
        </g>

        <!-- GRANERO IZQUIERDO -->
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

        <!-- GRANERO DERECHO -->
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
        <path d="M0 355 H1000 M0 380 H1000"
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
        <g font-size="35">
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


# ==================================================
# MOSTRAR MONITOREO Y ACTUALIZAR DATOS
# ==================================================

@st.fragment(run_every="2s")
def mostrar_granja_conectada():

    leer_datos_mqtt()

    temperatura = st.session_state.datos_ambientales[
        "temperatura"
    ]

    humedad = st.session_state.datos_ambientales[
        "humedad"
    ]

    estado = obtener_estado(temperatura, humedad)

    st.markdown(
        """
        <div class="section-title">
            🌤️ Así se encuentra tu granja
        </div>

        <div class="section-description">
            Visualiza las condiciones ambientales recibidas
            desde los sensores conectados a Wokwi.
        </div>
        """,
        unsafe_allow_html=True
    )

    if estado_mqtt["conectado"]:
        st.success("🟢 Conexión MQTT activa. Recibiendo datos.")
    else:
        st.warning("🟡 Esperando conexión con Wokwi.")

        if estado_mqtt["error"]:
            st.caption(estado_mqtt["error"])

    # ILUSTRACIÓN
    components.html(
        ilustracion_granja(estado),
        height=440,
        scrolling=False
    )

    # INDICADORES
    col1, col2 = st.columns(2)

    with col1:

        valor = (
            "--"
            if temperatura is None
            else f"{temperatura:.1f} °C"
        )

        st.metric(
            "🌡️ Temperatura",
            valor,
            clasificar_sensor(temperatura, "temperatura")
        )

    with col2:

        valor = (
            "--"
            if humedad is None
            else f"{humedad:.1f} %"
        )

        st.metric(
            "💧 Humedad",
            valor,
            clasificar_sensor(humedad, "humedad")
        )

    if estado == "espera":
        st.info(
            "Inicia la simulación de Wokwi para recibir "
            "los primeros datos ambientales."
        )

    elif estado == "bajo":
        st.info(
            "❄️ La granja cambia a tonos azules porque "
            "se detectó una temperatura inferior a 20 °C "
            "o una humedad inferior al 30 %."
        )

    elif estado == "alto":
        st.warning(
            "☀️ La granja cambia a tonos amarillos porque "
            "se detectó una temperatura igual o superior "
            "a 35 °C o una humedad superior al 70 %."
        )

    else:
        st.success(
            "🌿 La granja mantiene sus colores verdes "
            "porque las lecturas están dentro de los "
            "rangos establecidos."
        )


# ==================================================
# SECCIÓN: GRANJA CONECTADA
# ==================================================

mostrar_granja_conectada()


# ==================================================
# TARJETAS: HTML EN COMPONENTES INDEPENDIENTES
# ==================================================

def mostrar_tarjeta(icono, titulo, descripcion):
    html_tarjeta = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
    * {{ box-sizing: border-box; }}
    html, body {{
        margin: 0;
        padding: 0;
        width: 100%;
        font-family: Arial, Helvetica, sans-serif;
    }}
    .card-box {{
        background: linear-gradient(145deg, #174a32 0%, #246642 100%);
        border-radius: 20px;
        padding: 28px;
        min-height: 225px;
        border: 1px solid rgba(255,255,255,.12);
        box-shadow: 0 8px 22px rgba(20,65,42,.10);
    }}
    .card-icon {{
        font-size: 38px;
        margin-bottom: 14px;
    }}
    .card-title {{
        color: white;
        font-size: 24px;
        font-weight: 800;
        margin-bottom: 12px;
    }}
    .card-description {{
        color: #e1f0e4;
        font-size: 14px;
        line-height: 1.6;
        min-height: 65px;
    }}
    </style>
    </head>
    <body>
        <div class="card-box">
            <div class="card-icon">{icono}</div>
            <div class="card-title">{titulo}</div>
            <div class="card-description">{descripcion}</div>
        </div>
    </body>
    </html>
    """
    components.html(html_tarjeta, height=245, scrolling=False)


col1, col2 = st.columns(2, gap="large")

with col1:
    mostrar_tarjeta(
        "🐄",
        "Corral inteligente",
        "Controla el acceso del corral, reconoce gestos "
        "y regula la ventilación para favorecer el "
        "bienestar de los animales."
    )

    if st.button(
        "Ingresar al Corral →",
        key="boton_corral",
        use_container_width=True
    ):
        st.switch_page("pages/2_Corral.py")


with col2:
    mostrar_tarjeta(
        "💧",
        "Bebedero inteligente",
        "Supervisa el nivel de agua y las condiciones "
        "ambientales, y controla el suministro mediante "
        "comandos de voz o texto."
    )

    if st.button(
        "Ingresar al Bebedero →",
        key="boton_bebedero",
        use_container_width=True
    ):
        st.switch_page("pages/1_Bebedero.py")


# ==================================================
# PIE DE PÁGINA
# ==================================================

st.markdown(
    """
    <div class="footer-line"></div>
    <div class="footer-text">
        GranjaConecta · Tecnología para el campo
        <br>
        Monitoreo inteligente y bienestar animal
    </div>
    """,
    unsafe_allow_html=True
)
