
import streamlit as st
import streamlit.components.v1 as components
import paho.mqtt.client as mqtt
import json
import os
import re
import uuid
import hashlib
import threading
import numpy as np
from PIL import Image
from tensorflow.keras.models import load_model

# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================

st.set_page_config(
    page_title="GranjaConecta | Corral",
    page_icon="🐄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# MQTT
# =========================================================

BROKER = "broker.mqttdashboard.com"
PUERTO = 1883

TOPICO_COMANDOS = "granjaconecta/comandos"
TOPICO_TELEMETRIA = "granjaconecta/telemetria"
TOPICO_RESPUESTAS = "granjaconecta/respuestas"

# Estado compartido del cliente MQTT
@st.cache_resource
def obtener_mqtt():

    estado = {
        "conectado": False,
        "telemetria": {},
        "respuesta": "Esperando información del ESP32...",
        "ultimo_mensaje": ""
    }

    bloqueo = threading.Lock()

    def al_conectar(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            estado["conectado"] = True
            client.subscribe(TOPICO_TELEMETRIA)
            client.subscribe(TOPICO_RESPUESTAS)
        else:
            estado["conectado"] = False

    def al_desconectar(client, userdata, disconnect_flags, reason_code, properties):
        estado["conectado"] = False

    def al_recibir(client, userdata, mensaje):
        try:
            contenido = mensaje.payload.decode("utf-8")

            with bloqueo:
                estado["ultimo_mensaje"] = contenido

                if mensaje.topic == TOPICO_TELEMETRIA:
                    datos = json.loads(contenido)
                    estado["telemetria"].update(datos)

                elif mensaje.topic == TOPICO_RESPUESTAS:
                    estado["respuesta"] = contenido

        except Exception as error:
            estado["respuesta"] = f"Error al recibir MQTT: {error}"

    cliente = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"GranjaConecta_Corral_{uuid.uuid4().hex[:8]}"
    )

    cliente.on_connect = al_conectar
    cliente.on_disconnect = al_desconectar
    cliente.on_message = al_recibir

    try:
        cliente.connect(BROKER, PUERTO, 60)
        cliente.loop_start()
    except Exception as error:
        estado["respuesta"] = f"No se pudo conectar: {error}"

    return cliente, estado


cliente, estado_mqtt = obtener_mqtt()


def enviar_comando(comando):
    """Envía un comando al ESP32 mediante MQTT."""
    try:
        mensaje = json.dumps({"comando": comando})
        resultado = cliente.publish(TOPICO_COMANDOS, mensaje)

        if resultado.rc == mqtt.MQTT_ERR_SUCCESS:
            st.toast(f"Orden enviada: {comando}", icon="📡")
        else:
            st.warning("No se pudo enviar la orden MQTT.")

    except Exception as error:
        st.error(f"Error al enviar comando: {error}")


# =========================================================
# CARGA DEL MODELO TEACHABLE MACHINE
# =========================================================

RUTA_MODELO = "keras_model.h5"
RUTA_ETIQUETAS = "labels.txt"


@st.cache_resource
def cargar_modelo():
    if not os.path.exists(RUTA_MODELO):
        return None

    return load_model(RUTA_MODELO, compile=False)


@st.cache_data
def cargar_etiquetas():
    if not os.path.exists(RUTA_ETIQUETAS):
        return []

    with open(RUTA_ETIQUETAS, "r", encoding="utf-8") as archivo:
        return [
            re.sub(r"^\s*\d+\s+", "", linea.strip())
            for linea in archivo
            if linea.strip()
        ]


modelo = None
etiquetas = []

try:
    modelo = cargar_modelo()
    etiquetas = cargar_etiquetas()
except Exception as error:
    st.error(f"No se pudo cargar el modelo: {error}")


# =========================================================
# MAPEO DE LOS SEIS GESTOS
# =========================================================

GESTOS = {
    0: {
        "nombre": "Abrir puerta",
        "emoji": "✋",
        "accion": "Abrir la puerta del granero",
        "comando": "PUERTA_ABRIR",
        "color": "#16a34a"
    },
    1: {
        "nombre": "Cerrar puerta",
        "emoji": "✊",
        "accion": "Cerrar la puerta del granero",
        "comando": "PUERTA_CERRAR",
        "color": "#dc2626"
    },
    2: {
        "nombre": "Subir ventilación",
        "emoji": "👍",
        "accion": "Aumentar la ventilación",
        "comando": "VENTILACION_SUBIR",
        "color": "#0ea5e9"
    },
    3: {
        "nombre": "Bajar ventilación",
        "emoji": "👎",
        "accion": "Disminuir la ventilación",
        "comando": "VENTILACION_BAJAR",
        "color": "#0ea5e9"
    },
    4: {
        "nombre": "Subir humedad visual",
        "emoji": "✌️",
        "accion": "Aumentar la niebla visual",
        "comando": "HUMEDAD_SUBIR",
        "color": "#8b5cf6"
    },
    5: {
        "nombre": "Bajar humedad visual",
        "emoji": "🔄✌️",
        "accion": "Disminuir la niebla visual",
        "comando": "HUMEDAD_BAJAR",
        "color": "#8b5cf6"
    }
}

# Los índices corresponden al orden de las seis clases
# del modelo Teachable Machine entregado.


# =========================================================
# ESTADO VISUAL
# =========================================================

if "humedad_visual" not in st.session_state:
    st.session_state.humedad_visual = 50

if "ultimo_gesto" not in st.session_state:
    st.session_state.ultimo_gesto = None

if "ultima_confianza" not in st.session_state:
    st.session_state.ultima_confianza = 0.0

if "ultima_imagen" not in st.session_state:
    st.session_state.ultima_imagen = None

if "ultimo_comando" not in st.session_state:
    st.session_state.ultimo_comando = None


# =========================================================
# PROCESAMIENTO DE LA CÁMARA
# =========================================================

def reconocer_gesto(imagen_archivo):

    imagen = Image.open(imagen_archivo).convert("RGB")
    imagen = imagen.resize((224, 224))

    arreglo = np.asarray(imagen, dtype=np.float32)

    # Normalización utilizada en el ejemplo del modelo
    datos = np.expand_dims((arreglo / 127.0) - 1.0, axis=0)

    predicciones = modelo.predict(datos, verbose=0)[0]

    indice = int(np.argmax(predicciones))
    confianza = float(predicciones[indice])

    return indice, confianza


# =========================================================
# DISEÑO GENERAL Y FONDO
# =========================================================

st.markdown("""
<style>

/* Fondo completo de la aplicación */
.stApp {
    background:
        linear-gradient(
            135deg,
            #e8f5e9 0%,
            #d9edda 45%,
            #edf7e9 100%
        );
}

/* Contenedor principal */
section.main {
    background: transparent;
}

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1500px;
}

/* Barra lateral verde oscuro */
[data-testid="stSidebar"] {
    background: linear-gradient(
        180deg,
        #123d25 0%,
        #174d2d 55%,
        #0d321e 100%
    );
}

[data-testid="stSidebar"] * {
    color: #ffffff !important;
}

/* Ocultar menú y pie */
#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

/* Títulos */
h1, h2, h3 {
    color: #173d26;
}

/* Tarjetas */
.tarjeta {
    background: rgba(255,255,255,0.92);
    border: 1px solid #d4e6d3;
    border-radius: 18px;
    padding: 18px;
    box-shadow: 0 5px 18px rgba(24, 65, 37, 0.09);
}

/* Encabezado */
.encabezado {
    background: linear-gradient(100deg, #164b2d, #287647);
    color: white;
    padding: 20px 25px;
    border-radius: 18px;
    margin-bottom: 18px;
    box-shadow: 0 5px 16px rgba(20,60,35,.18);
}

.encabezado h1 {
    color: white !important;
    margin: 0;
}

.encabezado p {
    color: #e3f5e6;
    margin: 5px 0 0 0;
}

/* Indicadores */
.indicador {
    background: white;
    padding: 13px;
    border-radius: 14px;
    border: 1px solid #d6e8d5;
    text-align: center;
    min-height: 100px;
}

.valor {
    font-size: 25px;
    font-weight: 800;
    color: #174b2b;
}

.nombre-indicador {
    font-size: 13px;
    color: #58735d;
}

/* Etiquetas */
.estado-normal {
    color: #15803d;
    font-weight: 800;
}

.estado-alerta {
    color: #d97706;
    font-weight: 800;
}

.estado-critico {
    color: #dc2626;
    font-weight: 900;
}

/* Cámara */
[data-testid="stCameraInput"] {
    border-radius: 15px;
    overflow: hidden;
}

/* Botones */
.stButton > button {
    border-radius: 12px;
    font-weight: 700;
}

/* Texto */
p, label {
    color: #294d32;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# BARRA LATERAL
# =========================================================

with st.sidebar:
    st.markdown("## 🐄 GranjaConecta")
    st.markdown("---")

    st.markdown("### 🌾 Panel del corral")
    st.write("Control inteligente del ambiente ganadero.")

    st.markdown("---")

    if estado_mqtt["conectado"]:
        st.success("🟢 Conectado al ESP32")
    else:
        st.warning("🟡 Conectando con MQTT...")

    st.markdown("---")
    st.markdown("### 📡 Comunicación")
    st.caption(BROKER)
    st.caption(f"Puerto: {PUERTO}")

    st.markdown("---")
    st.markdown("### 🎮 Gestos disponibles")
    st.write("✋ Abrir puerta")
    st.write("✊ Cerrar puerta")
    st.write("👍 Subir ventilación")
    st.write("👎 Bajar ventilación")
    st.write("✌️ Subir humedad visual")
    st.write("🔄✌️ Bajar humedad visual")


# =========================================================
# ENCABEZADO
# =========================================================

st.markdown("""
<div class="encabezado">
    <h1>🐄 Interior del corral</h1>
    <p>
        Observa el ambiente del granero y controla sus funciones
        mediante reconocimiento de gestos.
    </p>
</div>
""", unsafe_allow_html=True)


# =========================================================
# LECTURA DE TELEMETRÍA
# =========================================================

telemetria = estado_mqtt["telemetria"]

temperatura = telemetria.get("temperatura", None)
humedad = telemetria.get("humedad", None)
ventilacion = telemetria.get("ventilacion", 0)
puerta = telemetria.get("puerta", "CERRADA")

try:
    ventilacion = float(ventilacion)
except (ValueError, TypeError):
    ventilacion = 0

puerta_texto = str(puerta).upper()

if puerta_texto in ["1", "TRUE", "ABIERTA", "ABIERTO", "OPEN"]:
    puerta_abierta = True
else:
    puerta_abierta = False


# =========================================================
# INDICADORES DEL CORRAL
# =========================================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    valor = "--" if temperatura is None else f"{temperatura} °C"
    st.markdown(
        f'<div class="indicador"><div>🌡️</div>'
        f'<div class="valor">{valor}</div>'
        f'<div class="nombre-indicador">Temperatura</div></div>',
        unsafe_allow_html=True
    )

with col2:
    valor = "--" if humedad is None else f"{humedad} %"
    st.markdown(
        f'<div class="indicador"><div>💧</div>'
        f'<div class="valor">{valor}</div>'
        f'<div class="nombre-indicador">Humedad real</div></div>',
        unsafe_allow_html=True
    )

with col3:
    st.markdown(
        f'<div class="indicador"><div>🌀</div>'
        f'<div class="valor">{ventilacion:.0f} %</div>'
        f'<div class="nombre-indicador">Ventilación</div></div>',
        unsafe_allow_html=True
    )

with col4:
    estado_puerta = "Abierta" if puerta_abierta else "Cerrada"
    st.markdown(
        f'<div class="indicador"><div>🚪</div>'
        f'<div class="valor">{estado_puerta}</div>'
        f'<div class="nombre-indicador">Puerta</div></div>',
        unsafe_allow_html=True
    )


st.write("")


# =========================================================
# ESCENARIO INTERIOR DEL GRANERO
# =========================================================

# La humedad visual controla la cantidad de niebla.
niebla = st.session_state.humedad_visual / 100

# Temperatura: efectos visuales ilustrativos.
if temperatura is None:
    color_ambiente = "#dcebd9"
elif float(temperatura) < 15:
    color_ambiente = "#c9e8f4"
elif float(temperatura) > 30:
    color_ambiente = "#f7d6a5"
else:
    color_ambiente = "#dcebd9"

puerta_visual = "translateX(0)" if puerta_abierta else "translateX(0)"

html_granero = f"""
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
    background: transparent;
}}

