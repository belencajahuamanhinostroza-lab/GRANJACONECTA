import streamlit as st
import streamlit.components.v1 as components
import paho.mqtt.client as mqtt
import json
import io
import re
import unicodedata
import queue

import speech_recognition as sr
from streamlit_mic_recorder import mic_recorder
from streamlit_autorefresh import st_autorefresh


# =========================================================
# 1. CONFIGURACIÓN
# =========================================================

st.set_page_config(
    page_title="GranjaConecta | Bebedero",
    page_icon="🐔",
    layout="wide"
)

BROKER = "broker.mqttdashboard.com"
PUERTO = 1883
TOPICO = "granjaconecta"


# =========================================================
# 2. ESTILOS
# =========================================================

st.markdown("""
<style>
    .stApp {
        background-color: #EDF5E9;
        color: #17472D;
    }

    [data-testid="stSidebar"] {
        background-color: #DCEBD8;
    }

    h1, h2, h3, h4, p, label {
        color: #17472D !important;
    }

    .bloque-info {
        background: #F8FCF6;
        border: 1px solid #D1E2CD;
        border-radius: 15px;
        padding: 17px;
        text-align: center;
        min-height: 105px;
    }

    .dato-titulo {
        color: #54745B;
        font-size: 13px;
        font-weight: 700;
        margin-bottom: 8px;
    }

    .dato-valor {
        color: #17472D;
        font-size: 25px;
        font-weight: 900;
    }

    .respuesta {
        background: #F8FCF6;
        border-left: 5px solid #477B50;
        border-radius: 10px;
        padding: 15px;
        color: #17472D;
        margin-top: 10px;
    }

    .alerta {
        background: #FFF4D9;
        border-left: 5px solid #D99B28;
        border-radius: 10px;
        padding: 13px;
        color: #704D0D;
        margin: 8px 0;
    }

    .estado-ok {
        color: #26733B;
        font-weight: 800;
    }

    .estado-error {
        color: #B3261E;
        font-weight: 800;
    }

    div[data-testid="stButton"] button {
        background-color: #17472D;
        color: white;
    }
</style>
""", unsafe_allow_html=True)


# =========================================================
# 3. ESTADOS INICIALES
# =========================================================

if "nivel_agua" not in st.session_state:
    st.session_state.nivel_agua = 50.0

if "valvula" not in st.session_state:
    st.session_state.valvula = "desconocida"

if "vaciando" not in st.session_state:
    st.session_state.vaciando = False

if "distancia_agua" not in st.session_state:
    st.session_state.distancia_agua = None

if "lectura_agua_valida" not in st.session_state:
    st.session_state.lectura_agua_valida = True

if "estado_agua" not in st.session_state:
    st.session_state.estado_agua = "SIN DATOS"

if "mqtt_conectado" not in st.session_state:
    st.session_state.mqtt_conectado = False

if "respuesta" not in st.session_state:
    st.session_state.respuesta = (
        "Hola. Puedes darme órdenes por voz para controlar el bebedero."
    )

if "ultima_transcripcion" not in st.session_state:
    st.session_state.ultima_transcripcion = ""

if "ultimo_audio_id" not in st.session_state:
    st.session_state.ultimo_audio_id = None

if "historial" not in st.session_state:
    st.session_state.historial = []


# =========================================================
# 4. NORMALIZAR TEXTO
# =========================================================

def normalizar(texto):
    texto = texto.lower().strip()

    texto = unicodedata.normalize(
        "NFD",
        texto
    )

    texto = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )

    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto


# =========================================================
# 5. CONEXIÓN MQTT
# =========================================================

@st.cache_resource
def iniciar_mqtt():

    mensajes = queue.Queue()

    cliente = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="GRANJACONECTA_BEBEDERO_STREAMLIT"
    )

    def al_conectar(
        client,
        userdata,
        flags,
        reason_code,
        properties
    ):
        conectado = reason_code == 0

        mensajes.put(("conexion", conectado, None))

        if conectado:
            client.subscribe(TOPICO)

    def al_desconectar(
        client,
        userdata,
        disconnect_flags,
        reason_code,
        properties
    ):
        mensajes.put(("conexion", False, None))

    def al_recibir(client, userdata, msg):
        try:
            contenido = msg.payload.decode("utf-8")
            datos = json.loads(contenido)

            mensajes.put(("mensaje", datos, None))

        except Exception as error:
            mensajes.put(("error", str(error), None))

    cliente.on_connect = al_conectar
    cliente.on_disconnect = al_desconectar
    cliente.on_message = al_recibir

    try:
        cliente.connect_async(
            BROKER,
            PUERTO,
            keepalive=60
        )

        cliente.loop_start()

    except Exception as error:
        mensajes.put(("conexion", False, str(error)))

    return cliente, mensajes


