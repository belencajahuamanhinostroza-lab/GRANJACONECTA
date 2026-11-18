
import json
import re
import sys
import threading
from pathlib import Path
from io import BytesIO

import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

# =========================================================
# 1. CONFIGURACIÓN GENERAL
# =========================================================

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MODEL_PATH = ROOT / "keras_model.h5"
LABELS_PATH = ROOT / "labels.txt"

BROKER = "broker.mqttdashboard.com"
PORT = 1883

TOPICO_COMANDOS = "granjaconecta/comandos"
TOPICO_TELEMETRIA = "granjaconecta/telemetria"
TOPICO_RESPUESTAS = "granjaconecta/respuestas"

st.set_page_config(
    page_title="GranjaConecta - Corral",
    page_icon="🐄",
    layout="wide"
)

# =========================================================
# 2. DISEÑO GENERAL
# =========================================================

st.markdown("""
<style>
.stApp {
    background: #f2f8f2;
}

h1, h2, h3 {
    color: #24583b;
}

.titulo {
    color: #24583b;
    font-size: 34px;
    font-weight: 800;
    margin-bottom: 0;
}

.subtitulo {
    color: #66816d;
    margin-bottom: 20px;
}

div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e0ebe1;
    padding: 14px;
    border-radius: 12px;
}

.resultado {
    background: #edf8ef;
    border-left: 5px solid #29945b;
    padding: 15px;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="titulo">🐄 GranjaConecta - Corral</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitulo">'
    'Escenario virtual y reconocimiento de gestos'
    '</div>',
    unsafe_allow_html=True
)

# =========================================================
# 3. CONEXIÓN MQTT DIRECTA
# =========================================================

@st.cache_resource
def iniciar_mqtt():
    import paho.mqtt.client as mqtt

    estado = {
        "conectado": False,
        "telemetria": {},
        "respuestas": [],
        "error": ""
    }

    bloqueo = threading.Lock()

    def al_conectar(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            with bloqueo:
                estado["conectado"] = True
                estado["error"] = ""

            client.subscribe(TOPICO_TELEMETRIA)
            client.subscribe(TOPICO_RESPUESTAS)

        else:
            with bloqueo:
                estado["conectado"] = False
                estado["error"] = f"Error de conexión: {reason_code}"

    def al_desconectar(client, userdata, disconnect_flags,
                       reason_code, properties):
        with bloqueo:
            estado["conectado"] = False

    def al_recibir(client, userdata, msg):
        contenido = msg.payload.decode("utf-8", errors="replace")

        with bloqueo:
            if msg.topic == TOPICO_TELEMETRIA:
                try:
                    datos = json.loads(contenido)

                    if isinstance(datos, dict):
                        estado["telemetria"] = datos

                except json.JSONDecodeError:
                    estado["error"] = "Telemetría recibida con formato inválido"

            elif msg.topic == TOPICO_RESPUESTAS:
                estado["respuestas"].append(contenido)
                estado["respuestas"] = estado["respuestas"][-20:]

    cliente = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="GranjaConecta_Corral",
        protocol=mqtt.MQTTv311
    )

    cliente.on_connect = al_conectar
    cliente.on_disconnect = al_desconectar
    cliente.on_message = al_recibir

    try:
        cliente.connect(BROKER, PORT, keepalive=60)
        cliente.loop_start()

    except Exception as error:
        with bloqueo:
            estado["error"] = str(error)

    return cliente, estado, bloqueo


try:
    cliente_mqtt, mqtt_estado, mqtt_bloqueo = iniciar_mqtt()
except Exception as error:
    cliente_mqtt = None
    mqtt_estado = {
        "conectado": False,
        "telemetria": {},
        "respuestas": [],
        "error": str(error)
    }
    mqtt_bloqueo = None


def obtener_estado_mqtt():
    if mqtt_bloqueo is None:
        return mqtt_estado.copy()

    with mqtt_bloqueo:
        return {
            "conectado": mqtt_estado["conectado"],
            "telemetria": dict(mqtt_estado["telemetria"]),
            "respuestas": list(mqtt_estado["respuestas"]),
            "error": mqtt_estado["error"]
        }


def enviar_comando(comando):
    if cliente_mqtt is None:
        return False, "No existe conexión MQTT."

    if not cliente_mqtt.is_connected():
        return False, "El broker MQTT no está conectado."

    mensaje = json.dumps({"comando": comando})

    resultado = cliente_mqtt.publish(
        TOPICO_COMANDOS,
        mensaje,
        qos=0,
        retain=False
    )

    if resultado.rc == 0:
        return True, f"Comando enviado: {comando}"

    return False, "No se pudo publicar el comando MQTT."


estado_mqtt = obtener_estado_mqtt()
telemetria = estado_mqtt["telemetria"]

# =========================================================
# 4. FUNCIONES DE LECTURA
# =========================================================

def obtener_numero(datos, clave, valor_default):
    try:
        return float(datos.get(clave, valor_default))
    except (TypeError, ValueError, AttributeError):
        return float(valor_default)


def interpretar_puerta(valor):
    if isinstance(valor, bool):
        return valor

    if isinstance(valor, (int, float)):
        return valor != 0

    texto = str(valor).strip().lower()

    return texto in [
        "abierta", "abierto", "open",
        "1", "true", "on"
    ]


temperatura = obtener_numero(
    telemetria, "temperatura", 28
)

humedad_sensor = obtener_numero(
    telemetria, "humedad", 60
)

ventilacion = obtener_numero(
    telemetria, "ventilacion", 50
)

puerta_abierta = interpretar_puerta(
    telemetria.get("puerta", "cerrada")
)

# =========================================================
# 5. MODELO KERAS Y ETIQUETAS
# =========================================================

@st.cache_resource
def cargar_modelo():
    from tensorflow.keras.models import load_model
    return load_model(str(MODEL_PATH), compile=False)


def cargar_etiquetas():
    etiquetas = []

    with open(LABELS_PATH, "r", encoding="utf-8") as archivo:
        for linea in archivo:
            linea = linea.strip()

            if not linea:
                continue

            # Ejemplo: "0 Abrir puerta" -> "Abrir puerta"
            linea = re.sub(r"^\d+\s+", "", linea)
            etiquetas.append(linea)

    return etiquetas


# El índice corresponde al orden de labels.txt.
# Las clases 2 y 3 controlan ventilación aunque
# sus etiquetas originales mencionen temperatura.

GESTOS = {
    0: {
        "comando": "PUERTA_ABRIR",
        "accion": "Abrir la puerta del corral",
        "icono": "🚪"
    },
    1: {
        "comando": "PUERTA_CERRAR",
        "accion": "Cerrar la puerta del corral",
        "icono": "🚪"
    },
    2: {
        "comando": "VENTILACION_SUBIR",
        "accion": "Aumentar la ventilación",
        "icono": "🌀"
    },
    3: {
        "comando": "VENTILACION_BAJAR",
        "accion": "Disminuir la ventilación",
        "icono": "💨"
    },
    4: {
        "comando": "HUMEDAD_SUBIR",
        "accion": "Aumentar la niebla visual",
        "icono": "🌫️"
    },
    5: {
        "comando": "HUMEDAD_BAJAR",
        "accion": "Disminuir la niebla visual",
        "icono": "☀️"
    }
}

# =========================================================
# 6. VARIABLES DE SESIÓN
# =========================================================

if "humedad_visual" not in st.session_state:
    st.session_state.humedad_visual = 50

if "ultimo_gesto" not in st.session_state:
    st.session_state.ultimo_gesto = "Esperando gesto"

if "ultima_confianza" not in st.session_state:
    st.session_state.ultima_confianza = 0.0

if "ultima_accion" not in st.session_state:
    st.session_state.ultima_accion = "Sin acción"

if "ultimo_comando" not in st.session_state:
    st.session_state.ultimo_comando = "Ninguno"

if "mensaje_resultado" not in st.session_state:
    st.session_state.mensaje_resultado = ""

# =========================================================
# 7. ESCENARIO ANIMADO 2D
# =========================================================

def crear_escenario(temp, humedad, ventilacion, puerta_abierta):

    if temp >= 30:
        cielo = "#f3c38e"
        granero = "#d77a42"
        estado_temp = "Ambiente caliente"
        calor = "0.35"

    elif temp <= 15:
        cielo = "#b9d9ed"
        granero = "#76a9c7"
        estado_temp = "Ambiente frío"
        calor = "0"

    else:
        cielo = "#a9d9ee"
        granero = "#e5a16c"
        estado_temp = "Temperatura normal"
        calor = "0"

    humedad = max(0, min(100, humedad))
    ventilacion = max(0, min(100, ventilacion))

    duracion = max(
        0.15,
        2.5 - (ventilacion / 100) * 2.3
    )

    puerta_css = (
        "translateX(105%)"
        if puerta_abierta
        else "translateX(0)"
    )

    estado_puerta = (
        "ABIERTA" if puerta_abierta else "CERRADA"
    )

    html = """
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">

    <style>
    * { box-sizing: border-box; }

    body {
        margin: 0;
        font-family: Arial, sans-serif;
        overflow: hidden;
    }

    .scene {
        position: relative;
        height: 510px;
        width: 100%;
        overflow: hidden;
        border-radius: 20px;
        background: linear-gradient(
            to bottom,
            __CIELO__ 0%,
            #d8edce 72%,
            #85b96b 73%,
            #55934c 100%
        );
    }

    .sun {
        position: absolute;
        top: 30px;
        right: 12%;
        width: 75px;
        height: 75px;
        border-radius: 50%;
        background: #ffe58a;
        box-shadow: 0 0 35px #ffe58a;
        animation: pulse 4s infinite alternate;
    }

    @keyframes pulse {
        to { transform: scale(1.12); }
    }

    .cloud {
        position: absolute;
        top: 50px;
        left: 10%;
        font-size: 55px;
        animation: cloud 18s linear infinite alternate;
    }

    @keyframes cloud {
        to { transform: translateX(100px); }
    }

    .tree {
        position: absolute;
        bottom: 85px;
        left: 4%;
        font-size: 95px;
    }

    .barn {
        position: absolute;
        bottom: 75px;
        left: 50%;
        transform: translateX(-50%);
        width: min(590px, 76%);
        height: 330px;
    }

    .roof {
        position: absolute;
        top: 0;
        left: -4%;
        width: 108%;
        height: 100px;
        background: #a94e37;
        clip-path: polygon(50% 0, 100% 100%, 0 100%);
        z-index: 2;
    }

    .barn-body {
        position: absolute;
        top: 70px;
        width: 100%;
        height: 260px;
        background: __GRANERO__;
        border: 7px solid #874c35;
    }

    .window {
        position: absolute;
        top: 40px;
        width: 75px;
        height: 70px;
        background: #bde9f5;
        border: 8px solid #75452f;
    }

    .left { left: 45px; }
    .right { right: 45px; }

    .fan {
        position: absolute;
        top: 115px;
        left: 50%;
        font-size: 54px;
        animation: spin __DURACION__s linear infinite;
    }

    @keyframes spin {
        from { transform: translateX(-50%) rotate(0deg); }
        to { transform: translateX(-50%) rotate(360deg); }
    }

    .door-frame {
        position: absolute;
        bottom: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 150px;
        height: 180px;
        background: #56331f;
        border: 8px solid #f0c58d;
        overflow: hidden;
    }

    .door {
        position: absolute;
        inset: 0;
        background: #754323;
        transform: __PUERTA__;
        transition: transform 1.2s ease-in-out;
        border-left: 6px solid #d5a46d;
        background-image: repeating-linear-gradient(
            90deg,
            transparent 0,
            transparent 35px,
            rgba(0,0,0,.16) 36px,
            rgba(0,0,0,.16) 40px
        );
    }

    .knob {
        position: absolute;
        right: 15px;
        top: 50%;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #f8d77b;
    }

    .cow {
        position: absolute;
        bottom: 80px;
        left: 20%;
        font-size: 90px;
        z-index: 5;
        animation: cow 3s ease-in-out infinite alternate;
    }

    @keyframes cow {
        to { transform: translateY(-5px); }
    }

    .ground {
        position: absolute;
        bottom: 0;
        height: 90px;
        width: 100%;
        background: #65a354;
        z-index: 1;
    }

    .grass {
        position: absolute;
        bottom: 5px;
        width: 100%;
        text-align: center;
        font-size: 30px;
        z-index: 6;
    }

    .fog {
        position: absolute;
        inset: 80px 0 65px 0;
        opacity: __NIEBLA__;
        pointer-events: none;
        background:
            radial-gradient(ellipse at 35% 70%,
            rgba(255,255,255,.8), transparent 40%),
            radial-gradient(ellipse at 70% 55%,
            rgba(255,255,255,.75), transparent 42%);
        animation: fog 7s ease-in-out infinite alternate;
        z-index: 4;
    }

    @keyframes fog {
        from { transform: translateX(-15px); }
        to { transform: translateX(20px); }
    }

    .heat {
        position: absolute;
        inset: 0;
        background: rgba(255, 110, 35, __CALOR__);
        pointer-events: none;
        mix-blend-mode: screen;
        animation: heat 2s infinite alternate;
        z-index: 7;
    }

    @keyframes heat {
        from { opacity: .10; }
        to { opacity: .30; }
    }

    .info {
        position: absolute;
        top: 14px;
        left: 14px;
        z-index: 10;
        background: rgba(255,255,255,.92);
        padding: 11px 14px;
        border-radius: 12px;
        color: #28543b;
        font-size: 13px;
        line-height: 1.7;
        font-weight: bold;
    }

    .door-status {
        position: absolute;
        bottom: 12px;
        right: 15px;
        z-index: 10;
        background: rgba(255,255,255,.9);
        padding: 8px 12px;
        border-radius: 10px;
        color: #28543b;
        font-weight: bold;
        font-size: 13px;
    }

    @media(max-width: 600px) {
        .scene { height: 390px; }
        .barn { width: 85%; height: 260px; }
        .barn-body { height: 205px; }
        .door-frame { width: 105px; height: 130px; }
        .cow { font-size: 60px; left: 8%; }
        .tree { font-size: 65px; }
        .fan { font-size: 40px; }
    }
    </style>
    </head>

    <body>
    <div class="scene">

        <div class="sun"></div>
        <div class="cloud">☁️</div>
        <div class="tree">🌳</div>

        <div class="info">
            🌡️ __TEMP__ °C · __ESTADO_TEMP__
            <br>
            💧 Humedad visual: __HUMEDAD__ %
            <br>
            🌀 Ventilación: __VENTILACION__ %
        </div>

        <div class="barn">
            <div class="roof"></div>

            <div class="barn-body">
                <div class="window left"></div>
                <div class="window right"></div>

                <div class="fan">🌀</div>

                <div class="door-frame">
                    <div class="door">
                        <div class="knob"></div>
                    </div>
                </div>
            </div>
        </div>

        <div class="cow">🐄</div>
        <div class="fog"></div>
        <div class="ground"></div>
        <div class="grass">🌿 🌱 🌾 🌿 🌱 🌾 🌿</div>

        <div class="door-status">
            🚪 PUERTA __ESTADO_PUERTA__
        </div>

        <div class="heat"></div>

    </div>
    </body>
    </html>
    """

    reemplazos = {
        "__CIELO__": cielo,
        "__GRANERO__": granero,
        "__DURACION__": f"{duracion:.2f}",
        "__PUERTA__": puerta_css,
        "__NIEBLA__": f"{humedad / 100:.2f}",
        "__CALOR__": calor,
        "__TEMP__": f"{temp:.1f}",
        "__ESTADO_TEMP__": estado_temp,
        "__HUMEDAD__": f"{humedad:.0f}",
        "__VENTILACION__": f"{ventilacion:.0f}",
        "__ESTADO_PUERTA__": estado_puerta
    }

    for clave, valor in reemplazos.items():
        html = html.replace(clave, valor)

    return html


# =========================================================
# 8. ESCENARIO GRANDE
# =========================================================

st.markdown("### 🌳 Escenario virtual del corral")

escenario = crear_escenario(
    temperatura,
    st.session_state.humedad_visual,
    ventilacion,
    puerta_abierta
)

components.html(
    escenario,
    height=525,
    scrolling=False
)

# =========================================================
# 9. INDICADORES
# =========================================================

st.markdown("### 📊 Supervisión del corral")

c1, c2, c3 = st.columns(3)

c1.metric(
    "🌡️ Temperatura medida",
    f"{temperatura:.1f} °C"
)

c2.metric(
    "💧 Humedad medida",
    f"{humedad_sensor:.1f} %"
)

c3.metric(
    "🌀 Ventilación",
    f"{ventilacion:.0f} %"
)

st.caption(
    "La humedad visual del escenario es independiente "
    "de la medición física del DHT22."
)

# =========================================================
# 10. CÁMARA E INFORMACIÓN DEL GESTO
# =========================================================

st.divider()
st.markdown("### 🎥 Reconocimiento de gestos")

col_camara, col_informacion = st.columns([1, 1.15])

with col_camara:

    st.markdown("#### Cámara")

    foto = st.camera_input(
        "Coloca tu mano frente a la cámara",
        key="camara_corral"
    )

    st.caption(
        "Captura tu gesto para que el modelo Keras lo reconozca."
    )

with col_informacion:

    st.markdown("#### Gesto reconocido")

    st.markdown(
        f"""
        <div class="resultado">
            <h3>{st.session_state.ultimo_gesto}</h3>
            <p><b>Acción:</b> {st.session_state.ultima_accion}</p>
            <p><b>Confianza:</b>
            {st.session_state.ultima_confianza * 100:.1f}%</p>
            <p><b>Último comando:</b>
            {st.session_state.ultimo_comando}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.session_state.mensaje_resultado:
        st.info(st.session_state.mensaje_resultado)

# =========================================================
# 11. RECONOCER GESTO Y ENVIAR COMANDO
# =========================================================

if foto is not None:

    if st.button(
        "🤚 Reconocer gesto y ejecutar acción",
        type="primary",
        use_container_width=True
    ):

        try:
            if not MODEL_PATH.exists():
                st.error(
                    "No se encuentra keras_model.h5 en la raíz del proyecto."
                )
                st.stop()

            if not LABELS_PATH.exists():
                st.error(
                    "No se encuentra labels.txt en la raíz del proyecto."
                )
                st.stop()

            etiquetas = cargar_etiquetas()

            if len(etiquetas) != 6:
                st.error(
                    "Se esperaban seis etiquetas en labels.txt. "
                    f"Se encontraron {len(etiquetas)}."
                )
                st.stop()

            modelo = cargar_modelo()

            imagen = Image.open(
                BytesIO(foto.getvalue())
            ).convert("RGB")

            imagen = imagen.resize((224, 224))

            imagen_array = np.asarray(
                imagen,
                dtype=np.float32
            )

            # Normalización utilizada en el código
            # de referencia de tu proyecto anterior.
            imagen_array = (
                imagen_array.astype(np.float32) / 127.0
            ) - 1.0

            imagen_array = np.expand_dims(
                imagen_array,
                axis=0
            )

            prediccion = modelo.predict(
                imagen_array,
                verbose=0
            )[0]

            indice = int(np.argmax(prediccion))
            confianza = float(prediccion[indice])

            st.session_state.ultimo_gesto = etiquetas[indice]
            st.session_state.ultima_confianza = confianza

            if confianza < 0.60:

                st.session_state.ultima_accion = (
                    "Gesto no reconocido con suficiente confianza"
                )

                st.session_state.mensaje_resultado = (
                    "No se envió ningún comando. "
                    "Intenta tomar otra fotografía."
                )

                st.warning(
                    f"Confianza baja: {confianza * 100:.1f}%"
                )

            else:

                gesto = GESTOS[indice]
                comando = gesto["comando"]

                st.session_state.ultima_accion = gesto["accion"]
                st.session_state.ultimo_comando = comando

                # Enviar comando al broker
                exito, mensaje = enviar_comando(comando)

                if exito:

                    st.session_state.mensaje_resultado = mensaje

                    # Los gestos de humedad cambian
                    # únicamente la niebla visual.
                    if indice == 4:
                        st.session_state.humedad_visual = min(
                            100,
                            st.session_state.humedad_visual + 25
                        )

                    elif indice == 5:
                        st.session_state.humedad_visual = max(
                            0,
                            st.session_state.humedad_visual - 25
                        )

                    st.success(
                        f"Gesto reconocido: {etiquetas[indice]}. "
                        f"{gesto['accion']}."
                    )

                else:
                    st.session_state.mensaje_resultado = mensaje
                    st.error(mensaje)

            st.rerun()

        except Exception as error:
            st.error(
                f"Error al procesar el gesto: {error}"
            )

# =========================================================
# 12. PRUEBA VISUAL DE HUMEDAD
# =========================================================

with st.expander("🌫️ Prueba manual de la animación de humedad"):

    st.write(
        "Estos botones solo prueban el efecto visual. "
        "No modifican la lectura del sensor."
    )

    a, b = st.columns(2)

    with a:
        if st.button(
            "Subir niebla +25 %",
            use_container_width=True
        ):
            st.session_state.humedad_visual = min(
                100,
                st.session_state.humedad_visual + 25
            )
            st.rerun()

    with b:
        if st.button(
            "Bajar niebla -25 %",
            use_container_width=True
        ):
            st.session_state.humedad_visual = max(
                0,
                st.session_state.humedad_visual - 25
            )
            st.rerun()

    st.write(
        f"Humedad visual actual: "
        f"{st.session_state.humedad_visual}%"
    )

# =========================================================
# 13. ESTADO DE MQTT Y RESPUESTAS DEL ESP32
# =========================================================

st.divider()
st.markdown("### 📡 Comunicación con el ESP32")

estado_mqtt = obtener_estado_mqtt()

if estado_mqtt["conectado"]:
    st.success("Conectado al broker MQTT")
else:
    st.warning(
        "Sin conexión MQTT. "
        + str(estado_mqtt["error"])
    )

st.caption(
    f"Broker: {BROKER}:{PORT}"
)

st.caption(
    f"Comandos: {TOPICO_COMANDOS}"
)

st.caption(
    f"Telemetría: {TOPICO_TELEMETRIA}"
)

st.caption(
    f"Respuestas: {TOPICO_RESPUESTAS}"
)

st.markdown("#### Últimas respuestas del ESP32")

respuestas = estado_mqtt["respuestas"]

if respuestas:
    for respuesta in reversed(respuestas[-5:]):
        st.write("•", respuesta)
else:
    st.caption(
        "Todavía no se han recibido respuestas del ESP32."
    )

if st.button("🔄 Actualizar datos del corral"):
    st.rerun()

st.caption(
    "GranjaConecta · Prototipo académico de simulación."
)