.granero {{
    height: 440px;
    width: 100%;
    position: relative;
    overflow: hidden;
    border-radius: 20px;
    border: 5px solid #704522;
    background: {color_ambiente};
    box-shadow: 0 7px 18px rgba(30,60,30,.2);
}}

/* Techo interior */
.techo {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 85px;
    background: repeating-linear-gradient(
        0deg,
        #744729,
        #744729 14px,
        #8d5a32 15px,
        #8d5a32 28px
    );
    border-bottom: 8px solid #4b301c;
}}

/* Vigas */
.viga {{
    position: absolute;
    top: 70px;
    left: 8%;
    width: 10px;
    height: 270px;
    background: #754625;
    box-shadow: 250px 0 #754625, 500px 0 #754625;
}}

/* Pared */
.pared {{
    position: absolute;
    top: 85px;
    left: 0;
    width: 100%;
    height: 230px;
    background: repeating-linear-gradient(
        90deg,
        #d6a56e,
        #d6a56e 45px,
        #c9915b 46px,
        #c9915b 51px
    );
}}

/* Piso */
.piso {{
    position: absolute;
    bottom: 0;
    width: 100%;
    height: 115px;
    background: repeating-linear-gradient(
        0deg,
        #7b512d,
        #7b512d 18px,
        #96683c 19px,
        #96683c 37px
    );
    border-top: 9px solid #573a24;
}}