cliente_mqtt, cola_mqtt = iniciar_mqtt()


# =========================================================
# 6. LEER MENSAJES MQTT
# =========================================================

while not cola_mqtt.empty():

    tipo, contenido, extra = cola_mqtt.get()

    if tipo == "conexion":

        st.session_state.mqtt_conectado = contenido

    elif tipo == "mensaje":

        datos_mqtt = contenido

        tipo_mensaje = datos_mqtt.get("tipo", "")

        if tipo_mensaje == "telemetria":

            datos = datos_mqtt.get("datos", {})

            nivel = datos.get(
                "nivelAgua",
                datos.get("agua", None)
            )

            if nivel is not None:
                try:
                    st.session_state.nivel_agua = max(
                        0.0,
                        min(100.0, float(nivel))
                    )
                except (TypeError, ValueError):
                    pass

            st.session_state.valvula = datos.get(
                "valvula",
                st.session_state.valvula
            )

            st.session_state.vaciando = datos.get(
                "vaciando",
                st.session_state.vaciando
            )

            st.session_state.distancia_agua = datos.get(
                "distancia",
                st.session_state.distancia_agua
            )

            st.session_state.lectura_agua_valida = datos.get(
                "lecturaAguaValida",
                st.session_state.lectura_agua_valida
            )

            st.session_state.estado_agua = datos.get(
                "estadoAgua",
                st.session_state.estado_agua
            )

        elif tipo_mensaje == "respuesta":

            mensaje_esp = datos_mqtt.get(
                "message",
                "El ESP32 recibió una respuesta."
            )

            st.session_state.historial.append(
                "ESP32: " + str(mensaje_esp)
            )

    elif tipo == "error":

        st.session_state.historial.append(
            "Error MQTT: " + str(contenido)
        )


# =========================================================
# 7. ENVIAR COMANDOS AL ESP32
# =========================================================

def enviar_comando(comando):

    if not st.session_state.mqtt_conectado:
        return False, (
            "No puedo enviar la orden porque no hay conexión MQTT "
            "con el ESP32."
        )

    mensaje = {
        "tipo": "comando",
        "command": comando
    }

    try:
        resultado = cliente_mqtt.publish(
            TOPICO,
            json.dumps(mensaje),
            qos=0
        )

        if resultado.rc == mqtt.MQTT_ERR_SUCCESS:

            return True, "Orden enviada al ESP32: " + comando

        return False, "No se pudo publicar la orden MQTT."

    except Exception as error:

        return False, "Error al enviar la orden: " + str(error)


# =========================================================
# 8. RESPUESTAS A ÓRDENES INFORMATIVAS
# =========================================================

def consultar_nivel():

    nivel = st.session_state.nivel_agua

    if not st.session_state.lectura_agua_valida:
        return (
            "No puedo confirmar el nivel de agua porque "
            "la lectura del sensor no es válida."
        )

    if nivel <= 10:
        return (
            f"El bebedero tiene {nivel:.0f}% de agua. "
            "Está prácticamente vacío. Es necesario rellenarlo."
        )

    if nivel <= 25:
        return (
            f"El bebedero tiene {nivel:.0f}% de agua. "
            "El nivel es bajo. Recomiendo rellenarlo pronto."
        )

    if nivel >= 90:
        return (
            f"El bebedero tiene {nivel:.0f}% de agua. "
            "Está lleno o muy cerca de su capacidad máxima."
        )

    return (
        f"El bebedero tiene {nivel:.0f}% de agua. "
        "El nivel es suficiente por el momento."
    )


def responder_orden_informativa(texto):

    # Informar el nivel o porcentaje de agua
    if any(frase in texto for frase in [
        "indica el nivel de agua",
        "informa el nivel de agua",
        "dime el nivel de agua",
        "muestra el nivel de agua",
        "indica el porcentaje de agua",
        "informa el porcentaje de agua",
        "muestra el porcentaje de agua",
        "lee el nivel de agua"
    ]):
        return consultar_nivel()

    # Informar si hace falta rellenar
    if any(frase in texto for frase in [
        "indica si necesita agua",
        "informa si necesita agua",
        "revisa si necesita agua",
        "indica si debo rellenar",
        "informa si debo rellenar",
        "revisa el nivel del bebedero",
        "indica si hay que rellenar"
    ]):
        nivel = st.session_state.nivel_agua

        if not st.session_state.lectura_agua_valida:
            return (
                "No puedo confirmar si necesita agua porque "
                "la lectura del sensor no es válida."
            )

        if nivel <= 25:
            return (
                f"El bebedero necesita agua. "
                f"Actualmente tiene {nivel:.0f}% de agua."
            )

        return (
            f"El bebedero tiene suficiente agua. "
            f"Actualmente tiene {nivel:.0f}%."
        )

    # Informar el estado de la válvula
    if any(frase in texto for frase in [
        "indica el estado de la valvula",
        "informa el estado de la valvula",
        "muestra el estado de la valvula",
        "revisa la valvula",
        "lee el estado de la valvula"
    ]):
        return (
            "El estado actual de la válvula es "
            + str(st.session_state.valvula)
            + "."
        )

    # Informar el estado general del bebedero
    if any(frase in texto for frase in [
        "informa el estado del bebedero",
        "indica el estado del bebedero",
        "revisa el bebedero",
        "muestra el estado del bebedero",
        "lee el estado del bebedero"
    ]):
        nivel = st.session_state.nivel_agua
        return (
            f"El bebedero tiene {nivel:.0f}% de agua. "
            f"La válvula está {st.session_state.valvula}."
        )

    return None


