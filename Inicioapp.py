
import streamlit as st
from pathlib import Path
import base64

# =====================================================
# CONFIGURACIÓN GENERAL
# =====================================================

st.set_page_config(
    page_title="GranjaConecta",
    page_icon="🐄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# La imagen está en la raíz del repositorio,
# al mismo nivel que Inicioapp.py.
BASE_DIR = Path(__file__).resolve().parent
IMAGE_PATH = BASE_DIR / "fondogranja.jpg"


# =====================================================
# CARGAR IMAGEN DE FONDO
# =====================================================

def cargar_fondo(ruta):
    """Convierte la imagen local a Base64 para usarla en CSS."""
    if not ruta.is_file():
        return None

    with ruta.open("rb") as archivo:
        imagen_base64 = base64.b64encode(
            archivo.read()
        ).decode("utf-8")

    extension = ruta.suffix.lower()
    mime_type = (
        "image/png"
        if extension == ".png"
        else "image/jpeg"
    )

    return f"data:{mime_type};base64,{imagen_base64}"


fondo = cargar_fondo(IMAGE_PATH)


# =====================================================
# ESTILOS DE LA APLICACIÓN
# =====================================================

st.markdown(
    """
    <style>

    @import url(
        'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Playfair+Display:wght@600;700&display=swap'
    );

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    .stApp {
        background: #EAF7EF;
        color: #173F2B;
    }

    .block-container {
        max-width: 1350px;
        padding: 1.2rem 2rem 2.5rem 2rem;
    }

    /* PORTADA PRINCIPAL */

    .hero {
        min-height: 760px;
        width: 100%;
        box-sizing: border-box;
        border-radius: 22px;
        overflow: hidden;
        padding: 62px 24px 40px 24px;
        text-align: center;
        background-color: #CFF0DF;
        background-size: cover;
        background-position: center 42%;
        background-repeat: no-repeat;
        display: flex;
        justify-content: flex-start;
        align-items: flex-start;
    }

    .hero-content {
        width: 100%;
        max-width: 850px;
        margin: 0 auto;
    }

    .brand-small {
        color: #24563A;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 3px;
        text-transform: uppercase;
        margin-bottom: 28px;
    }

    .hero h1 {
        font-family: 'Playfair Display', serif;
        color: #104331;
        font-size: clamp(42px, 6vw, 76px);
        font-weight: 700;
        line-height: 1.08;
        margin: 0 0 18px 0;
    }

    .hero-description {
        color: #24563F;
        font-size: 16px;
        font-weight: 600;
        line-height: 1.8;
        max-width: 690px;
        margin: 0 auto;
    }

    .hero-tag {
        display: inline-block;
        margin-top: 24px;
        padding: 9px 17px;
        border-radius: 30px;
        background: rgba(255,255,255,0.62);
        color: #24563A;
        font-size: 10px;
        font-weight: 800;
        letter-spacing: 1.3px;
        border: 1px solid rgba(255,255,255,0.7);
    }

    /* SECCIÓN DE ACCESOS */

    .access-section {
        text-align: center;
        padding: 42px 10px 18px 10px;
    }

    .access-section h2 {
        font-family: 'Playfair Display', serif;
        color: #16452E;
        font-size: 35px;
        font-weight: 700;
        margin: 0 0 8px 0;
    }

    .access-section p {
        color: #687D6D;
        font-size: 14px;
        margin: 0;
    }

    /* TARJETAS */

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #FFFFFF;
        border: 1px solid #DCEBDD;
        border-radius: 18px;
        padding: 22px;
        box-shadow: 0 7px 22px rgba(25, 73, 45, 0.06);
    }

    .card-icon {
        font-size: 36px;
        margin-bottom: 9px;
    }

    .card-title {
        color: #19472F;
        font-size: 22px;
        font-weight: 800;
        margin-bottom: 8px;
    }

    .card-text {
        color: #718174;
        font-size: 13px;
        line-height: 1.7;
        min-height: 72px;
        margin-bottom: 15px;
    }

    /* BOTONES */

    div[data-testid="stPageLink"] a {
        background: #24583A;
        color: #FFFFFF !important;
        border-radius: 10px;
        border: none;
        padding: 12px 16px;
        font-weight: 800;
        text-decoration: none;
    }

    div[data-testid="stPageLink"] a:hover {
        background: #B5DD65;
        color: #183D27 !important;
    }

    /* PIE DE PÁGINA */

    .footer {
        text-align: center;
        padding: 28px 10px 8px 10px;
        color: #809183;
        font-size: 12px;
    }

    /* ADAPTACIÓN A MÓVILES */

    @media (max-width: 768px) {

        .block-container {
            padding: 0.7rem 0.8rem 2rem 0.8rem;
        }

        .hero {
            min-height: 650px;
            padding: 42px 16px 30px 16px;
            background-position: center center;
        }

        .hero-description {
            font-size: 14px;
        }

        .access-section h2 {
            font-size: 29px;
        }

    }

    </style>
    """,
    unsafe_allow_html=True
)


# =====================================================
# PORTADA PRINCIPAL
# =====================================================

if fondo:

    st.markdown(
        f"""
        <section class="hero" style="background-image:
            linear-gradient(
                to bottom,
                rgba(218, 247, 231, 0.05) 0%,
                rgba(218, 247, 231, 0.02) 48%,
                rgba(2, 48, 35, 0.12) 100%
            ),
            url('{fondo}');">

            <div class="hero-content">

                <div class="brand-small">
                    🌱 TECNOLOGÍA PARA EL CAMPO
                </div>

                <h1>GranjaConecta</h1>

                <div class="hero-description">
                    Una granja más inteligente, conectada y sostenible.
                    Monitorea y controla espacios esenciales para el
                    bienestar animal mediante tecnología y automatización.
                </div>

                <div class="hero-tag">
                    INNOVACIÓN · BIENESTAR ANIMAL · AUTOMATIZACIÓN
                </div>

            </div>

        </section>
        """,
        unsafe_allow_html=True
    )

else:

    st.error(
        "No se encontró la imagen 'fondogranja.jpg'. "
        "Colócala en la raíz del repositorio, "
        "junto a Inicioapp.py."
    )


# =====================================================
# SECCIÓN DE ACCESO
# =====================================================

st.markdown(
    """
    <div class="access-section">

        <h2>Explora tu granja</h2>

        <p>
            Selecciona el área que deseas supervisar y controlar.
        </p>

    </div>
    """,
    unsafe_allow_html=True
)


# =====================================================
# TARJETAS DE LAS DOS SECCIONES
# =====================================================

col_corral, col_bebedero = st.columns(
    2,
    gap="large"
)


# -----------------------------------------------------
# SECCIÓN CORRAL
# -----------------------------------------------------

with col_corral:

    with st.container(border=True):

        st.markdown(
            """
            <div class="card-icon">🐄</div>

            <div class="card-title">
                Control del corral
            </div>

            <div class="card-text">
                Gestiona la apertura y el cierre de la puerta
                del corral y regula la ventilación mediante
                reconocimiento de gestos.
            </div>
            """,
            unsafe_allow_html=True
        )

        st.page_link(
            "pages/2_Corral.py",
            label="INGRESAR AL CORRAL  →",
            use_container_width=True
        )


# -----------------------------------------------------
# SECCIÓN BEBEDERO
# -----------------------------------------------------

with col_bebedero:

    with st.container(border=True):

        st.markdown(
            """
            <div class="card-icon">💧</div>

            <div class="card-title">
                Control del bebedero
            </div>

            <div class="card-text">
                Consulta el nivel de agua, la temperatura
                y la humedad. Controla la válvula mediante
                comandos de voz o texto.
            </div>
            """,
            unsafe_allow_html=True
        )

        st.page_link(
            "pages/1_Bebedero.py",
            label="INGRESAR AL BEBEDERO  →",
            use_container_width=True
        )


# =====================================================
# PIE DE PÁGINA
# =====================================================

st.markdown(
    """
    <div class="footer">

        <strong>GranjaConecta</strong><br>

        Tecnología al servicio del bienestar animal.

    </div>
    """,
    unsafe_allow_html=True
)