/* Ventana */
.ventana {{
    position: absolute;
    top: 125px;
    right: 10%;
    width: 85px;
    height: 85px;
    background: #a9d9e8;
    border: 8px solid #704522;
    box-shadow: inset 0 0 0 3px #d9f2fa;
}}

/* Comedero */
.comedero {{
    position: absolute;
    bottom: 72px;
    left: 7%;
    font-size: 42px;
    z-index: 5;
}}

/* Vaca */
.vaca {{
    position: absolute;
    bottom: 90px;
    left: 36%;
    font-size: 115px;
    z-index: 6;
    filter: drop-shadow(3px 5px 2px rgba(0,0,0,.15));
}}

/* Puerta */
.puerta-marco {{
    position: absolute;
    right: 3%;
    bottom: 68px;
    width: 115px;
    height: 190px;
    background: #472c1b;
    border: 8px solid #5c3821;
    z-index: 4;
}}

.puerta {{
    position: absolute;
    inset: 0;
    background: repeating-linear-gradient(
        90deg,
        #a46b3d,
        #a46b3d 23px,
        #744523 24px,
        #744523 28px
    );
    border: 3px solid #4e2f1a;
    transform-origin: left center;
    transition: transform 1s ease;
}}

.puerta.abierta {{
    transform: perspective(300px) rotateY(-65deg);
}}

