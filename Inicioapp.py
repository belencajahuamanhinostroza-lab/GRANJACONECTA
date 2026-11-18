
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
IMAGE_PATH = BASE_DIR / "fondogranja.jpg"


# =====================================================
# CARGAR FONDO
# =====================================================

def cargar_fondo(ruta):
    if not ruta.is_file():
        return None

    with open(ruta, "rb") as archivo:
        imagen = base64.b64encode(
            archivo.read()
        ).decode("utf-8")

    return f"data:image/jpeg;base64,{imagen}"


fondo = cargar_fondo(IMAGE_PATH)


# =====================================================
# DISEÑO Y TIPOGRAFÍAS
# =====================================================

if fondo:

    st.markdown(
        f"""
        <style>

        @import url(
        'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Playfair+Display:wght@400;500;600;700&display=swap'
        );

        /* FONDO DE TODA LA APLICACIÓN */

        .stApp {{
            background-color: #032E25;
            background-image:
                linear-gradient(
                    rgba(220, 250, 235, 0.04),
                    rgba(0, 35, 27, 0.08)
                ),
                url("{fondo}");

            background-size: 100% auto;
            background-position: center top;
            background-repeat: no-repeat;
            background-attachment: scroll;

            font-family: 'DM Sans', sans-serif;
        }}

        /* QUITAR ELEMENTOS INNECESARIOS */

        #MainMenu {{
            visibility: hidden;
        }}

        footer {{
            visibility: hidden;
        }}

        header[data-testid="stHeader"] {{
            background: transparent;
        }}

        .block-container {{
            max-width: 1250px;
            padding: 1rem 2rem 4rem 2rem;
        }}

        /* BARRA SUPERIOR */

        .navbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 8px;
            margin-bottom: 35px;
        }}

        .brand {{
            font-family: 'DM Sans', sans-serif;
            color: #123F32;
            font-size: 15px;
            font-weight: 800;
            letter-spacing: 1px;
        }}

        .brand span {{
            color: #3E805D;
            margin-right: 7px;
            font-size: 20px;
        }}

        .nav-label {{
            color: #174A38;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1px;
        }}

        /* PORTADA */

        .hero {{
            min-height: 650px;
            display: flex;
            justify-content: flex-start;
            align-items: center;
            flex-direction: column;
            text-align: center;
            padding: 75px 20px 30px 20px;
        }}

        .eyebrow {{
            font-family: 'DM Sans', sans-serif;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 4px;
            color: #245D43;
            text-transform: uppercase;
            margin-bottom: 25px;
        }}

        .hero-title {{
            font-family: 'Playfair Display', serif;
            font-size: clamp(54px, 8vw, 100px);
            font-weight: 500;
            line-height: 1.05;
            letter-spacing: -3px;
            color: #073C31;
            margin: 0;
        }}

        .hero-subtitle {{
            font-family: 'DM Sans', sans-serif;
            font-size: 15px;
            line-height: 1.9;
            font-weight: 500;
            color: #24523E;
            max-width: 620px;
            margin: 28px auto 0 auto;
        }}

        .hero-line {{
            width: 55px;
            height: 2px;
            background: #5D9A69;
            margin: 28px auto;
        }}

        .hero-small {{
            font-family: 'DM Sans', sans-serif;
            color: #32664A;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 3px;
        }}

        /* SECCIÓN INFERIOR */

        .access {{
            text-align: center;
            padding: 45px 10px 20px 10px;
        }}

        .access-label {{
            font-family: 'DM Sans', sans-serif;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 4px;
            color: #B7E8C9;
            margin-bottom: 14px;
        }}

        .access-title {{
            font-family: 'Playfair Display', serif;
            font-size: clamp(34px, 5vw, 52px);
            font-weight: 500;
            color: #F2FFF5;
            margin-bottom: 12px;
        }}

        .access-description {{
            font-family: 'DM Sans', sans-serif;
            font-size: 14px;
            color: #D1E9D9;
            line-height: 1.8;
        }}

        /* TARJETAS */

        div[data-testid="stVerticalBlockBorderWrapper"] {{
            background: rgba(231, 248, 237, 0.95);
            border: 1px solid rgba(255,255,255,0.55);
            border-radius: 4px;
            padding: 25px;
            box-shadow: 0 12px 35px rgba(0, 25, 17, 0.15);
        }}

        .card-number {{
            font-family: 'Playfair Display', serif;
            font-size: 14px;
            color: #659575;
            margin-bottom: 15px;
        }}

        .card-icon {{
            font-size: 36px;
            margin-bottom: 12px;
        }}

        .card-title {{
            font-family: 'Playfair Display', serif;
            color: #123F32;
            font-size: 29px;
            font-weight: 600;
            margin-bottom: 12px;
        }}

        .card-description {{
            font-family: 'DM Sans', sans-serif;
            color: #587064;
            font-size: 13px;
            line-height: 1.8;
            min-height: 75px;
            margin-bottom: 15px;
        }}

        /* BOTONES */

        div[data-testid="stPageLink"] a {{
            background: #B8E56B;
            color: #123D2C !important;
            border: none;
            border-radius: 2px;
            padding: 13px 16px;
            font-family: 'DM Sans', sans-serif;
            font-size: 12px;
            font-weight: 800;
            letter-spacing: 1px;
            transition: 0.3s;
        }}

        div[data-testid="stPageLink"] a:hover {{
            background: #24583A;
            color: white !important;
        }}

        /* PIE DE PÁGINA */

        .footer {{
            text-align: center;
            padding: 55px 10px 15px 10px;
            color: #B7D8C3;
            font-size: 11px;
            letter-spacing: 1px;
        }}

        /* MÓVILES */

        @media (max-width: 768px) {{

            .block-container {{
                padding: 0.5rem 1rem 3rem 1rem;
            }}

            .hero {{
                min-height: 570px;
                padding-top: 65px;
            }}

            .hero-title {{
                letter-spacing: -1px;
            }}

            .hero-subtitle {{
                font-size: 13px;
            }}

            .navbar {{
                margin-bottom: 10px;
            }}

            .nav-label {{
                display: none;
            }}

        }}

        </style>
        """,
        unsafe_allow_html=True
    )