# =========================================================
# 9. INTERPRETAR ÓRDENES DE VOZ
# =========================================================

def procesar_orden_voz(frase):

    texto = normalizar(frase)

    # Primero reconocer las órdenes informativas
    respuesta_informativa = responder_orden_informativa(texto)

    if respuesta_informativa:
        respuesta = respuesta_informativa

    # Abrir válvula
    elif any(palabra in texto for palabra in [
        "abre la valvula",
        "abrir la valvula",
        "abre valvula",
        "abrir valvula",
        "abre el paso del agua",
        "deja pasar el agua"
    ]):
        ok, respuesta = enviar_comando("VALVULA_ABRIR")

    # Cerrar válvula
    elif any(palabra in texto for palabra in [
        "cierra la valvula",
        "cerrar la valvula",
        "cierra valvula",
        "cerrar valvula",
        "deten el agua",
        "detener el agua",
        "para el agua"
    ]):
        ok, respuesta = enviar_comando("VALVULA_CERRAR")

    # Vaciar bebedero
    elif any(palabra in texto for palabra in [
        "vacia el bebedero",
        "vaciar el bebedero",
        "vacia bebedero",
        "vacia el agua",
        "saca el agua"
    ]):
        ok, respuesta = enviar_comando("BEBEDERO_VACIAR")

    # Llenar bebedero
    elif any(palabra in texto for palabra in [
        "llena el bebedero",
        "llenar el bebedero",
        "rellena el bebedero",
        "rellenar el bebedero",
        "dejalo lleno",
        "dejala llena",
        "llena el agua",
        "llena bebedero"
    ]):
        ok, respuesta = enviar_comando("BEBEDERO_LLENO")

    else:
        respuesta = (
            "No he reconocido la orden. Puedes decir: "
            "indica el nivel de agua, informa el estado del bebedero, "
            "indica si necesita agua, abre la válvula, "
            "cierra la válvula, llena el bebedero o vacía el bebedero."
        )

    st.session_state.respuesta = respuesta

    st.session_state.historial.append(
        "Tú: " + frase
    )

    st.session_state.historial.append(
        "GranjaConecta: " + respuesta
    )


# =========================================================
# 10. ENCABEZADO
# =========================================================

st.title("🐔 GranjaConecta")
st.subheader("Control inteligente del bebedero")

st.markdown(
    "Controla el suministro de agua de tu granja mediante "
    "órdenes de voz para conocer el estado y controlar el bebedero."
)


# =========================================================
# 11. ESTADO DE CONEXIÓN
# =========================================================

if st.session_state.mqtt_conectado:

    st.markdown(
        '<p class="estado-ok">🟢 Conectado al ESP32 mediante MQTT</p>',
        unsafe_allow_html=True
    )

else:

    st.markdown(
        '<p class="estado-error">🔴 Esperando conexión con el ESP32...</p>',
        unsafe_allow_html=True
    )


# =========================================================
# 12. BEBEDERO GRÁFICO
# =========================================================

nivel_agua = st.session_state.nivel_agua

components.html(f"""
<div style="
    display:flex;
    align-items:center;
    justify-content:center;
    gap:18px;
    padding:15px;
    background:#EAF3E7;
    border-radius:18px;
    font-family:Arial,sans-serif;
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
            background:repeating-linear-gradient(
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
            height:{nivel_agua:.1f}%;
            background:#42A5D5;
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
            {nivel_agua:.0f}%
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
""", height=285)


# =========================================================
# 13. INFORMACIÓN DEL BEBEDERO
# =========================================================

st.markdown("### 📊 Información del bebedero")

col1, col2, col3 = st.columns(3)

with col1:

    st.markdown(f"""
    <div class="bloque-info">
        <div class="dato-titulo">NIVEL DE AGUA</div>
        <div class="dato-valor">{nivel_agua:.0f}%</div>
    </div>
    """, unsafe_allow_html=True)