.puerta.cerrada {{
    transform: perspective(300px) rotateY(0deg);
}}

/* Ventilador */
.ventilador {{
    position: absolute;
    top: 105px;
    left: 44%;
    font-size: 45px;
    z-index: 8;
    animation: girar {max(0.12, 1.2 - ventilacion / 100):.2f}s linear infinite;
}}

@keyframes girar {{
    from {{ transform: rotate(0deg); }}
    to {{ transform: rotate(360deg); }}
}}

/* Niebla visual */
.niebla {{
    position: absolute;
    inset: 85px 0 100px 0;
    background: rgba(255,255,255,{niebla * 0.48:.2f});
    pointer-events: none;
    z-index: 9;
}}

/* Luz ambiente */
.lampara {{
    position: absolute;
    top: 80px;
    left: 48%;
    font-size: 32px;
    z-index: 10;
}}

/* Estado de la puerta */
.estado {{
    position: absolute;
    top: 15px;
    right: 15px;
    background: rgba(20,50,25,.85);
    color: white;
    padding: 8px 12px;
    border-radius: 10px;
    font-size: 13px;
    z-index: 12;
}}

/* Indicador de ambiente */
.ambiente {{
    position: absolute;
    bottom: 12px;
    left: 12px;
    color: white;
    background: rgba(30,45,25,.75);
    padding: 7px 10px;
    border-radius: 8px;
    z-index: 12;
    font-size: 12px;
}}
</style>
</head>

<body>
<div class="granero">

    <div class="techo"></div>
    <div class="pared"></div>
    <div class="viga"></div>
    <div class="piso"></div>

    <div class="ventana"></div>

    <div class="lampara">💡</div>
    <div class="ventilador">🌀</div>

    <div class="comedero">🌾</div>

    <div class="vaca">🐄</div>

    <div class="puerta-marco">
        <div class="puerta {'abierta' if puerta_abierta else 'cerrada'}"></div>
    </div>

    <div class="niebla"></div>

    <div class="estado">
        🚪 Puerta: {'ABIERTA' if puerta_abierta else 'CERRADA'}
    </div>

    <div class="ambiente">
        🌫️ Humedad visual: {st.session_state.humedad_visual} %
        &nbsp; | &nbsp;
        🌀 Ventilación: {ventilacion:.0f} %
    </div>