# =====================================================
# BARRA SUPERIOR
# =====================================================

st.markdown(
    """
    <div class="navbar">

        <div class="brand">
            <span>✳</span> GRANJACONECTA
        </div>

        <div class="nav-label">
            BIENESTAR &nbsp;&nbsp;&nbsp;
            TECNOLOGÍA &nbsp;&nbsp;&nbsp;
            AUTOMATIZACIÓN
        </div>

    </div>
    """,
    unsafe_allow_html=True
)


# =====================================================
# PORTADA
# =====================================================

if fondo:

    st.markdown(
        """
        <section class="hero">

            <div class="eyebrow">
                TECNOLOGÍA PARA EL CAMPO
            </div>

            <h1 class="hero-title">
                GranjaConecta
            </h1>

            <div class="hero-subtitle">
                Conectamos la tecnología con el bienestar animal.
                Una propuesta de monitoreo y automatización
                inteligente para hacer más eficiente el cuidado
                de los espacios de una granja.
            </div>

            <div class="hero-line"></div>

            <div class="hero-small">
                INNOVACIÓN · CONTROL · BIENESTAR ANIMAL
            </div>

        </section>
        """,
        unsafe_allow_html=True
    )

else:

    st.error(
        "No se encontró fondogranja.jpg. "
        "Comprueba que esté junto a Inicioapp.py."
    )


# =====================================================
# ACCESO A LAS DOS ÁREAS
# =====================================================

st.markdown(
    """
    <section class="access">

        <div class="access-label">
            EXPLORA TU GRANJA
        </div>

        <div class="access-title">
            Un espacio, dos áreas conectadas
        </div>

        <div class="access-description">
            Selecciona el área que deseas supervisar y controlar.
        </div>

    </section>
    """,
    unsafe_allow_html=True
)


# =====================================================
# TARJETAS DE NAVEGACIÓN
# =====================================================

col_corral, col_bebedero = st.columns(2, gap="large")


# ---------------- CORRAL ----------------

with col_corral:

    with st.container(border=True):

        st.markdown(
            """
            <div class="card-number">01 / CONTROL ANIMAL</div>

            <div class="card-icon">🐄</div>

            <div class="card-title">
                El corral
            </div>

            <div class="card-description">
                Supervisa el acceso al corral y controla
                la apertura de la puerta y la ventilación
                mediante reconocimiento de gestos.
            </div>
            """,
            unsafe_allow_html=True
        )

        st.page_link(
            "pages/2_Corral.py",
            label="EXPLORAR CORRAL  →",
            use_container_width=True
        )


# ---------------- BEBEDERO ----------------

with col_bebedero:

    with st.container(border=True):

        st.markdown(
            """
            <div class="card-number">02 / CONTROL HÍDRICO</div>

            <div class="card-icon">💧</div>

            <div class="card-title">
                El bebedero
            </div>

            <div class="card-description">
                Consulta el nivel de agua, la temperatura
                y la humedad. Controla la válvula mediante
                comandos de voz o texto.
            </div>
            """,
            unsafe_allow_html=True
        )

        st.page_link(
            "pages/1_Bebedero.py",
            label="EXPLORAR BEBEDERO  →",
            use_container_width=True
        )


# =====================================================
# PIE DE PÁGINA
# =====================================================

st.markdown(
    """
    <div class="footer">
        GRANJACONECTA<br><br>
        Tecnología al servicio del bienestar animal.
    </div>
    """,
    unsafe_allow_html=True
)
