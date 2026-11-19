import hashlib
import json
import queue
import threading
import uuid
from pathlib import Path

import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

# =====================================================
# 1. CONFIGURACIÓN
# =====================================================

st.set_page_config(
    page_title="GranjaConecta - Corral",
    page_icon="🐔",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).resolve().parents[1]
RUTA_MODELO = ROOT / "keras_model.h5"
RUTA_LABELS = ROOT / "labels.txt"

# También permite ejecutar Corral.py directamente durante pruebas.
if not RUTA_MODELO.exists():
    RUTA_MODELO = Path(__file__).resolve().parent / "keras_model.h5"
if not RUTA_LABELS.exists():
    RUTA_LABELS = Path(__file__).resolve().parent / "labels.txt"

BROKER = "broker.mqttdashboard.com"
PUERTO = 1883
TOPICO_UNICO = "granjaconecta"

try:
    import paho.mqtt.client as mqtt
    ERROR_MQTT = None
except ModuleNotFoundError as exc:
    mqtt = None
    ERROR_MQTT = str(exc)

# Confianza mínima para aceptar un gesto.
# Si el modelo falla mucho, revisar primero las fotos de entrenamiento.
CONFIANZA_MINIMA = 80.0

# Evita repetir el mismo comando si Streamlit vuelve a procesar la misma foto.
# Una foto nueva genera un hash distinto.
# =====================================================
# 2. ESTILO VISUAL
# =====================================================

