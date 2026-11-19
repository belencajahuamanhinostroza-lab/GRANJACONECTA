
import streamlit as st
import streamlit.components.v1 as components
import unicodedata
import re
import hashlib

# =========================================================
# 1. CONFIGURACIÓN
# =========================================================

st.set_page_config(
    page_title="GranjaConecta | Bebedero",
    page_icon="🐔",
    layout="wide"
)

# Micrófono opcional
try:
    from streamlit_mic_recorder import mic_recorder
    import speech_recognition as sr
    MICROFONO_DISPONIBLE = True
except ImportError:
    MICROFONO_DISPONIBLE = False


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

    .titulo-principal {
        color: #17472D;
        font-size: 34px;
        font-weight: 800;
        margin-bottom: 5px;
    }

    .subtitulo {
        color: #52735A;
        font-size: 15px;
        margin-bottom: 20px;
    }

    .tarjeta {
        background: #FFFFFF;
        border: 1px solid #C9DDC5;
        border-radius: 15px;
        padding: 18px;
        min-height: 115px;
        box-shadow: 0 2px 8px rgba(23,71,45,0.06);
    }

    .tarjeta-titulo {
        color: #52735A;
        font-size: 13px;
        font-weight: 700;
        margin-bottom: 8px;
    }

    .tarjeta-valor {
        color: #17472D;
        font-size: 25px;
        font-weight: 800;
    }

    .tarjeta-detalle {
        color: #66816A;
        font-size: 12px;
        margin-top: 5px;
    }

    div.stButton > button {
        background-color: #17472D;
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 700;
        min-height: 43px;
        width: 100%;
    }

    div.stButton > button:hover {
        background-color: #286341;
        color: white;
        border: 1px solid #286341;
    }

    div.stButton > button:focus {
        color: white;
        border-color: #17472D;
    }

    div[data-testid="stFormSubmitButton"] button {
        background-color: #17472D;
        color: white;
        border-radius: 10px;
        font-weight: bold;
    }

    div[data-testid="stFormSubmitButton"] button:hover {
        background-color: #286341;
        color: white;
    }

    div[data-testid="stMetric"] {
        background: white;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #C9DDC5;
    }

    div[data-testid="stMetric"] label {
        color: #52735A !important;
    }

    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #17472D !important;
    }

    hr {
        border-color: #C9DDC5;
    }

    .aviso {
        background: #FFFFFF;
        border-left: 5px solid #238A80;
        padding: 13px;
        border-radius: 8px;
        color: #17472D;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


# =========================================================
# 3. ESTADO DE LA SIMULACIÓN
# =========================================================

if "nivel_agua" not in st.session_state:
    st.session_state.nivel_agua = 50.0

if "valvula_abierta" not in st.session_state:
    st.session_state.valvula_abierta = False

if "vaciando" not in st.session_state:
    st.session_state.vaciando = False

if "historial" not in st.session_state:
    st.session_state.historial = []

if "respuesta" not in st.session_state:
    st.session_state.respuesta = (
        "¡Hola! Puedes darme una orden para controlar el bebedero."
    )

if "distancia_control" not in st.session_state:
    st.session_state.distancia_control = 30 - (
        st.session_state.nivel_agua / 90 * 20
    )


# =========================================================
# 4. FUNCIONES DEL BEBEDERO
# =========================================================

def calcular_distancia(nivel):
    """
    Simulación:
    0 % de agua  = 30 cm
    90 % de agua = 10 cm
    """
    distancia = 30 - (nivel / 90) * 20
    return round(distancia, 1)


def calcular_nivel(distancia):
    distancia = max(10, min(30, float(distancia)))
    nivel = ((30 - distancia) / 20) * 90
    return max(0, min(90, nivel))


def obtener_estado(distancia):
    if distancia < 10:
        return "Posible desbordamiento", "🔴"

    if distancia <= 10:
        return "Lleno", "🟢"

    if distancia >= 30:
        return "Vacío", "🔴"

    if distancia > 25:
        return "Nivel bajo", "🟠"

    return "Nivel normal", "🟢"


def obtener_altura(nivel):
    return max(0, min(100, (nivel / 90) * 100))


def abrir_valvula():
    st.session_state.valvula_abierta = True
    st.session_state.vaciando = False

    if st.session_state.nivel_agua >= 90:
        st.session_state.valvula_abierta = False
        st.session_state.respuesta = (
            "El bebedero ya está lleno. La válvula permanece cerrada."
        )
        return

    st.session_state.nivel_agua = min(
        90,
        st.session_state.nivel_agua + 10
    )

    if st.session_state.nivel_agua >= 90:
        st.session_state.valvula_abierta = False
        st.session_state.respuesta = (
            "El bebedero llegó al nivel máximo. "
            "La válvula se cerró automáticamente en la simulación."
        )
    else:
        st.session_state.respuesta = (
            "Válvula abierta. El nivel de agua aumentó en la simulación."
        )

    actualizar_control()


def cerrar_valvula():
    st.session_state.valvula_abierta = False
    st.session_state.vaciando = False
    st.session_state.respuesta = (
        "Válvula cerrada. El nivel de agua se mantiene."
    )


def llenar_bebedero():
    st.session_state.vaciando = False
    st.session_state.nivel_agua = 90
    st.session_state.valvula_abierta = False
    st.session_state.respuesta = (
        "Bebedero lleno. La válvula se cerró automáticamente."
    )
    actualizar_control()


def vaciar_bebedero():
    st.session_state.valvula_abierta = False
    st.session_state.vaciando = True
    st.session_state.nivel_agua = 0
    st.session_state.vaciando = False
    st.session_state.respuesta = (
        "El bebedero se ha vaciado en la simulación."
    )
    actualizar_control()


def actualizar_control():
    st.session_state.distancia_control = calcular_distancia(
        st.session_state.nivel_agua
    )


# =========================================================
# 5. INTERPRETACIÓN DE COMANDOS
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

    texto = re.sub(r"[¿?¡!.,;:]", "", texto)

    return texto


def procesar_mensaje(mensaje):
    texto = normalizar(mensaje)

    if not texto:
        return "Escribe una orden para controlar el bebedero."

    # CERRAR VÁLVULA
    if any(x in texto for x in [
        "cerrar valvula",
        "cierra valvula",
        "apaga valvula",
        "detener llenado",
        "detener el agua",
        "para el agua"
    ]):
        cerrar_valvula()
        return st.session_state.respuesta

    # VACIAR
    if any(x in texto for x in [
        "vaciar",
        "vacia el bebedero",
        "drenar",
        "sacar el agua"
    ]):
        vaciar_bebedero()
        return st.session_state.respuesta

    # LLENAR COMPLETAMENTE
    if any(x in texto for x in [
        "llenar completamente",
        "llena completamente",
        "llenar el bebedero",
        "llena el bebedero",
        "llenar",
        "llenalo"
    ]):
        llenar_bebedero()
        return st.session_state.respuesta

    # ABRIR VÁLVULA
    if any(x in texto for x in [
        "abrir valvula",
        "abre valvula",
        "activar valvula",
        "iniciar llenado",
        "dejar pasar agua"
    ]):
        abrir_valvula()
        return st.session_state.respuesta

    # CONSULTAS
    distancia = calcular_distancia(
        st.session_state.nivel_agua
    )

    estado, emoji = obtener_estado(distancia)

    if any(x in texto for x in [
        "distancia",
        "centimetros",
        "cuantos cm"
    ]):
        return (
            f"La distancia actual es de {distancia} centímetros."
        )

    if any(x in texto for x in [
        "estado",
        "nivel",
        "como esta",
        "como se encuentra"
    ]):
        return (
            f"El bebedero está en estado: {estado}. "
            f"La distancia es de {distancia} centímetros."
        )

    if any(x in texto for x in [
        "valvula",
        "esta abierta",
        "esta cerrada"
    ]):
        estado_valvula = (
            "abierta"
            if st.session_state.valvula_abierta
            else "cerrada"
        )

        return f"La válvula está {estado_valvula}."

    if any(x in texto for x in [
        "hola",
        "buenos dias",
        "buenas tardes",
        "buenas noches"
    ]):
        return (
            "¡Hola! Soy GranjaConecta. "
            "Puedo ayudarte a controlar y consultar el bebedero."
        )

    return (
        "No reconocí esa solicitud. Puedes pedirme abrir la válvula, "
        "cerrarla, llenar o vaciar el bebedero, o consultar su estado."
    )


# =========================================================
# 6. ENCABEZADO
# =========================================================

st.markdown(
    '<div class="titulo-principal">🐔 GranjaConecta</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitulo">'
    'Control y monitoreo inteligente del bebedero'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="aviso">'
    '🧪 <b>Modo de prueba:</b> la interfaz está funcionando '
    'con datos simulados. Todavía no está conectada al ESP32.'
    '</div>',
    unsafe_allow_html=True
)

st.divider()


# =========================================================
# 7. DATOS ACTUALES
# =========================================================

nivel = st.session_state.nivel_agua
distancia = calcular_distancia(nivel)
estado, emoji = obtener_estado(distancia)

valvula = (
    "Abierta"
    if st.session_state.valvula_abierta
    else "Cerrada"
)

altura = obtener_altura(nivel)


# =========================================================
# 8. DISTRIBUCIÓN PRINCIPAL
# =========================================================

columna_dibujo, columna_datos = st.columns(
    [1.1, 1],
    gap="large"
)

with columna_dibujo:

    st.markdown("### 🐔 Visualización del bebedero")

    dibujo = f"""
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
            padding: 0;
            background: transparent;
            font-family: Arial, sans-serif;
        }}

        .zona {{
            width: 100%;
            height: 330px;
            display: flex;
            justify-content: center;
            align-items: center;
        }}

        .bebedero {{
            width: 210px;
            height: 270px;
            position: relative;
            overflow: hidden;
            border: 5px solid #17472D;
            border-radius: 18px 18px 35px 35px;
            background: #F8FFF6;
            box-shadow: 0 5px 12px rgba(23,71,45,0.12);
        }}

        .borde {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 10px;
            background: #17472D;
            z-index: 4;
        }}

        .agua {{
            position: absolute;
            bottom: 0;
            left: 0;
            width: 100%;
            height: {altura:.1f}%;
            background: linear-gradient(
                to top,
                #168477,
                #43BFA8,
                #8AE0C9
            );
            transition: height 0.8s ease;
            z-index: 1;
        }}

        .superficie {{
            position: absolute;
            top: -7px;
            left: 0;
            width: 100%;
            height: 13px;
            background: rgba(255,255,255,0.35);
            border-radius: 50%;
        }}

        .etiqueta {{
            position: absolute;
            top: 20px;
            width: 100%;
            text-align: center;
            color: #17472D;
            font-size: 15px;
            font-weight: bold;
            z-index: 5;
        }}

        .nivel {{
            position: absolute;
            bottom: 15px;
            width: 100%;
            text-align: center;
            color: #FFFFFF;
            font-size: 15px;
            font-weight: bold;
            text-shadow: 0 1px 3px #17472D;
            z-index: 5;
        }}

        .base {{
            position: absolute;
            bottom: -5px;
            left: -12px;
            width: calc(100% + 24px);
            height: 9px;
            background: #17472D;
            z-index: 6;
        }}
    </style>
    </head>

    <body>
        <div class="zona">
            <div class="bebedero">

                <div class="borde"></div>

                <div class="etiqueta">
                    AGUA
                </div>

                <div class="agua">
                    <div class="superficie"></div>
                </div>

                <div class="nivel">
                    {distancia:.1f} cm
                </div>

                <div class="base"></div>

            </div>
        </div>
    </body>
    </html>
    """

    components.html(
        dibujo,
        height=335,
        scrolling=False
    )

    st.caption(
        "Representación visual del nivel de agua. "
        "La distancia se mide desde el sensor simulado "
        "hasta la superficie del agua."
    )


with columna_datos:

    st.markdown("### 📊 Estado del bebedero")

    st.metric(
        label="Distancia hasta el agua",
        value=f"{distancia:.1f} cm",
        help="Medición simulada desde el sensor hasta el agua."
    )

    st.metric(
        label="Estado del agua",
        value=f"{emoji} {estado}"
    )

    st.metric(
        label="Estado de la válvula",
        value=valvula
    )

    if st.session_state.valvula_abierta:
        st.success("💧 La válvula está abierta.")
    else:
        st.info("🔒 La válvula está cerrada.")

    if estado == "Vacío":
        st.error("El bebedero está vacío. Se recomienda llenarlo.")
    elif estado == "Nivel bajo":
        st.warning("El nivel de agua está bajo.")
    elif estado == "Lleno":
        st.success("El bebedero alcanzó el nivel máximo.")
    elif estado == "Posible desbordamiento":
        st.error("¡Atención! Posible desbordamiento.")
    else:
        st.success("El nivel de agua es normal.")


st.divider()


# =========================================================
# 9. CONTROLES DE PRUEBA
# =========================================================

st.markdown("### 🎛️ Control del bebedero")

st.write(
    "Prueba los botones para comprobar cómo cambia "
    "el nivel de agua en el dibujo."
)

boton1, boton2, boton3, boton4 = st.columns(4)

with boton1:
    st.button(
        "💧 Abrir válvula",
        key="btn_abrir",
        on_click=abrir_valvula
    )

with boton2:
    st.button(
        "🔒 Cerrar válvula",
        key="btn_cerrar",
        on_click=cerrar_valvula
    )

with boton3:
    st.button(
        "⬆️ Llenar",
        key="btn_llenar",
        on_click=llenar_bebedero
    )

with boton4:
    st.button(
        "⬇️ Vaciar",
        key="btn_vaciar",
        on_click=vaciar_bebedero
    )


st.markdown("#### Ajustar distancia manualmente")

st.caption(
    "Mueve el control para simular una lectura del sensor. "
    "10 cm representa el nivel máximo y 30 cm representa el bebedero vacío."
)

distancia_nueva = st.slider(
    "Distancia simulada del sensor (cm)",
    min_value=10.0,
    max_value=30.0,
    step=0.5,
    key="distancia_control"
)

if distancia_nueva != calcular_distancia(
    st.session_state.nivel_agua
):
    st.session_state.nivel_agua = calcular_nivel(
        distancia_nueva
    )

    st.session_state.valvula_abierta = False
    st.session_state.vaciando = False

    st.rerun()


st.divider()


# =========================================================
# 10. ASISTENTE DE TEXTO
# =========================================================

st.markdown("### 💬 Interactúa con GranjaConecta")

st.write(
    "Escribe una orden o pregunta sobre el bebedero."
)

with st.form("formulario_mensaje", clear_on_submit=True):

    mensaje = st.text_input(
        "Tu mensaje",
        placeholder="Ejemplo: abre la válvula"
    )

    enviar = st.form_submit_button(
        "Enviar mensaje",
        use_container_width=True
    )

if enviar and mensaje.strip():

    respuesta = procesar_mensaje(mensaje)

    st.session_state.historial.append({
        "usuario": mensaje,
        "asistente": respuesta
    })

    st.session_state.respuesta = respuesta

    st.rerun()


# =========================================================
# 11. MICRÓFONO OPCIONAL
# =========================================================

if MICROFONO_DISPONIBLE:

    st.markdown("#### 🎙️ Dar una orden por voz")

    audio = mic_recorder(
        start_prompt="🎙️ Hablar",
        stop_prompt="⏹️ Detener",
        just_once=True,
        key="microfono_bebedero"
    )

    if audio and audio.get("bytes"):

        huella = hashlib.md5(
            audio["bytes"]
        ).hexdigest()

        if st.session_state.get("ultimo_audio") != huella:

            st.session_state.ultimo_audio = huella

            try:
                import io

                reconocedor = sr.Recognizer()

                with sr.AudioFile(
                    io.BytesIO(audio["bytes"])
                ) as fuente:

                    audio_grabado = reconocedor.record(
                        fuente
                    )

                texto_voz = reconocedor.recognize_google(
                    audio_grabado,
                    language="es-CO"
                )

                respuesta = procesar_mensaje(texto_voz)

                st.session_state.historial.append({
                    "usuario": texto_voz,
                    "asistente": respuesta
                })

                st.session_state.respuesta = respuesta

                st.rerun()

            except sr.UnknownValueError:
                st.warning(
                    "No pude entender el audio. "
                    "Intenta hablar un poco más claro."
                )

            except sr.RequestError:
                st.error(
                    "No se pudo realizar el reconocimiento de voz. "
                    "Comprueba tu conexión a internet."
                )

            except Exception as error:
                st.error(
                    f"No se pudo procesar el audio: {error}"
                )

else:

    st.info(
        "El micrófono no está habilitado en este entorno. "
        "Puedes probar todas las funciones con texto y botones."
    )


# =========================================================
# 12. RESPUESTA DEL ASISTENTE
# =========================================================

st.markdown("#### 🤖 Respuesta de GranjaConecta")

st.markdown(
    f"""
    <div class="tarjeta">
        <div style="
            color:#17472D;
            font-size:15px;
            line-height:1.6;
        ">
            {st.session_state.respuesta}
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# 13. HISTORIAL
# =========================================================

st.markdown("### 📝 Historial de conversación")

if st.session_state.historial:

    for elemento in reversed(
        st.session_state.historial
    ):

        st.markdown(
            f"**👤 Tú:** {elemento['usuario']}"
        )

        st.markdown(
            f"**🐔 GranjaConecta:** {elemento['asistente']}"
        )

        st.divider()

else:

    st.caption(
        "Todavía no hay mensajes. Prueba escribiendo una orden."
    )


if st.button(
    "🗑️ Limpiar conversación",
    key="limpiar_historial"
):
    st.session_state.historial = []
    st.session_state.respuesta = (
        "Conversación limpiada. ¿En qué puedo ayudarte?"
    )
    st.rerun()


# =========================================================
# 14. INFORMACIÓN DE PRUEBA
# =========================================================

with st.expander("ℹ️ Información sobre esta simulación"):

    st.write("""
    **Cómo funciona la demostración:**

    - 30 cm: bebedero vacío.
    - Más de 25 cm: nivel bajo.
    - Más de 10 cm y hasta 25 cm: nivel normal.
    - 10 cm: bebedero lleno.
    - Menos de 10 cm: posible desbordamiento.

    La altura del agua en el dibujo se calcula a partir
    de la distancia simulada.

    Los botones modifican los datos locales de Streamlit.
    Todavía no envían órdenes a ningún dispositivo físico.
    """)
