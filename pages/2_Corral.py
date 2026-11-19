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
# 1. CONFIGURACION Y RUTAS
# =====================================================

st.set_page_config(
    page_title="GranjaConecta - Corral",
    page_icon="🐄",
    layout="wide",
    initial_sidebar_state="expanded",
)

CARPETA_PROYECTO = Path(__file__).resolve().parents[1]
RUTA_MODELO = CARPETA_PROYECTO / "keras_model.h5"
RUTA_LABELS = CARPETA_PROYECTO / "labels.txt"

BROKER = "broker.mqttdashboard.com"
PUERTO = 1883
TOPICO_COMANDOS = "granjaconecta/comandos"
TOPICO_TELEMETRIA = "granjaconecta/telemetria"
TOPICO_RESPUESTAS = "granjaconecta/respuestas"

# Paho MQTT 2.1.0. Si no está instalado, mostrar un mensaje claro
# en la página en lugar de un traceback poco útil.
try:
    import paho.mqtt.client as mqtt
    ERROR_IMPORT_MQTT = None
except ModuleNotFoundError as error:
    mqtt = None
    ERROR_IMPORT_MQTT = str(error)

# =====================================================
# 2. ESTILOS
# =====================================================

st.markdown(
    """
    <style>
    .stApp { background-color: #e5f2d8; }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #123d2b 0%, #245c36 100%);
    }
    section[data-testid="stSidebar"] * { color: white !important; }
    h1, h2, h3 { color: #245c36; }
    div[data-testid="stMetric"] {
        background-color: #f7fff1;
        border: 1px solid #b8d5a5;
        padding: 12px;
        border-radius: 12px;
    }
    div.stButton > button {
        border-radius: 10px;
        font-weight: bold;
        min-height: 42px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =====================================================
# 3. ESTADO DE STREAMLIT
# =====================================================

VALORES_INICIALES = {
    "telemetria": {},
    "respuestas": [],
    "ultimo_gesto": "Esperando gesto",
    "ultima_accion": "Ninguna",
    "humedad_visual": 50,
    "ultima_imagen": None,
    "mqtt_estado": False,
}
for clave, valor in VALORES_INICIALES.items():
    if clave not in st.session_state:
        st.session_state[clave] = valor

# =====================================================
# 4. CONEXION MQTT
# =====================================================

@st.cache_resource
def crear_conexion_mqtt():
    """Crea un cliente MQTT persistente y una cola para mensajes entrantes."""
    mensajes = queue.Queue()

    if mqtt is None:
        return None, mensajes, "No está instalado paho-mqtt. Revisa requirements.txt."

    cliente = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="GranjaConecta_Corral_" + uuid.uuid4().hex[:8],
        protocol=mqtt.MQTTv311,
    )

    def al_conectar(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            mensajes.put(("conexion", "conectado"))
            client.subscribe(TOPICO_TELEMETRIA, qos=0)
            client.subscribe(TOPICO_RESPUESTAS, qos=0)
        else:
            mensajes.put(("conexion", f"error: {reason_code}"))

    def al_desconectar(client, userdata, disconnect_flags, reason_code, properties):
        mensajes.put(("conexion", "desconectado"))

    def al_recibir(client, userdata, mensaje):
        try:
            contenido = mensaje.payload.decode("utf-8")
            mensajes.put((mensaje.topic, contenido))
        except Exception as error:
            print("Error recibiendo MQTT:", error)

    cliente.on_connect = al_conectar
    cliente.on_disconnect = al_desconectar
    cliente.on_message = al_recibir

    try:
        cliente.connect(BROKER, PUERTO, keepalive=60)
        cliente.loop_start()
        return cliente, mensajes, None
    except Exception as error:
        try:
            cliente.loop_stop()
            cliente.disconnect()
        except Exception:
            pass
        return None, mensajes, str(error)


cliente_mqtt, cola_mensajes, error_mqtt = crear_conexion_mqtt()

# =====================================================
# 5. PUBLICAR COMANDOS
# =====================================================

def publicar_comando(comando):
    if cliente_mqtt is None:
        st.error("No hay conexión MQTT. Revisa el estado del broker.")
        return False

    try:
        resultado = cliente_mqtt.publish(
            TOPICO_COMANDOS,
            payload=comando,
            qos=0,
            retain=False,
        )
        if resultado.rc == mqtt.MQTT_ERR_SUCCESS:
            return True

        st.error(f"No se pudo publicar el comando MQTT. Código: {resultado.rc}")
        return False
    except Exception as error:
        st.error(f"Error enviando el comando: {error}")
        return False


# =====================================================
# 6. PROCESAR TELEMETRIA Y RESPUESTAS
# =====================================================

def procesar_mensajes():
    while True:
        try:
            topico, contenido = cola_mensajes.get_nowait()

            if topico == "conexion":
                st.session_state.mqtt_estado = contenido == "conectado"

            elif topico == TOPICO_TELEMETRIA:
                datos = json.loads(contenido)
                if isinstance(datos, dict):
                    st.session_state.telemetria.update(datos)
                    if "humedadVisual" in datos:
                        st.session_state.humedad_visual = max(
                            0, min(100, int(float(datos["humedadVisual"])))
                        )

            elif topico == TOPICO_RESPUESTAS:
                st.session_state.respuestas.append(contenido)
                st.session_state.respuestas = st.session_state.respuestas[-10:]

        except queue.Empty:
            break
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            print("Mensaje MQTT no válido:", error)
        except Exception as error:
            print("Error procesando mensajes MQTT:", error)
            break


# =====================================================
# 7. MONITOREO AUTOMATICO
# =====================================================

@st.fragment(run_every="2s")
def mostrar_monitoreo():
    procesar_mensajes()
    datos = st.session_state.telemetria

    st.subheader("📊 Monitoreo del corral")

    if st.session_state.mqtt_estado:
        st.success("Conectado al broker MQTT")
    else:
        st.warning("Esperando conexión MQTT o telemetría del ESP32...")

    temperatura = datos.get("temperatura", "--")
    humedad = datos.get("humedad", "--")
    ventilacion = datos.get("ventilacion", "--")
    puerta = datos.get("puerta", "--")
    nivel_agua = datos.get("nivelAgua", "--")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("🌡️ Temperatura", f"{temperatura} °C" if temperatura != "--" else "--")
    with c2:
        st.metric("💧 Humedad real", f"{humedad} %" if humedad != "--" else "--")
    with c3:
        st.metric("🌀 Ventilación", f"{ventilacion} %" if ventilacion != "--" else "--")
    with c4:
        st.metric("🚪 Puerta", str(puerta))

    st.metric("💧 Humedad visual", f"{st.session_state.humedad_visual}%")
    st.caption(
        "La humedad visual es una representación gráfica. "
        "No modifica la humedad real medida por el DHT22."
    )
    st.caption(f"Último nivel de agua recibido: {nivel_agua}%")

    if st.session_state.respuestas:
        with st.expander("📩 Últimas respuestas del ESP32"):
            for respuesta in reversed(st.session_state.respuestas):
                st.write("• " + respuesta)


# =====================================================
# 8. CARGAR MODELO Y ETIQUETAS
# =====================================================

@st.cache_resource
def cargar_modelo(ruta_modelo):
    from tensorflow.keras.models import load_model

    ruta = Path(ruta_modelo)
    if not ruta.is_file():
        raise FileNotFoundError(f"No se encuentra el modelo: {ruta}")
    return load_model(ruta, compile=False)


@st.cache_data
def cargar_etiquetas(ruta_labels):
    ruta = Path(ruta_labels)
    if not ruta.is_file():
        raise FileNotFoundError(f"No se encuentra labels.txt: {ruta}")

    etiquetas = []
    with ruta.open("r", encoding="utf-8") as archivo:
        for linea in archivo:
            linea = linea.strip()
            if not linea:
                continue
            partes = linea.split(maxsplit=1)
            etiquetas.append(partes[1] if len(partes) == 2 else partes[0])
    return etiquetas


# =====================================================
# 9. RECONOCIMIENTO DE GESTOS
# =====================================================

def reconocer_gesto(imagen_subida, modelo):
    imagen = Image.open(imagen_subida).convert("RGB").resize((224, 224))
    arreglo = np.asarray(imagen, dtype=np.float32)

    datos = np.empty((1, 224, 224, 3), dtype=np.float32)
    # Se conserva la normalización del código de Teachable Machine
    # que utilizabas en tu aplicación anterior.
    datos[0] = (arreglo / 127.0) - 1.0

    prediccion = modelo.predict(datos, verbose=0)
    indice = int(np.argmax(prediccion[0]))
    confianza = float(prediccion[0][indice]) * 100.0
    return indice, confianza


# =====================================================
# 10. MAPEO DE LAS SEIS CLASES
# =====================================================

ACCIONES = {
    0: {"nombre": "Abrir puerta", "comando": "PUERTA_ABRIR", "emoji": "✋"},
    1: {"nombre": "Cerrar puerta", "comando": "PUERTA_CERRAR", "emoji": "✊"},
    2: {"nombre": "Subir ventilación", "comando": "VENTILACION_SUBIR", "emoji": "👍"},
    3: {"nombre": "Bajar ventilación", "comando": "VENTILACION_BAJAR", "emoji": "👎"},
    4: {"nombre": "Subir humedad visual", "comando": "HUMEDAD_SUBIR", "emoji": "🫶"},
    5: {"nombre": "Bajar humedad visual", "comando": "HUMEDAD_BAJAR", "emoji": "🫶"},
}


def ejecutar_gesto(indice):
    if indice not in ACCIONES:
        st.error("Gesto no reconocido.")
        return

    accion = ACCIONES[indice]
    if publicar_comando(accion["comando"]):
        st.session_state.ultimo_gesto = f'{accion["emoji"]} {accion["nombre"]}'
        st.session_state.ultima_accion = accion["nombre"]
        st.success(f"Comando {accion['nombre'].lower()} enviado al broker MQTT.")
        # El valor de humedad visual se actualiza con la telemetría del ESP32.
        # No se modifica aquí para evitar mostrar un estado no confirmado.


# =====================================================
# 11. BARRA LATERAL
# =====================================================

with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center; padding:18px 5px 22px;">
            <div style="font-size:40px;">🌱</div>
            <div style="font-size:22px; font-weight:800;">GranjaConecta</div>
            <div style="font-size:11px; letter-spacing:2px; color:#c6f36a;">
                TECNOLOGÍA PARA EL CAMPO
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.subheader("Panel del corral")
    st.write("📷 Reconocimiento de gestos")
    st.write("🚪 Control de puerta")
    st.write("🌀 Control de ventilación")
    st.write("💧 Humedad visual")
    st.write("🌡️ Monitoreo ambiental")
    st.markdown("---")
    st.caption("Sistema académico de simulación")


# =====================================================
# 12. ENCABEZADO Y ESTADO MQTT
# =====================================================

st.title("🐄 GranjaConecta - Corral")
st.write(
    "Monitoreo y control del corral mediante "
    "reconocimiento de gestos y comunicación MQTT."
)

if ERROR_IMPORT_MQTT:
    st.error(
        "No está instalada la librería paho-mqtt en el entorno de Streamlit. "
        "Comprueba que requirements.txt esté en la raíz del repositorio "
        "y que la instalación de dependencias haya terminado correctamente."
    )
    st.code("paho-mqtt==2.1.0")
    st.stop()

if cliente_mqtt is None:
    st.error("No se pudo iniciar MQTT. Comprueba el broker y la conexión.")
    if error_mqtt:
        st.caption(error_mqtt)
    if st.button("Reintentar conexión MQTT"):
        crear_conexion_mqtt.clear()
        st.rerun()

# =====================================================
# 13. ESCENARIO DEL GRANERO
# =====================================================

st.divider()
st.subheader("🏡 Interior del granero")

humedad_actual = st.session_state.humedad_visual
datos_actuales = st.session_state.telemetria
estado_puerta = str(datos_actuales.get("puerta", "Sin dato")).lower()
nivel_ventilacion = datos_actuales.get("ventilacion", "--")

if estado_puerta in ("abierta", "abierto", "open", "1", "true"):
    texto_puerta = "Puerta abierta"
    color_puerta = "#76b947"
elif estado_puerta in ("cerrada", "cerrado", "closed", "0", "false"):
    texto_puerta = "Puerta cerrada"
    color_puerta = "#9b6338"
else:
    texto_puerta = "Estado de puerta sin dato"
    color_puerta = "#9b6338"

html_granero = f"""
<div style="
    width:100%; height:320px;
    background:linear-gradient(#b8d9e9 0%,#dcebd3 70%);
    border:8px solid #754523; border-radius:15px;
    position:relative; overflow:hidden; font-family:Arial,sans-serif;
    box-sizing:border-box;">
    <div style="position:absolute; top:0; width:100%; height:45px; background:#754523;"></div>
    <div style="position:absolute; top:45px; left:0; width:100%; height:12px; background:#9c6536;"></div>
    <div style="position:absolute; top:65px; left:20px; width:115px; height:85px;
        background:#9ed7ed; border:9px solid #754523; box-sizing:border-box;">
        <div style="position:absolute; left:50%; height:100%; width:5px; background:#754523;"></div>
        <div style="position:absolute; top:50%; height:5px; width:100%; background:#754523;"></div>
    </div>
    <div style="position:absolute; bottom:0; width:100%; height:90px;
        background:#8d633e; border-top:12px solid #4f8c38; box-sizing:border-box;"></div>
    <div style="position:absolute; bottom:62px; left:39%; font-size:88px;">🐄</div>
    <div style="position:absolute; bottom:90px; right:8%; width:75px; height:130px;
        background:{color_puerta}; border:6px solid #603b21; border-radius:5px;
        display:flex; align-items:center; justify-content:center; color:white; font-size:26px;">
        🚪
    </div>
    <div style="position:absolute; top:75px; right:35%; font-size:42px;">🌀</div>
    <div style="position:absolute; top:145px; left:5%; font-size:24px;">🌫️</div>
    <div style="position:absolute; top:170px; right:15%; font-size:24px;">🌫️</div>
    <div style="position:absolute; bottom:12px; left:15px; color:white;
        font-weight:bold; font-size:14px; text-shadow:1px 1px 3px black;">
        {texto_puerta} · Ventilación: {nivel_ventilacion}% · Humedad visual: {humedad_actual}%
    </div>
</div>
"""
components.html(html_granero, height=340, scrolling=False)

# =====================================================
# 14. CAMARA Y RECONOCIMIENTO
# =====================================================

st.divider()
st.subheader("📷 Reconocimiento de gestos")

col_camara, col_resultado = st.columns([1, 1])

with col_camara:
    st.markdown("#### Cámara")
    foto = st.camera_input(
        "Toma una fotografía de tu gesto",
        key="camara_corral",
    )

with col_resultado:
    st.markdown("#### Resultado del reconocimiento")
    st.info("Último gesto: " + st.session_state.ultimo_gesto)
    st.info("Acción: " + st.session_state.ultima_accion)

    if foto is not None:
        contenido = foto.getvalue()
        hash_imagen = hashlib.md5(contenido).hexdigest()

        if hash_imagen != st.session_state.ultima_imagen:
            st.session_state.ultima_imagen = hash_imagen

            try:
                modelo = cargar_modelo(str(RUTA_MODELO))
                etiquetas = cargar_etiquetas(str(RUTA_LABELS))
                indice, confianza = reconocer_gesto(foto, modelo)

                if indice >= len(etiquetas):
                    st.error(
                        "El índice reconocido no coincide con las etiquetas. "
                        "Comprueba labels.txt y el modelo."
                    )
                else:
                    st.write("Etiqueta del modelo: " + etiquetas[indice])
                    if confianza >= 70:
                        st.success(f"Confianza: {confianza:.1f}%")
                        if indice in ACCIONES:
                            ejecutar_gesto(indice)
                        else:
                            st.warning("La clase reconocida no tiene una acción configurada.")
                    else:
                        st.warning(
                            f"Confianza baja: {confianza:.1f}%. "
                            "Intenta otra fotografía."
                        )
            except Exception as error:
                st.error(f"Error al cargar o ejecutar el modelo: {error}")
        else:
            st.caption("Esta misma fotografía ya fue procesada. Toma otra para repetir.")

# =====================================================
# 15. MONITOREO AUTOMATICO
# =====================================================

st.divider()
mostrar_monitoreo()

# =====================================================
# 16. CONTROLES MANUALES
# =====================================================

st.divider()
st.subheader("🎮 Controles manuales del corral")

col_puerta, col_ventilacion, col_humedad = st.columns(3)

with col_puerta:
    st.markdown("#### 🚪 Puerta")
    if st.button("Abrir puerta", use_container_width=True):
        if publicar_comando("PUERTA_ABRIR"):
            st.success("Comando enviado al broker MQTT.")
    if st.button("Cerrar puerta", use_container_width=True):
        if publicar_comando("PUERTA_CERRAR"):
            st.success("Comando enviado al broker MQTT.")

with col_ventilacion:
    st.markdown("#### 🌀 Ventilación")
    if st.button("Subir ventilación", use_container_width=True):
        if publicar_comando("VENTILACION_SUBIR"):
            st.success("Comando enviado al broker MQTT.")
    if st.button("Bajar ventilación", use_container_width=True):
        if publicar_comando("VENTILACION_BAJAR"):
            st.success("Comando enviado al broker MQTT.")

with col_humedad:
    st.markdown("#### 💧 Humedad visual")
    if st.button("Subir humedad visual", use_container_width=True):
        if publicar_comando("HUMEDAD_SUBIR"):
            st.success("Comando enviado al broker MQTT.")
    if st.button("Bajar humedad visual", use_container_width=True):
        if publicar_comando("HUMEDAD_BAJAR"):
            st.success("Comando enviado al broker MQTT.")

# =====================================================
# 17. PIE DE PAGINA
# =====================================================

st.divider()
st.caption(
    "GranjaConecta | ESP32 + Wokwi + MQTT | "
    "Prototipo académico de monitoreo y control ganadero."
)
