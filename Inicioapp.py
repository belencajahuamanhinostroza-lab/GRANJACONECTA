
import streamlit as st
from pathlib import Path
import base64

# =====================================================
# CONFIGURACIÓN
# =====================================================

st.set_page_config(
    page_title="GranjaConecta",
    page_icon="🐄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

BASE_DIR = Path(__file__).resolve().parent
IMAGE_PATH = BASE_DIR / "assets" / "fondogranja.jpg"


# =====================================================
# CARGAR IMAGEN DE FONDO
# =====================================================

def cargar_fondo(ruta):
    if ruta.exists():
        with open(ruta, "rb") as imagen:
            contenido = base64.b64encode(imagen.read()).decode()
        return f"data:image/jpeg;base64,{contenido}"
    return None


fondo = cargar_fondo(IMAGE_PATH)


# =====================================================
# ESTILOS
# =====================================================

if fondo:

    st.markdown(f"""
    <style>

    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Playfair+Display:wght@600;700&display=swap');

    .stApp {{
        background-color: #EAF7EF;
        font-family: 'DM Sans', sans-serif;
    }}

    .block-container {{
        max-width: 1350px;
        padding: 1rem 2rem 3rem 2rem;
    }}

    /* PORTADA CON IMAGEN */

    .hero {{
        background-image:
            linear-gradient(
                to bottom,
                rgba(218, 247, 231, 0.08) 0%,
                rgba(218, 247, 231, 0.03) 35%,
                rgba(2, 48, 35, 0.18) 100%
            ),
            url("{fondo}");

        background-size: cover;
        background-position: center 42%;
        background-repeat: no-repeat;

        min-height: 790px;
        border-radius: 22px;
        position: relative;
        overflow: hidden;

        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: flex-start;

        padding: 65px 25px 40px 25px;
        text-align: center;
        box-shadow: 0 12px 35px rgba(17, 64, 43, 0.10);
    }}

    .hero-content {{
        max-width: 850px;
        margin: 0 auto;
        position: relative;
        z-index: 2;
    }}

    .brand-small {{
        color: #24563A;
        font-size: 13px;
        font-weight: 800;
        letter-spacing: 4px;
        text-transform: uppercase;
        margin-bottom: 32px;
    }}

    .hero h1 {{
        font-family: 'Playfair Display', serif;
        color: #104331;
        font-size: clamp(42px, 6vw, 76px);
        font-weight: 700;
        line-height: 1.08;
        margin-bottom: 18px;
        text-shadow: 0 2px 12px rgba(255,255,255,0.18);
    }}

    .hero-description {{
        color: #24563F;
        font-size: 17px;
        font-weight: 600;
        line-height: 1.8;
        max-width: 690px;
        margin: 0 auto;
    }}

    .hero-tag {{
        display: inline-block;
        margin-top: 25px;
        padding: 9px 18px;
        border-radius: 30px;
        background: rgba(255,255,255,0.55);
        color: #24563A;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 1.5px;
        border: 1px solid rgba(255,255,255,0.65);
    }}

    /* SECCIÓN DE ACCESOS */

    .access-section {{
        text-align: center;
        padding: 45px 10px 15px 10px;
    }}

    .access-section h2 {{
        font-family: 'Playfair Display', serif;
        color: #16452E;
        font-size: 36px;
        font-weight: 700;
        margin-bottom: 8px;
    }}

    .access-section p {{
        color: #687D6D;
        font-size: 15px;
        margin-bottom: 10px;
    }}

    /* TARJETAS */

    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: #FFFFFF;
        border: 1px solid #DCEBDD;
        border-radius: 19px;
        padding: 23px;
        box-shadow: 0 7px 22px rgba(25, 73, 45, 0.06);
    }}

    .card-icon {{
        font-size: 37px;
        margin-bottom: 10px;
    }}

    .card-title {{
        color: #19472F;
        font-size: 23px;
        font-weight: 800;
        margin-bottom: 9px;
    }}

    .card-text {{
        color: #718174;
        font-size: 14px;
        line-height: 1.7;
        min-height: 75px;
    }}

    /* BOTONES DE NAVEGACIÓN */

    div[data-testid="stPageLink"] a {{
        background-color: #24583A;
        color: #FFFFFF !important;
        border-radius: 11px;
        border: none;
        padding: 13px 18px;
        font-weight: 800;
        text-align: center;
        transition: 0.2s;
    }}

    div[data-testid="stPageLink"] a:hover {{
        background-color: #B5DD65;
        color: #183D27 !important;
    }}

    /* PIE */

    .footer {{
        text-align: center;
        padding: 30px 10px 10px;
        color: #809183;
        font-size: 12px;
    }}

    @media (max-width: 768px) {{
        .hero {{
            min-height: 650px;
            padding-top: 45px;
            background-position: center center;
        }}

        .hero-description {{
            font-size: 14px;
        }}

        .access-section h2 {{
            font-size: 29px;
        }}
    }}

    </style>
    """, unsafe_allow_html=True)

else:

    st.error(
        "No se encontró assets/fondogranja.jpg. "
        "Comprueba que la imagen esté en la carpeta assets."
    )


# =====================================================
# PORTADA PRINCIPAL
# =====================================================

st.markdown("""
<div class="hero">

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

</div>
""", unsafe_allow_html=True)


# =====================================================
# SECCIÓN DE ACCESO
# =====================================================

st.markdown("""
<div class="access-section">

    <h2>Explora tu granja</h2>

    <p>
        Selecciona el área que deseas supervisar y controlar.
    </p>

</div>
""", unsafe_allow_html=True)


# =====================================================
# DOS SECCIONES PRINCIPALES
# =====================================================

col_corral, col_bebedero = st.columns(2, gap="large")


# -----------------------------------------------------
# CORRAL
# -----------------------------------------------------

with col_corral:

    with st.container(border=True):

        st.markdown("""
        <div class="card-icon">🐄</div>

        <div class="card-title">
            Control del corral
        </div>

        <div class="card-text">
            Gestiona la apertura y el cierre de la puerta
            del corral y regula la ventilación mediante
            reconocimiento de gestos.
        </div>
        """, unsafe_allow_html=True)

        st.page_link(
            "pages/2_Corral.py",
            label="INGRESAR AL CORRAL  →",
            use_container_width=True
        )


# -----------------------------------------------------
# BEBEDERO
# -----------------------------------------------------

with col_bebedero:

    with st.container(border=True):

        st.markdown("""
        <div class="card-icon">💧</div>

        <div class="card-title">
            Control del bebedero
        </div>

        <div class="card-text">
            Consulta el nivel de agua, la temperatura
            y la humedad. Controla la válvula mediante
            comandos de voz o texto.
        </div>
        """, unsafe_allow_html=True)

        st.page_link(
            "pages/1_Bebedero.py",
            label="INGRESAR AL BEBEDERO  →",
            use_container_width=True
        )


# =====================================================
# PIE DE PÁGINA
# =====================================================

st.markdown("""
<div class="footer">

    <b>GranjaConecta</b><br>

    Tecnología al servicio del bienestar animal.

</div>
""", unsafe_allow_html=True)
