import hashlib
import json
import queue
import uuid
from pathlib import Path

import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

# =====================================================
# 1. CONFIGURACION
# =====================================================
st.set_page_config(
    page_title="GranjaConecta - Corral",
    page_icon="🐄",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).resolve().parents[1]
RUTA_MODELO = ROOT / "keras_model.h5"
RUTA_LABELS = ROOT / "labels.txt"
BROKER = "broker.mqttdashboard.com"
PUERTO = 1883
TOPICO_UNICO = "granjaconecta"

try:
    import paho.mqtt.client as mqtt
    ERROR_MQTT = None
except ModuleNotFoundError as exc:
    mqtt = None
    ERROR_MQTT = str(exc)

# =====================================================
# 2. ESTILO VERDE
# =====================================================
st.markdown(
    """
    <style>
    .stApp { background: #f4faf5; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg,#123d2b,#245c36); }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    h1,h2,h3,h4,p,label,.stMarkdown { color: #245c36; }
    [data-testid="stMetric"] {
        background: #ffffff; border: 1px solid #c9dfc4;
        border-radius: 14px; padding: 12px;
    }
    div.stButton > button {
        background: #c6f36a; color: #17452c; border: 1px solid #a8d64d;
        border-radius: 11px; font-weight: 700; min-height: 43px;
    }
    div.stButton > button:hover { background: #b4e653; color: #123d2b; border-color: #83b833; }
    [data-testid="stCameraInput"] { background:#ffffff; border:1px solid #c9dfc4; border-radius:12px; padding:8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# =====================================================
# 3. ESTADO DE LA PAGINA
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
    "ultima_humedad_visual": 50,
}
for k, v in INICIALES.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =====================================================
# 4. MQTT: UN SOLO TOPIC Y MENSAJES JSON TIPADOS
# =====================================================
@st.cache_resource
def crear_cliente_mqtt():
    cola = queue.Queue()
    if mqtt is None:
        return None, cola, "Falta paho-mqtt. Verifica requirements.txt."

    cliente = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="GranjaConecta_Corral_" + uuid.uuid4().hex[:9],
        protocol=mqtt.MQTTv311,
    )

    def al_conectar(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            cola.put(("conexion", "conectado"))
            client.subscribe(TOPICO_UNICO, qos=0)
        else:
            cola.put(("conexion", f"error: {reason_code}"))

    def al_desconectar(client, userdata, disconnect_flags, reason_code, properties):
        cola.put(("conexion", "desconectado"))

    def al_recibir(client, userdata, mensaje):
        try:
            cola.put((mensaje.topic, mensaje.payload.decode("utf-8", errors="replace")))
        except Exception as exc:
            print("Error leyendo MQTT:", exc)

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
    """Publica un comando en granjaconecta. La interfaz espera confirmacion/telemetria."""
    if cliente_mqtt is None:
        st.error("No hay cliente MQTT conectado. Revisa el broker y requirements.txt.")
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
            st.error(f"No se pudo publicar el comando. Codigo MQTT: {resultado.rc}")
            return False
        st.session_state.ultimo_comando = comando
        st.session_state.comando_pendiente = comando
        return True
    except Exception as exc:
        st.error(f"Error al enviar el comando MQTT: {exc}")
        return False


def procesar_mensajes_mqtt():
    """Procesa unicamente telemetria/respuestas del topic compartido."""
    while True:
        try:
            topic, contenido = cola_mqtt.get_nowait()
        except queue.Empty:
            break

        if topic == "conexion":
            st.session_state.mqtt_conectado = contenido == "conectado"
            continue
        if topic != TOPICO_UNICO:
            continue
        try:
            paquete = json.loads(contenido)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(paquete, dict):
            continue

        tipo = paquete.get("tipo")
        if tipo == "telemetria":
            datos = paquete.get("datos", {})
            if isinstance(datos, dict):
                st.session_state.telemetria_corral.update(datos)
                if "humedadVisual" in datos:
                    st.session_state.ultima_humedad_visual = max(
                        0, min(100, int(float(datos["humedadVisual"])))
                    )
                # Una telemetria nueva confirma que el ESP32 sigue respondiendo.
                st.session_state.comando_pendiente = ""
        elif tipo == "respuesta":
            texto = paquete.get("message", paquete.get("status", "Respuesta del ESP32"))
            st.session_state.respuestas_esp32.append(str(texto))
            st.session_state.respuestas_esp32 = st.session_state.respuestas_esp32[-8:]


# =====================================================
# 5. MODELO Y RECONOCIMIENTO DE GESTOS
# =====================================================
@st.cache_resource
def cargar_modelo(ruta):
    from tensorflow.keras.models import load_model
    archivo = Path(ruta)
    if not archivo.is_file():
        raise FileNotFoundError(f"No se encuentra {archivo.name} en la raiz del repositorio.")
    return load_model(archivo, compile=False)


@st.cache_data
def cargar_etiquetas(ruta):
    archivo = Path(ruta)
    if not archivo.is_file():
        raise FileNotFoundError("No se encuentra labels.txt en la raiz del repositorio.")
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
    # Se conserva la normalizacion usada al entrenar/exportar el modelo.
    entrada[0] = (arreglo / 127.0) - 1.0
    prediccion = modelo.predict(entrada, verbose=0)
    indice = int(np.argmax(prediccion[0]))
    confianza = float(prediccion[0][indice]) * 100.0
    return indice, confianza


# El orden corresponde a las seis clases del modelo Teachable Machine.
ACCIONES = {
    0: {"nombre": "Abrir puerta", "comando": "PUERTA_ABRIR", "emoji": "✋"},
    1: {"nombre": "Cerrar puerta", "comando": "PUERTA_CERRAR", "emoji": "✊"},
    2: {"nombre": "Subir ventilacion", "comando": "VENTILACION_SUBIR", "emoji": "👍"},
    3: {"nombre": "Bajar ventilacion", "comando": "VENTILACION_BAJAR", "emoji": "👎"},
    4: {"nombre": "Subir humedad visual", "comando": "HUMEDAD_SUBIR", "emoji": "🫶"},
    5: {"nombre": "Bajar humedad visual", "comando": "HUMEDAD_BAJAR", "emoji": "🫶"},
}


def ejecutar_gesto(indice, confianza):
    accion = ACCIONES.get(indice)
    if accion is None:
        st.warning("La clase reconocida no tiene un comando configurado.")
        return
    if enviar_comando(accion["comando"]):
        st.session_state.ultimo_gesto = f'{accion["emoji"]} {accion["nombre"]}'
        st.session_state.ultima_accion = accion["nombre"]
        st.session_state.ultima_confianza = confianza
        st.success("Orden enviada al ESP32. La imagen del corral cambiara al recibir la telemetria.")

# =====================================================
# 6. MENU Y ENCABEZADO
# =====================================================
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center;padding:18px 5px 22px;">
          <div style="font-size:42px;">🌱</div>
          <div style="font-size:23px;font-weight:800;">GranjaConecta</div>
          <div style="font-size:11px;letter-spacing:2px;color:#c6f36a;">TECNOLOGIA PARA EL CAMPO</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.subheader("Panel del corral")
    st.write("📷 Reconocimiento de gestos")
    st.write("🚪 Puerta")
    st.write("🌀 Ventilacion")
    st.write("💧 Humedad visual")
    st.write("🌡️ Monitoreo ambiental")
    st.markdown("---")
    st.caption("Prototipo academico ESP32 + Wokwi + MQTT")

st.markdown("<h1 style='color:#245c36;margin-bottom:0'>🐄 GranjaConecta - Corral inteligente</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='color:#477b4e;font-size:16px'>Controla el corral desde Streamlit. Los cambios visuales se actualizan con los datos que devuelve el ESP32 simulado en Wokwi.</p>",
    unsafe_allow_html=True,
)

if ERROR_MQTT:
    st.error("No esta instalada la libreria paho-mqtt. Agrega paho-mqtt==2.1.0 a requirements.txt.")
    st.stop()
if cliente_mqtt is None:
    st.warning("No se pudo iniciar la conexion MQTT. " + str(error_conexion or "Revisa el broker."))
    if st.button("Reintentar conexion MQTT"):
        crear_cliente_mqtt.clear()
        st.rerun()

# =====================================================
# 7. ESCENA VISUAL + TELEMETRIA (SE REFRESCA CADA 2 SEGUNDOS)
# =====================================================
@st.fragment(run_every="2s")
def panel_en_vivo():
    procesar_mensajes_mqtt()
    datos = st.session_state.telemetria_corral

    if st.session_state.mqtt_conectado:
        st.success("MQTT conectado · Topic: granjaconecta")
    else:
        st.warning("Conectando con MQTT... Esperando telemetria de Wokwi.")

    if st.session_state.comando_pendiente:
        st.info(f"Orden enviada: {st.session_state.comando_pendiente}. Esperando actualizacion del ESP32...")

    temperatura = datos.get("temperatura", "--")
    humedad_real = datos.get("humedad", "--")
    puerta = str(datos.get("puerta", "sin dato")).lower()
    ventilacion = datos.get("ventilacion", "--")
    humedad_visual = int(float(datos.get("humedadVisual", st.session_state.ultima_humedad_visual)))
    humedad_visual = max(0, min(100, humedad_visual))

    puerta_abierta = puerta in ("abierta", "abierto", "open", "1", "true")
    puerta_cerrada = puerta in ("cerrada", "cerrado", "closed", "0", "false")
    if puerta_abierta:
        estado_puerta = "ABIERTA"
        color_puerta = "#86c94b"
        transform_puerta = "translateX(-42px) rotateY(-24deg)"
    elif puerta_cerrada:
        estado_puerta = "CERRADA"
        color_puerta = "#a66a35"
        transform_puerta = "translateX(0) rotateY(0)"
    else:
        estado_puerta = "SIN DATO"
        color_puerta = "#a66a35"
        transform_puerta = "translateX(0) rotateY(0)"

    try:
        ventilacion_num = max(0, min(100, int(float(ventilacion))))
    except (TypeError, ValueError):
        ventilacion_num = 0
    intensidad_ventilador = max(0.2, ventilacion_num / 100)
    niebla_opacidad = 0.08 + (humedad_visual / 100) * 0.48

    st.subheader("🏡 Vista del interior del corral")
    html = f"""
    <div style="height:345px;width:100%;position:relative;overflow:hidden;border:8px solid #754523;border-radius:16px;box-sizing:border-box;font-family:Arial,sans-serif;background:linear-gradient(#b8d9e9 0%,#dcebd3 66%,#91b66c 67%,#91b66c 100%);">
      <div style="position:absolute;top:0;left:0;width:100%;height:43px;background:#754523;"></div>
      <div style="position:absolute;top:43px;left:0;width:100%;height:11px;background:#a36c3c;"></div>
      <div style="position:absolute;top:67px;left:22px;width:112px;height:82px;background:#a9e0ef;border:8px solid #754523;box-sizing:border-box;"><div style="position:absolute;left:50%;height:100%;width:4px;background:#754523"></div><div style="position:absolute;top:50%;height:4px;width:100%;background:#754523"></div></div>
      <div style="position:absolute;top:65px;right:24px;width:95px;height:80px;background:#a9e0ef;border:8px solid #754523;box-sizing:border-box;"></div>
      <div style="position:absolute;bottom:0;left:0;width:100%;height:86px;background:#8b633f;border-top:10px solid #4f8c38;box-sizing:border-box;"></div>
      <div style="position:absolute;bottom:64px;left:39%;font-size:88px;z-index:2;">🐄</div>
      <div style="position:absolute;bottom:78px;right:7%;width:72px;height:132px;background:{color_puerta};border:6px solid #603b21;border-radius:5px;box-sizing:border-box;display:flex;align-items:center;justify-content:center;color:white;font-size:28px;transform:{transform_puerta};transform-origin:left center;transition:transform .7s ease;z-index:3;">🚪</div>
      <div style="position:absolute;top:72px;left:48%;font-size:43px;opacity:{intensidad_ventilador};">🌀</div>
      <div style="position:absolute;top:130px;left:10%;right:10%;height:95px;pointer-events:none;opacity:{niebla_opacidad};font-size:31px;letter-spacing:17px;">🌫️　🌫️　🌫️　🌫️</div>
      <div style="position:absolute;bottom:10px;left:15px;right:15px;color:white;font-weight:bold;font-size:14px;text-shadow:1px 1px 3px #222;z-index:5;">Puerta: {estado_puerta}　|　Ventilacion: {ventilacion_num}%　|　Humedad visual: {humedad_visual}%</div>
    </div>
    """
    components.html(html, height=360, scrolling=False)

    st.subheader("📊 Datos recibidos del ESP32")
    a, b, c, d = st.columns(4)
    a.metric("🌡️ Temperatura", f"{temperatura} °C" if temperatura != "--" else "--")
    b.metric("💧 Humedad real", f"{humedad_real} %" if humedad_real != "--" else "--")
    c.metric("🌀 Ventilacion", f"{ventilacion_num} %" if ventilacion != "--" else "--")
    d.metric("🚪 Puerta", estado_puerta)
    st.metric("💧 Humedad visual", f"{humedad_visual}%")
    st.caption("La humedad visual modifica solo la niebla representada; no cambia la humedad real medida por el DHT22.")

    if st.session_state.respuestas_esp32:
        with st.expander("Respuestas recibidas del ESP32"):
            for respuesta in reversed(st.session_state.respuestas_esp32):
                st.write("• " + respuesta)

panel_en_vivo()

# =====================================================
# 8. CAMARA PEQUENA A LA IZQUIERDA Y RESULTADO A LA DERECHA
# =====================================================
st.divider()
st.subheader("📷 Reconocimiento de gestos")
col_camara, col_resultado = st.columns([0.85, 1.35], gap="large")
with col_camara:
    st.markdown("#### Camara")
    foto = st.camera_input("Toma una foto del gesto", key="camara_corral")
with col_resultado:
    st.markdown("#### Gesto y accion detectados")
    st.markdown(f"**Ultimo gesto:** {st.session_state.ultimo_gesto}")
    st.markdown(f"**Accion:** {st.session_state.ultima_accion}")
    if st.session_state.ultima_confianza is not None:
        st.markdown(f"**Confianza:** {st.session_state.ultima_confianza:.1f}%")
    if foto is not None:
        hash_foto = hashlib.sha256(foto.getvalue()).hexdigest()
        if hash_foto != st.session_state.ultima_foto_hash:
            st.session_state.ultima_foto_hash = hash_foto
            try:
                modelo = cargar_modelo(str(RUTA_MODELO))
                etiquetas = cargar_etiquetas(str(RUTA_LABELS))
                indice, confianza = reconocer_gesto(foto, modelo)
                etiqueta = etiquetas[indice] if indice < len(etiquetas) else f"Clase {indice}"
                st.write(f"**Etiqueta del modelo:** {etiqueta}")
                if confianza >= 70:
                    if indice in ACCIONES:
                        ejecutar_gesto(indice, confianza)
                    else:
                        st.warning("La clase reconocida no tiene accion asignada.")
                else:
                    st.warning(f"Confianza baja ({confianza:.1f}%). Toma otra foto con la mano bien visible.")
            except Exception as exc:
                st.error(f"No se pudo ejecutar el reconocimiento: {exc}")
        else:
            st.caption("Esta foto ya fue procesada. Toma otra para enviar una nueva orden.")

# =====================================================
# 9. CONTROLES MANUALES DESDE STREAMLIT
# =====================================================
st.divider()
st.subheader("🎮 Controles manuales del corral")
st.caption("Puedes enviar las mismas ordenes sin utilizar la camara.")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("#### 🚪 Puerta")
    if st.button("Abrir puerta", use_container_width=True, key="corral_abrir"):
        if enviar_comando("PUERTA_ABRIR"):
            st.success("Orden enviada. La puerta se mostrara abierta cuando llegue la telemetria.")
    if st.button("Cerrar puerta", use_container_width=True, key="corral_cerrar"):
        if enviar_comando("PUERTA_CERRAR"):
            st.success("Orden enviada. La puerta se mostrara cerrada cuando llegue la telemetria.")
with c2:
    st.markdown("#### 🌀 Ventilacion")
    if st.button("Subir ventilacion", use_container_width=True, key="corral_vent_mas"):
        if enviar_comando("VENTILACION_SUBIR"):
            st.success("Orden enviada al ESP32.")
    if st.button("Bajar ventilacion", use_container_width=True, key="corral_vent_menos"):
        if enviar_comando("VENTILACION_BAJAR"):
            st.success("Orden enviada al ESP32.")
with c3:
    st.markdown("#### 💧 Humedad visual")
    if st.button("Subir humedad visual", use_container_width=True, key="corral_hum_mas"):
        if enviar_comando("HUMEDAD_SUBIR"):
            st.success("Orden enviada al ESP32.")
    if st.button("Bajar humedad visual", use_container_width=True, key="corral_hum_menos"):
        if enviar_comando("HUMEDAD_BAJAR"):
            st.success("Orden enviada al ESP32.")

st.divider()
st.caption("GranjaConecta | ESP32 + Wokwi + MQTT | Prototipo academico de monitoreo y control ganadero.")