with col2:

    estado_valvula = str(
        st.session_state.valvula
    ).upper()

    st.markdown(f"""
    <div class="bloque-info">
        <div class="dato-titulo">ESTADO DE LA VÁLVULA</div>
        <div class="dato-valor" style="font-size:20px;">
            {estado_valvula}
        </div>
    </div>
    """, unsafe_allow_html=True)

with col3:

    estado_vaciado = (
        "VACIANDO"
        if st.session_state.vaciando
        else "INACTIVO"
    )

    st.markdown(f"""
    <div class="bloque-info">
        <div class="dato-titulo">PROCESO DE VACIADO</div>
        <div class="dato-valor" style="font-size:20px;">
            {estado_vaciado}
        </div>
    </div>
    """, unsafe_allow_html=True)


# =========================================================
# 14. CONTROL POR VOZ
# =========================================================

st.markdown("---")
st.markdown("### 🎙️ Control por voz")

st.write(
    "Pulsa el micrófono y utiliza órdenes de voz para "
    "consultar el estado y controlar el bebedero."
)

audio_voz = mic_recorder(
    start_prompt="🎙️ Hablar",
    stop_prompt="⏹️ Terminar grabación",
    just_once=True,
    use_container_width=True,
    key="microfono_bebedero",
    format="wav"
)

if audio_voz and audio_voz.get("bytes"):

    audio_id = audio_voz.get("id")

    if audio_id != st.session_state.ultimo_audio_id:

        st.session_state.ultimo_audio_id = audio_id

        try:

            reconocedor = sr.Recognizer()

            archivo_audio = io.BytesIO(
                audio_voz["bytes"]
            )

            with sr.AudioFile(archivo_audio) as fuente:

                audio = reconocedor.record(fuente)

            transcripcion = reconocedor.recognize_google(
                audio,
                language="es-CO"
            )

            st.session_state.ultima_transcripcion = transcripcion

            procesar_orden_voz(transcripcion)

        except sr.UnknownValueError:

            st.session_state.respuesta = (
                "No pude entender lo que dijiste. "
                "Intenta hablar un poco más claro."
            )

        except sr.RequestError:

            st.session_state.respuesta = (
                "No fue posible conectar con el servicio "
                "de reconocimiento de voz. Revisa tu conexión."
            )

        except Exception as error:

            st.session_state.respuesta = (
                "Ocurrió un problema al procesar el audio: "
                + str(error)
            )


# =========================================================
# 15. RESPUESTA ESCRITA
# =========================================================

st.markdown("### 💬 Respuesta de GranjaConecta")

if st.session_state.ultima_transcripcion:

    st.markdown(
        f"""
        <div class="respuesta">
            <b>Tu orden:</b><br>
            {st.session_state.ultima_transcripcion}
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown(
    f"""
    <div class="respuesta">
        <b>GranjaConecta:</b><br>
        {st.session_state.respuesta}
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# 16. ALERTAS
# =========================================================

st.markdown("---")
st.markdown("### 🔔 Alertas del bebedero")

nivel = st.session_state.nivel_agua

if not st.session_state.mqtt_conectado:

    st.markdown("""
    <div class="alerta">
        🔴 No hay conexión con el ESP32. No se pueden confirmar
        las órdenes ni actualizar los datos del bebedero.
    </div>
    """, unsafe_allow_html=True)

if not st.session_state.lectura_agua_valida:

    st.markdown("""
    <div class="alerta">
        ⚠️ La lectura del nivel de agua no es válida.
        Revisa el sensor y sus conexiones.
    </div>
    """, unsafe_allow_html=True)

elif nivel <= 10:

    st.markdown("""
    <div class="alerta">
        🚨 El bebedero está prácticamente vacío.
        Es necesario rellenarlo.
    </div>
    """, unsafe_allow_html=True)

elif nivel <= 25:

    st.markdown("""
    <div class="alerta">
        ⚠️ Nivel de agua bajo. Se recomienda rellenar el bebedero.
    </div>
    """, unsafe_allow_html=True)

elif nivel >= 90:

    st.success("💧 El bebedero está lleno o cerca de su capacidad máxima.")

else:

    st.success("✅ El nivel de agua se encuentra dentro de un rango adecuado.")


# =========================================================
# 17. HISTORIAL
# =========================================================

st.markdown("---")
st.markdown("### 📝 Historial de interacción")

if st.session_state.historial:

    for registro in reversed(st.session_state.historial[-12:]):

        st.write("• " + registro)

else:

    st.caption("Todavía no hay órdenes registradas.")


# =========================================================
# 18. ACTUALIZACIÓN AUTOMÁTICA
# =========================================================

st_autorefresh(
    interval=2000,
    key="actualizacion_bebedero"
)