st.markdown(
    """
    <style>
    .stApp { background: #f4faf5; }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg,#123d2b,#245c36);
    }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    h1,h2,h3,h4,p,label,.stMarkdown { color: #245c36; }
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #c9dfc4;
        border-radius: 14px;
        padding: 12px;
    }
    div.stButton > button {
        background: #c6f36a;
        color: #17452c;
        border: 1px solid #a8d64d;
        border-radius: 11px;
        font-weight: 700;
        min-height: 43px;
    }
    div.stButton > button:hover {
        background: #b4e653;
        color: #123d2b;
        border-color: #83b833;
    }
    [data-testid="stCameraInput"] {
        background:#ffffff;
        border:1px solid #c9dfc4;
        border-radius:12px;
        padding:8px;
    }
    .alerta-roja {
        background:#fff0ed;
        border:1px solid #e99a8d;
        border-left:6px solid #d93636;
        border-radius:10px;
        padding:12px 15px;
        margin:8px 0;
        color:#7a211b;
    }
    .alerta-verde {
        background:#eaf7eb;
        border:1px solid #a9d7ac;
        border-left:6px solid #29965a;
        border-radius:10px;
        padding:12px 15px;
        margin:8px 0;
        color:#245c36;
    }
    .accion-detectada {
        background:#eaf7eb;
        border:1px solid #a9d7ac;
        border-radius:14px;
        padding:15px;
        color:#245c36;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =====================================================
# 3. ESTADO DE LA PÁGINA
# =====================================================

INICIALES = {
    "telemetria_corral": {},
    "mqtt_conectado": False,
    "respuestas_esp32": [],
    "ultimo_gesto": "Esperando gesto",
    "ultima_accion": "Ninguna",
    "ultima_confianza": None,
    "ultima_foto_hash": None,
    "ultimo_comando": "Ninguno",
    "comando_pendiente": "",
    "ultimo_error_mqtt": None,
    "ultimo_paquete": None,
}

for k, v in INICIALES.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =====================================================
# 4. MQTT: UN SOLO TÓPICO Y MENSAJES JSON
# =====================================================

@st.cache_resource
def crear_cliente_mqtt():
    cola = queue.Queue()

    if mqtt is None:
        return None, cola, "Falta instalar paho-mqtt."

    # Compatible con Paho MQTT 1.x y 2.x
    try:
        cliente = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
            client_id="GranjaConecta_Corral_" + uuid.uuid4().hex[:9],
            protocol=mqtt.MQTTv311,
        )
    except (AttributeError, TypeError):
        cliente = mqtt.Client(
            client_id="GranjaConecta_Corral_" + uuid.uuid4().hex[:9],
            protocol=mqtt.MQTTv311,
        )

    def al_conectar(client, userdata, flags, rc, *extra):
        codigo = getattr(rc, "value", rc)
        if codigo == 0:
            cola.put(("conexion", "conectado"))
            client.subscribe(TOPICO_UNICO, qos=0)
        else:
            cola.put(("conexion", f"error: {codigo}"))

    def al_desconectar(client, userdata, rc, *extra):
        cola.put(("conexion", "desconectado"))

    def al_recibir(client, userdata, mensaje):
        try:
            contenido = mensaje.payload.decode("utf-8", errors="replace")
            cola.put((mensaje.topic, contenido))
        except Exception as exc:
            cola.put(("error", str(exc)))

    cliente.on_connect = al_conectar
    cliente.on_disconnect = al_desconectar
    cliente.on_message = al_recibir

    try:
        cliente.connect(BROKER, PUERTO, keepalive=60)
        cliente.loop_start()
        return cliente, cola, None
    except Exception as exc:
        try:
            cliente.loop_stop()
            cliente.disconnect()
        except Exception:
            pass
        return None, cola, str(exc)


cliente_mqtt, cola_mqtt, error_conexion = crear_cliente_mqtt()


def enviar_comando(comando):
    """Publica un comando con el formato que espera el ESP32."""
    if cliente_mqtt is None:
        st.error("No hay cliente MQTT disponible. Revisa el broker y requirements.txt.")
        return False

    mensaje = {
        "tipo": "comando",
        "command": comando,
        "source": "corral",
    }

    try:
        resultado = cliente_mqtt.publish(
            TOPICO_UNICO,
            payload=json.dumps(mensaje, ensure_ascii=False),
            qos=0,
            retain=False,
        )
        if resultado.rc != mqtt.MQTT_ERR_SUCCESS:
            st.error(f"No se pudo publicar el comando. Código MQTT: {resultado.rc}")
            return False

        st.session_state.ultimo_comando = comando
        st.session_state.comando_pendiente = comando
        return True
    except Exception as exc:
        st.error(f"Error al enviar el comando MQTT: {exc}")
        return False


def procesar_mensajes_mqtt():
    """Procesa telemetría y respuestas, aceptando ambos formatos de datos."""
    while True:
        try:
            topic, contenido = cola_mqtt.get_nowait()
        except queue.Empty:
            break

        if topic == "conexion":
            st.session_state.mqtt_conectado = contenido == "conectado"
            if contenido.startswith("error"):
                st.session_state.ultimo_error_mqtt = contenido
            continue

        if topic == "error":
            st.session_state.ultimo_error_mqtt = contenido
            continue

        if topic != TOPICO_UNICO:
            continue

        try:
            paquete = json.loads(contenido)
        except (json.JSONDecodeError, TypeError):
            continue

        if not isinstance(paquete, dict):
            continue

        st.session_state.ultimo_paquete = paquete
        tipo = paquete.get("tipo")

        if tipo == "telemetria":
            # Firmware puede enviar {"tipo":"telemetria","datos":{...}}
            # o {"tipo":"telemetria","temperatura":...}
            datos = paquete.get("datos", paquete)
            if isinstance(datos, dict):
                st.session_state.telemetria_corral.update(datos)
                st.session_state.comando_pendiente = ""

        elif tipo == "respuesta":
            texto = paquete.get(
                "message",
                paquete.get("mensaje", paquete.get("status", paquete.get("estado", "Respuesta del ESP32")))
            )
            st.session_state.respuestas_esp32.append(str(texto))
            st.session_state.respuestas_esp32 = st.session_state.respuestas_esp32[-8:]


# =====================================================
# 5. MODELO TEACHABLE MACHINE
# =====================================================

@st.cache_resource
def cargar_modelo(ruta):
    from tensorflow.keras.models import load_model
    archivo = Path(ruta)
    if not archivo.is_file():
        raise FileNotFoundError(
            f"No se encuentra {archivo.name}. Debe estar en la raíz del repositorio."
        )
    return load_model(archivo, compile=False)


@st.cache_data
def cargar_etiquetas(ruta):
    archivo = Path(ruta)
    if not archivo.is_file():
        raise FileNotFoundError(
            "No se encuentra labels.txt en la raíz del repositorio."
        )

    etiquetas = []
    with archivo.open("r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea:
                partes = linea.split(maxsplit=1)
                etiquetas.append(partes[1] if len(partes) > 1 else partes[0])
    return etiquetas


def reconocer_gesto(foto, modelo):
    imagen = Image.open(foto).convert("RGB").resize((224, 224))
    arreglo = np.asarray(imagen, dtype=np.float32)

    entrada = np.empty((1, 224, 224, 3), dtype=np.float32)
    # Normalización habitual del modelo exportado por Teachable Machine.
    entrada[0] = (arreglo / 127.5) - 1.0

    prediccion = modelo.predict(entrada, verbose=0)[0]
    indice = int(np.argmax(prediccion))
    confianza = float(prediccion[indice]) * 100.0
    return indice, confianza


# El orden de índices coincide con labels.txt subido por la usuaria.
ACCIONES = {
    0: {
        "nombre": "Abrir puerta",
        "comando": "PUERTA_ABRIR",
        "emoji": "✋",
        "detalle": "La puerta del corral debe abrirse.",
    },
    1: {
        "nombre": "Cerrar puerta",
        "comando": "PUERTA_CERRAR",
        "emoji": "✊",
        "detalle": "La puerta del corral debe cerrarse.",
    },
    2: {
        "nombre": "Aumentar ventilación",
        "comando": "VENTILACION_SUBIR",
        "emoji": "✌️",
        "detalle": "La ventilación aumenta 25 puntos porcentuales.",
    },
    3: {
        "nombre": "Disminuir ventilación",
        "comando": "VENTILACION_BAJAR",
        "emoji": "☝️",
        "detalle": "La ventilación disminuye 25 puntos porcentuales.",
    },
    4: {
        "nombre": "Subir ajuste térmico",
        "comando": "AJUSTE_TERMICO_SUBIR",
        "emoji": "👍",
        "detalle": "Aumenta 25 puntos el ajuste térmico simulado.",
    },
    5: {
        "nombre": "Bajar ajuste térmico",
        "comando": "AJUSTE_TERMICO_BAJAR",
        "emoji": "👎",
        "detalle": "Disminuye 25 puntos el ajuste térmico simulado.",
    },
    6: {
        "nombre": "Subir ajuste de humedad",
        "comando": "HUMEDAD_SUBIR",
        "emoji": "🤟",
        "detalle": "Aumenta 25 puntos el ajuste de humedad simulado.",
    },
    7: {
        "nombre": "Bajar ajuste de humedad",
        "comando": "HUMEDAD_BAJAR",
        "emoji": "👌",
        "detalle": "Disminuye 25 puntos el ajuste de humedad simulado.",
    },
}


def ejecutar_gesto(indice, confianza):
    accion = ACCIONES.get(indice)

    if accion is None:
        st.warning("La clase reconocida no tiene un comando configurado.")
        return

    if enviar_comando(accion["comando"]):
        st.session_state.ultimo_gesto = (
            f'{accion["emoji"]} {accion["nombre"]}'
        )
        st.session_state.ultima_accion = accion["nombre"]
        st.session_state.ultima_confianza = confianza
        st.success(
            f'Gesto reconocido: {accion["nombre"]}. '
            "Orden enviada; esperando confirmación de Wokwi."
        )


# =====================================================
# 6. MENÚ LATERAL Y ENCABEZADO
# =====================================================

with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center;padding:18px 5px 22px;">
          <div style="font-size:42px;">🌱</div>
          <div style="font-size:23px;font-weight:800;">GranjaConecta</div>
          <div style="font-size:11px;letter-spacing:2px;color:#c6f36a;">
            TECNOLOGÍA PARA EL CAMPO
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.subheader("Panel del corral")
    st.write("📷 Reconocimiento de gestos")
    st.write("🚪 Puerta automática")
    st.write("🌀 Ventilación")
    st.write("🌡️ Ajuste térmico")
    st.write("💧 Ajuste de humedad")
    st.write("📊 Monitoreo ambiental")
    st.markdown("---")
    st.caption("Prototipo académico ESP32 + Wokwi + MQTT")

st.markdown(
    "<h1 style='color:#245c36;margin-bottom:0'>🐔 GranjaConecta - Corral inteligente</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='color:#477b4e;font-size:16px'>"
    "Controla el corral mediante gestos. Observa los cambios visuales "
    "y los datos que devuelve el ESP32 simulado en Wokwi."
    "</p>",
    unsafe_allow_html=True,
)

if ERROR_MQTT:
    st.error("No está instalada la librería paho-mqtt. Agrégala a requirements.txt.")
    st.stop()

if cliente_mqtt is None:
    st.warning(
        "No se pudo iniciar la conexión MQTT. "
        + str(error_conexion or "Revisa el broker.")
    )
    if st.button("Reintentar conexión MQTT"):
        crear_cliente_mqtt.clear()
        st.rerun()

# =====================================================
# 7. FUNCIONES DE REPRESENTACIÓN DEL CORRAL
# =====================================================

def numero_porcentaje(valor, predeterminado=0):
    try:
        return max(0, min(100, int(float(valor))))
    except (TypeError, ValueError):
        return predeterminado


def obtener_estado_temperatura(valor):
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "SIN DATO", "gray"

    # Rangos iniciales configurables para el prototipo.
    if v < 17:
        return "BAJA", "#3b9ddd"
    if v > 25:
        return "ALTA", "#d93636"
    return "NORMAL", "#29965a"


def obtener_estado_humedad(valor):
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "SIN DATO", "gray"

    if v < 30:
        return "BAJA", "#3b9ddd"
    if v > 60:
        return "ALTA", "#d93636"
    return "NORMAL", "#29965a"


def construir_corral(puerta, ventilacion, temperatura="--", humedad_real="--",
                     ajuste_termico=50, ajuste_humedad=50):
    ventilacion = numero_porcentaje(ventilacion, 0)
    estado_temp, color_temp = obtener_estado_temperatura(temperatura)
    estado_hum, color_hum = obtener_estado_humedad(humedad_real)
    ajuste_termico = numero_porcentaje(ajuste_termico, 50)
    ajuste_humedad = numero_porcentaje(ajuste_humedad, 50)

    # El tinte es una representación visual del ajuste simulado,
    # no un cambio físico de temperatura o humedad.
    if ajuste_termico >= 75:
        tinte_termico = "rgba(255,110,55,.15)"
    elif ajuste_termico <= 25:
        tinte_termico = "rgba(70,160,230,.15)"
    else:
        tinte_termico = "rgba(255,255,255,0)"
    opacidad_humedad = 0.04 + (ajuste_humedad / 100) * 0.22
    puerta_txt = str(puerta).strip().lower()

    puerta_abierta = puerta_txt in (
        "abierta", "abierto", "open", "1", "true"
    )

    if puerta_abierta:
        estado_puerta = "ABIERTA"
        color_puerta = "#8ccf50"
        movimiento_puerta = "translateX(-48px) rotateY(-25deg)"
    else:
        estado_puerta = "CERRADA" if puerta_txt in (
            "cerrada", "cerrado", "closed", "0", "false"
        ) else "SIN DATO"
        color_puerta = "#a66a35"
        movimiento_puerta = "translateX(0) rotateY(0)"

    # 0-25: pequeño; 50: mediano; 75-100: amplio.
    diametro = 18 + (ventilacion * 0.82)
    opacidad_aire = 0.12 + (ventilacion / 100) * 0.22
    intensidad_ventilador = 0.15 + (ventilacion / 100) * 0.85

    html = f"""
    <div style="
        height:360px;width:100%;position:relative;overflow:hidden;
        border:8px solid #754523;border-radius:16px;box-sizing:border-box;
        font-family:Arial,sans-serif;
        background:linear-gradient(#b8d9e9 0%,#dcebd3 62%,#91b66c 63%,#91b66c 100%);
    ">
      <div style="position:absolute;top:0;left:0;width:100%;height:42px;background:#754523;"></div>
      <div style="position:absolute;top:42px;left:0;width:100%;height:10px;background:#a36c3c;"></div>

      <div style="position:absolute;top:68px;left:22px;width:105px;height:78px;background:#a9e0ef;border:7px solid #754523;box-sizing:border-box;">
        <div style="position:absolute;left:50%;height:100%;width:4px;background:#754523"></div>
        <div style="position:absolute;top:50%;height:4px;width:100%;background:#754523"></div>
      </div>
      <div style="position:absolute;top:68px;right:22px;width:95px;height:78px;background:#a9e0ef;border:7px solid #754523;box-sizing:border-box;"></div>

      <div style="position:absolute;inset:52px 0 83px;background:{tinte_termico};z-index:1;pointer-events:none;transition:background .5s;"></div>
      <div style="position:absolute;inset:100px 7% 95px;border-radius:50%;background:rgba(225,245,255,{opacidad_humedad});z-index:1;pointer-events:none;"></div>

      <div style="
        position:absolute;left:50%;top:54%;width:{diametro}%;height:{diametro}%;
        transform:translate(-50%,-50%);border-radius:50%;
        background:radial-gradient(circle,rgba(110,205,245,{opacidad_aire}) 0%,rgba(110,205,245,{opacidad_aire + 0.10}) 65%,rgba(110,205,245,{opacidad_aire + 0.18}) 100%);
        border:2px dashed rgba(40,135,190,.65);
        transition:all .6s ease;z-index:1;pointer-events:none;
      "></div>

      <div style="position:absolute;top:70px;left:46%;font-size:42px;opacity:{intensidad_ventilador};z-index:2;">🌀</div>

      <div style="position:absolute;bottom:0;left:0;width:100%;height:83px;background:#8b633f;border-top:10px solid #4f8c38;box-sizing:border-box;z-index:2;"></div>

      <div style="position:absolute;bottom:73px;left:18%;font-size:48px;z-index:3;">🐔</div>
      <div style="position:absolute;bottom:77px;left:39%;font-size:54px;z-index:3;">🐓</div>
      <div style="position:absolute;bottom:72px;left:61%;font-size:47px;z-index:3;">🐔</div>
      <div style="position:absolute;bottom:76px;left:78%;font-size:45px;z-index:3;">🐔</div>

      <div style="
        position:absolute;bottom:73px;right:4%;width:62px;height:125px;
        background:{color_puerta};border:6px solid #603b21;border-radius:5px;
        box-sizing:border-box;display:flex;align-items:center;justify-content:center;
        color:white;font-size:24px;transform:{movimiento_puerta};
        transform-origin:left center;transition:transform .7s ease;z-index:4;
      ">🚪</div>

      <div style="position:absolute;top:12px;left:50%;transform:translateX(-50%);color:white;font-size:15px;font-weight:bold;z-index:5;">🐔 CORRAL DE GALLINAS</div>

      <div style="position:absolute;top:60px;left:12px;background:{color_temp};color:white;padding:6px 9px;border-radius:8px;font-size:11px;font-weight:bold;z-index:6;">🌡️ TEMP: {estado_temp}</div>
      <div style="position:absolute;top:60px;right:12px;background:{color_hum};color:white;padding:6px 9px;border-radius:8px;font-size:11px;font-weight:bold;z-index:6;">💧 HUMEDAD: {estado_hum}</div>

      <div style="
        position:absolute;bottom:9px;left:12px;right:12px;color:white;
        font-weight:bold;font-size:13px;text-shadow:1px 1px 3px #222;z-index:5;
      ">
        Puerta: {estado_puerta} &nbsp; | &nbsp;
        Ventilación: {ventilacion}% &nbsp; | &nbsp;
        Alcance del aire: {('BAJO' if ventilacion <= 25 else 'NORMAL' if ventilacion <= 50 else 'ALTO')}
      </div>
    </div>
    """
    components.html(html, height=375, scrolling=False)
    return estado_puerta, puerta_abierta


# =====================================================
# 8. PANEL EN VIVO
# =====================================================

@st.fragment(run_every="2s")
def panel_en_vivo():
    procesar_mensajes_mqtt()
    datos = st.session_state.telemetria_corral

    if st.session_state.mqtt_conectado:
        st.success(f"MQTT conectado · Tópico: {TOPICO_UNICO}")
    else:
        st.warning("Conectando con MQTT... Esperando telemetría de Wokwi.")

    if st.session_state.comando_pendiente:
        st.info(
            f"Orden enviada: {st.session_state.comando_pendiente}. "
            "Esperando actualización del ESP32..."
        )

    temperatura = datos.get("temperatura", "--")
    humedad_real = datos.get("humedad", "--")
    ventilacion = numero_porcentaje(datos.get("ventilacion", 0), 0)

    # Admite distintos nombres de campo mientras unificamos firmware.
    ajuste_termico = numero_porcentaje(
        datos.get("ajusteTermico", datos.get("ajuste_termico", 50)), 50
    )
    humedad_ajustada = numero_porcentaje(
        datos.get("humedadVisual", datos.get("ajusteHumedad", 50)), 50
    )

    puerta = datos.get("puerta", "sin dato")
    st.subheader("🏡 Vista del interior del corral")
    st.caption(
        "El círculo azul representa el alcance visual de la ventilación: "
        "pequeño cuando es baja, mediano cuando es normal y amplio cuando es alta."
    )
    # Construimos el HTML y devolvemos los estados de puerta.
    estado_puerta, puerta_abierta = construir_corral(
        puerta, ventilacion, temperatura, humedad_real,
        ajuste_termico, humedad_ajustada
    )

    st.subheader("📊 Datos recibidos del ESP32")
    a, b, c, d = st.columns(4)

    a.metric(
        "🌡️ Temperatura real",
        f"{float(temperatura):.1f} °C" if temperatura != "--" else "--",
        obtener_estado_temperatura(temperatura)[0],
    )
    b.metric(
        "💧 Humedad real",
        f"{float(humedad_real):.0f} %" if humedad_real != "--" else "--",
        obtener_estado_humedad(humedad_real)[0],
    )
    c.metric("🌀 Ventilación", f"{ventilacion} %")
    d.metric("🚪 Puerta", estado_puerta)

    x, y = st.columns(2)
    x.metric("🌡️ Ajuste térmico simulado", f"{ajuste_termico}%")
    x.progress(ajuste_termico / 100)
    y.metric("💧 Ajuste de humedad simulado", f"{humedad_ajustada}%")
    y.progress(humedad_ajustada / 100)

    st.caption(
        "Los ajustes térmico y de humedad son variables simuladas. "
        "El DHT22 continúa mostrando las mediciones ambientales reales."
    )

    # Alertas según las lecturas reales.
    alertas = []
    try:
        temp_num = float(temperatura)
        if temp_num < 17:
            alertas.append(
                f"Temperatura baja ({temp_num:.1f} °C). Revisa las condiciones térmicas del corral."
            )
        elif temp_num > 25:
            alertas.append(
                f"Temperatura alta ({temp_num:.1f} °C). Se requiere revisar el ambiente."
            )
    except (TypeError, ValueError):
        pass

    try:
        hum_num = float(humedad_real)
        if hum_num < 30:
            alertas.append(
                f"Humedad baja ({hum_num:.0f} %). El indicador requiere atención."
            )
        elif hum_num > 60:
            alertas.append(
                f"Humedad alta ({hum_num:.0f} %). El indicador requiere atención."
            )
    except (TypeError, ValueError):
        pass

    if puerta_abierta:
        alertas.append("La puerta del corral está abierta.")

    if alertas:
        st.markdown("### 🚨 Alertas del corral")
        for alerta in alertas:
            st.markdown(
                f'<div class="alerta-roja"><strong>⚠️ ATENCIÓN</strong><br>{alerta}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div class="alerta-verde"><strong>✓ CORRAL ESTABLE</strong><br>'
            'No se detectan alertas con las lecturas recibidas.</div>',
            unsafe_allow_html=True,
        )

    if st.session_state.respuestas_esp32:
        with st.expander("Respuestas recibidas del ESP32"):
            for respuesta in reversed(st.session_state.respuestas_esp32):
                st.write("• " + respuesta)


panel_en_vivo()

# =====================================================
# 9. CÁMARA Y RECONOCIMIENTO DE GESTOS
# =====================================================

st.divider()
st.subheader("📷 Reconocimiento de gestos")
st.write(
    "Toma una fotografía con la mano visible. La aplicación identificará "
    "el gesto, mostrará la acción y enviará la orden a Wokwi."
)

col_camara, col_resultado = st.columns([0.9, 1.25], gap="large")

with col_camara:
    st.markdown("#### Cámara")
    foto = st.camera_input("Toma una foto del gesto", key="camara_corral")

with col_resultado:
    st.markdown("#### Gesto y acción detectados")
    st.markdown(f"**Último gesto:** {st.session_state.ultimo_gesto}")
    st.markdown(f"**Última acción:** {st.session_state.ultima_accion}")

    if st.session_state.ultima_confianza is not None:
        st.markdown(
            f"**Confianza:** {st.session_state.ultima_confianza:.1f}%"
        )

    if foto is not None:
        hash_foto = hashlib.sha256(foto.getvalue()).hexdigest()

        if hash_foto != st.session_state.ultima_foto_hash:
            st.session_state.ultima_foto_hash = hash_foto

            try:
                modelo = cargar_modelo(str(RUTA_MODELO))
                etiquetas = cargar_etiquetas(str(RUTA_LABELS))

                indice, confianza = reconocer_gesto(foto, modelo)
                etiqueta = (
                    etiquetas[indice]
                    if indice < len(etiquetas)
                    else f"Clase {indice}"
                )

                st.write(f"**Etiqueta reconocida:** {etiqueta}")

                if len(etiquetas) != 8:
                    st.error(
                        f"Se esperaban 8 etiquetas y se encontraron {len(etiquetas)}. "
                        "Verifica labels.txt."
                    )
                elif indice not in ACCIONES:
                    st.warning("La clase reconocida no tiene una acción asignada.")
                elif confianza >= CONFIANZA_MINIMA:
                    accion = ACCIONES[indice]
                    st.markdown(
                        f"""
                        <div class="accion-detectada">
                          <div style="font-size:28px">{accion["emoji"]}</div>
                          <strong>ACCIÓN RECONOCIDA</strong><br>
                          {accion["nombre"]}<br>
                          <small>{accion["detalle"]}</small>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    ejecutar_gesto(indice, confianza)
                else:
                    st.warning(
                        f"Confianza baja ({confianza:.1f}%). "
                        "No se envió ninguna orden. Centra la mano, mejora la luz e inténtalo de nuevo."
                    )

            except Exception as exc:
                st.error(f"No se pudo ejecutar el reconocimiento: {exc}")
        else:
            st.caption(
                "Esta foto ya fue procesada. Toma otra fotografía para enviar una nueva orden."
            )

# =====================================================
# 10. CONTROLES MANUALES PARA PRUEBAS
# =====================================================

st.divider()
st.subheader("🎮 Controles manuales del corral")
st.caption(
    "Estos botones sirven para probar Wokwi sin utilizar la cámara. "
    "Las mismas órdenes se envían por MQTT."
)

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("#### 🚪 Puerta")
    if st.button("Abrir puerta", use_container_width=True, key="corral_abrir"):
        if enviar_comando("PUERTA_ABRIR"):
            st.success("Orden de apertura enviada.")
    if st.button("Cerrar puerta", use_container_width=True, key="corral_cerrar"):
        if enviar_comando("PUERTA_CERRAR"):
            st.success("Orden de cierre enviada.")

with c2:
    st.markdown("#### 🌀 Ventilación")
    if st.button("Subir ventilación", use_container_width=True, key="corral_vent_mas"):
        if enviar_comando("VENTILACION_SUBIR"):
            st.success("Orden de aumento enviada.")
    if st.button("Bajar ventilación", use_container_width=True, key="corral_vent_menos"):
        if enviar_comando("VENTILACION_BAJAR"):
            st.success("Orden de disminución enviada.")

with c3:
    st.markdown("#### 🌡️ Ajuste térmico")
    if st.button("Subir ajuste térmico", use_container_width=True, key="corral_term_mas"):
        if enviar_comando("AJUSTE_TERMICO_SUBIR"):
            st.success("Orden de aumento enviada.")
    if st.button("Bajar ajuste térmico", use_container_width=True, key="corral_term_menos"):
        if enviar_comando("AJUSTE_TERMICO_BAJAR"):
            st.success("Orden de disminución enviada.")

c4, c5 = st.columns(2)
with c4:
    st.markdown("#### 💧 Ajuste de humedad")
    if st.button("Subir ajuste de humedad", use_container_width=True, key="corral_hum_mas"):
        if enviar_comando("HUMEDAD_SUBIR"):
            st.success("Orden de aumento enviada.")
    if st.button("Bajar ajuste de humedad", use_container_width=True, key="corral_hum_menos"):
        if enviar_comando("HUMEDAD_BAJAR"):
            st.success("Orden de disminución enviada.")

st.divider()
st.caption(
    "GranjaConecta | ESP32 + Wokwi + MQTT | "
    "Prototipo académico de monitoreo y control del corral de gallinas."
)