</div>
</body>
</html>
"""


# =========================================================
# DISTRIBUCIÓN: GRANERO + CÁMARA
# =========================================================

st.markdown("### 🏡 Vista interior y reconocimiento de gestos")

col_granero, col_camara = st.columns([1.25, 1], gap="medium")

with col_granero:
    st.markdown('<div class="tarjeta">', unsafe_allow_html=True)
    st.markdown("#### 🌾 Interior del granero")

    components.html(
        html_granero,
        height=455,
        scrolling=False
    )

    st.caption(
        "La puerta y la ventilación se muestran según los datos "
        "recibidos del ESP32. La niebla representa humedad visual."
    )
    st.markdown('</div>', unsafe_allow_html=True)


with col_camara:
    st.markdown('<div class="tarjeta">', unsafe_allow_html=True)
    st.markdown("#### 📷 Cámara de reconocimiento")

    foto = st.camera_input(
        "Muestra tu mano frente a la cámara",
        key="camara_corral"
    )

    if foto is not None and modelo is not None:

        contenido = foto.getvalue()
        huella = hashlib.md5(contenido).hexdigest()

        # Evita enviar el mismo gesto varias veces al actualizar
        if huella != st.session_state.ultima_imagen:

            try:
                indice, confianza = reconocer_gesto(foto)

                st.session_state.ultima_imagen = huella
                st.session_state.ultima_confianza = confianza

                if confianza >= 0.75 and indice in GESTOS:

                    gesto = GESTOS[indice]

                    st.session_state.ultimo_gesto = gesto

                    if indice in [0, 1, 2, 3]:
                        enviar_comando(gesto["comando"])
                        st.session_state.ultimo_comando = gesto["comando"]

                    elif indice == 4:
                        st.session_state.humedad_visual = min(
                            100,
                            st.session_state.humedad_visual + 25
                        )
                        enviar_comando(gesto["comando"])
                        st.session_state.ultimo_comando = gesto["comando"]

                    elif indice == 5:
                        st.session_state.humedad_visual = max(
                            0,
                            st.session_state.humedad_visual - 25
                        )
                        enviar_comando(gesto["comando"])
                        st.session_state.ultimo_comando = gesto["comando"]

                else:
                    st.session_state.ultimo_gesto = None
                    st.warning(
                        "No se reconoció un gesto con suficiente confianza."
                    )

            except Exception as error:
                st.error(f"Error al reconocer el gesto: {error}")

    elif modelo is None:
        st.error(
            "No se encontró el modelo. Revisa keras_model.h5 "
            "y labels.txt en la raíz del repositorio."
        )

    st.divider()

    st.markdown("#### ✋ Resultado del reconocimiento")

    if st.session_state.ultimo_gesto:

        gesto = st.session_state.ultimo_gesto

        st.markdown(
            f"""
            <div style="
                background:#edf7ed;
                border:2px solid {gesto['color']};
                border-radius:15px;
                padding:16px;
                text-align:center;
            ">
                <div style="font-size:55px;">{gesto['emoji']}</div>
                <h3 style="margin:5px 0;color:#174b2b;">
                    {gesto['nombre']}
                </h3>
                <p style="margin:5px;color:#355b3d;">
                    {gesto['accion']}
                </p>
                <div style="
                    font-size:18px;
                    font-weight:bold;
                    color:#174b2b;
                ">
                    Confianza: {st.session_state.ultima_confianza * 100:.1f} %
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    else:
        st.info(
            "Todavía no se ha reconocido ningún gesto. "
            "Toma una foto de tu mano para comenzar."
        )

    st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# ESTADO DE HUMEDAD VISUAL
# =========================================================

st.write("")

st.markdown("### 💧 Ambiente visual del granero")

st.progress(
    st.session_state.humedad_visual / 100,
    text=f"Humedad visual: {st.session_state.humedad_visual} %"
)

st.caption(
    "Este porcentaje es un efecto visual modificado por los gestos. "
    "No representa la humedad real medida por el DHT22."
)


# =========================================================
# ESTADO DE COMUNICACIÓN
# =========================================================

st.write("")
st.markdown("### 📡 Comunicación con el ESP32")

col_estado1, col_estado2 = st.columns(2)

with col_estado1:
    if estado_mqtt["conectado"]:
        st.success("Conexión MQTT activa")
    else:
        st.warning("Esperando conexión MQTT")

with col_estado2:
    st.info(estado_mqtt["respuesta"])

if st.button("🔄 Actualizar información del corral", use_container_width=True):
    st.rerun()

st.caption(
    "Si el ESP32 cambia un estado, actualiza esta página para "
    "ver la información más reciente recibida por MQTT."
)
