
import base64
from pathlib import Path

import streamlit as st


# --------------------------------------------------
# CONFIGURACIÓN GENERAL
# --------------------------------------------------

st.set_page_config(
    page_title="GranjaConecta",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

CARPETA = Path(__file__).resolve().parent
RUTA_IMAGEN = CARPETA / "fondogranja.jpg"


# --------------------------------------------------
# CARGAR IMAGEN DE PORTADA
# --------------------------------------------------

def cargar_imagen(ruta):
    if not ruta.exists():
        return None

    extension = ruta.suffix.lower()

    if extension == ".png":
        tipo = "image/png"
    elif extension in [".jpg", ".jpeg"]:
        tipo = "image/jpeg"
    else:
        return None

    with open(ruta, "rb") as archivo:
        imagen_base64 = base64.b64encode(
            archivo.read()
        ).decode("utf-8")

    return f"data:{tipo};base64,{imagen_base64}"


imagen_portada = cargar_imagen(RUTA_IMAGEN)


# --------------------------------------------------
# ESTILOS CSS
# --------------------------------------------------

st.markdown(
    """
    <style>

    /* Fondo general */

    .stApp {
        background-color: #f4faf5;
        color: #183d2b;
    }

    [data-testid="stHeader"] {
        background-color: transparent;
    }

    /* Espaciado principal */

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1250px;
    }

    /* Barra lateral */

    [data-testid="stSidebar"] {
        background: linear-gradient(
            180deg,
            #123d2b 0%,
            #1c5638 100%
        );
    }

    [data-testid="stSidebar"] * {
        color: white;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: white;
    }

    /* Banner principal */

    .hero {
        width: 100%;
        min-height: 390px;
        border-radius: 22px;
        overflow: hidden;
        position: relative;
        display: flex;
        align-items: center;
        background-color: #1b5638;
        background-size: cover;
        background-position: center;
        margin-bottom: 35px;
    }

    .hero-overlay {
        position: absolute;
        inset: 0;
        background: linear-gradient(
            90deg,
            rgba(8, 39, 25, 0.88) 0%,
            rgba(12, 54, 33, 0.65) 55%,
            rgba(12, 54, 33, 0.10) 100%
        );
    }

    .hero-content {
        position: relative;
        z-index: 2;
        padding: 55px;
        max-width: 700px;
    }

    .hero-label {
        color: #c6f36a;
        font-size: 13px;
        font-weight: 800;
        letter-spacing: 3px;
        margin-bottom: 18px;
    }

    .hero-title {
        color: white;
        font-size: clamp(38px, 6vw, 65px);
        font-weight: 800;
        line-height: 1.05;
        margin: 0 0 20px 0;
    }

    .hero-description {
        color: #f1f8f1;
        font-size: 17px;
        line-height: 1.7;
        max-width: 570px;
    }

    .hero-line {
        width: 85px;
        height: 5px;
        background-color: #c6f36a;
        border-radius: 10px;
        margin-top: 25px;
    }

    /* Títulos de sección */

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

    /* Tarjetas */

    .card-box {
        background: linear-gradient(
            145deg,
            #174a32 0%,
            #246642 100%
        );
        border-radius: 20px;
        padding: 28px;
        min-height: 225px;
        border: 1px solid rgba(255,255,255,0.12);
        box-shadow: 0 8px 22px rgba(20, 65, 42, 0.10);
    }

    .card-icon {
        font-size: 38px;
        margin-bottom: 14px;
    }

    .card-title {
        color: white;
        font-size: 24px;
        font-weight: 800;
        margin-bottom: 12px;
    }

    .card-description {
        color: #e1f0e4;
        font-size: 14px;
        line-height: 1.6;
        min-height: 65px;
    }

    /* Botones */

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

    /* Separador */

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

    /* Adaptación a pantallas pequeñas */

    @media (max-width: 700px) {
        .hero {
            min-height: 360px;
        }

        .hero-content {
            padding: 28px;
        }

        .hero-description {
            font-size: 15px;
        }

        .card-box {
            padding: 22px;
        }
    }

    </style>
    """,
    unsafe_allow_html=True
)


# --------------------------------------------------
# MENÚ LATERAL
# --------------------------------------------------

with st.sidebar:

    st.markdown(
        """
        <div style="text-align:center; padding:20px 5px 25px 5px;">
            <div style="font-size:42px;">🌱</div>
            <div style="
                font-size:23px;
                font-weight:800;
                color:white;
            ">
                GranjaConecta
            </div>
            <div style="
                font-size:11px;
                letter-spacing:2px;
                color:#c6f36a;
                margin-top:5px;
            ">
                TECNOLOGÍA PARA EL CAMPO
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    st.markdown("### Navegación")

    st.page_link(
        "Inicioapp.py",
        label="🏠 Inicio",
        icon=None
    )

    st.page_link(
        "pages/1_Bebedero.py",
        label="💧 Bebedero",
        icon=None
    )

    st.page_link(
        "pages/2_Corral.py",
        label="🐄 Corral",
        icon=None
    )

    st.markdown("---")

    st.caption("Sistema inteligente para el cuidado animal")


# --------------------------------------------------
# PORTADA PRINCIPAL
# --------------------------------------------------

if imagen_portada:

    html_portada = f"""
    <div class="hero"
         style="background-image: url('{imagen_portada}');">

        <div class="hero-overlay"></div>

        <div class="hero-content">

            <div class="hero-label">
                TECNOLOGÍA PARA EL CAMPO
            </div>

            <h1 class="hero-title">
                GranjaConecta
            </h1>

            <div class="hero-description">
                Conectamos la tecnología con el bienestar animal.
                Una granja inteligente donde el monitoreo y la
                automatización facilitan el cuidado diario.
            </div>

            <div class="hero-line"></div>

        </div>
    </div>
    """

    st.markdown(
        html_portada,
        unsafe_allow_html=True
    )

else:

    st.warning(
        "No se encontró fondogranja.jpg. "
        "Verifica que la imagen esté en la carpeta principal "
        "del proyecto."
    )

    st.markdown(
        """
        <div style="
            background:linear-gradient(135deg,#174a32,#246642);
            padding:55px 35px;
            border-radius:22px;
            margin-bottom:35px;
        ">
            <div style="
                color:#c6f36a;
                font-size:13px;
                font-weight:800;
                letter-spacing:3px;
            ">
                TECNOLOGÍA PARA EL CAMPO
            </div>

            <h1 style="
                color:white;
                font-size:55px;
                margin:15px 0;
            ">
                GranjaConecta
            </h1>

            <p style="
                color:white;
                font-size:17px;
            ">
                Conectamos la tecnología con el bienestar animal.
                Una granja inteligente donde el monitoreo y la
                automatización facilitan el cuidado diario.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


# --------------------------------------------------
# PRESENTACIÓN
# --------------------------------------------------

st.markdown(
    """
    <div class="section-title">
        Bienvenido a GranjaConecta
    </div>

    <div class="section-description">
        Una solución tecnológica diseñada para facilitar
        el monitoreo y la automatización de las actividades
        de una granja, conectando sensores, dispositivos
        y herramientas digitales en un solo lugar.
    </div>
    """,
    unsafe_allow_html=True
)


# --------------------------------------------------
# TARJETAS DE NAVEGACIÓN
# --------------------------------------------------

col1, col2 = st.columns(2, gap="large")


with col1:

    st.markdown(
        """
        <div class="card-box">

            <div class="card-icon">🐄</div>

            <div class="card-title">
                Corral inteligente
            </div>

            <div class="card-description">
                Controla el acceso del corral, reconoce gestos
                y regula la ventilación para favorecer el
                bienestar de los animales.
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button(
        "Ingresar al Corral →",
        key="boton_corral",
        use_container_width=True
    ):
        st.switch_page("pages/2_Corral.py")


with col2:

    st.markdown(
        """
        <div class="card-box">

            <div class="card-icon">💧</div>

            <div class="card-title">
                Bebedero inteligente
            </div>

            <div class="card-description">
                Supervisa el nivel de agua y las condiciones
                ambientales, y controla el suministro mediante
                comandos de voz o texto.
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button(
        "Ingresar al Bebedero →",
        key="boton_bebedero",
        use_container_width=True
    ):
        st.switch_page("pages/1_Bebedero.py")


# --------------------------------------------------
# PIE DE PÁGINA
# --------------------------------------------------

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
