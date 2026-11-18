
import streamlit as st
from pathlib import Path
import base64

# =====================================================
# 1. CONFIGURACIÓN
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
# 2. CARGAR IMAGEN
# =====================================================

def cargar_fondo(ruta):
    if not ruta.exists():
        return None

    with open(ruta, "rb") as archivo:
        contenido = base64.b64encode(
            archivo.read()
        ).decode("utf-8")

    return f"data:image/jpeg;base64,{contenido}"


fondo = cargar_fondo(IMAGE_PATH)


# =====================================================
# 3. DISEÑO VISUAL
# =====================================================

css_fondo = ""

if fondo:
    css_fondo = f"""
        background-image: url("{fondo}");
    """

st.markdown(
    f"""
    <style>

    @import url(
        'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Playfair+Display:wght@400;500;600;700&display=swap'
    );

    /* FONDO GENERAL */

    .stApp {{
        background-color: #032E25;
        {css_fondo}
        background-size: 100% auto;
        background-position: center top;
        background-repeat: no-repeat;
        background-attachment: scroll;
        font-family: 'DM Sans', sans-serif;
    }}

    .block-container {{
        max-width: 1250px;
        padding: 1rem 2rem 4rem 2rem;
    }}

    /* OCULTAR ELEMENTOS DE STREAMLIT */

    #MainMenu {{
        visibility: hidden;
    }}

    footer {{
        visibility: hidden;
    }}

    header[data-testid="stHeader"] {{
        background: transparent;
    }}

    /* TIPOGRAFÍAS */

    h1, h2, h3 {{
        font-family: 'Playfair Display', serif !important;
    }}

    p, label, button {{
        font-family: 'DM Sans', sans-serif !important;
    }}

    /* BARRA SUPERIOR */

    .brand-text {{
        color: #123F32;
        font-family: 'DM Sans', sans-serif;
        font-size: 15px;
        font-weight: 800;
        letter-spacing: 2px;
    }}

    .nav-text {{
        color: #174A38;
        font-family: 'DM Sans', sans-serif;
        font-size: 11px;
        font-weight: 700;
        text-align: right;
        letter-spacing: 1px;
    }}

    /* PORTADA */

    .hero-title {{
        font-family: 'Playfair Display', serif;
        color: #073C31;
        font-size: clamp(48px, 8vw, 100px);
        font-weight: 500;
        line-height: 1.1;
        text-align: center;
        letter-spacing: -2px;
    }}

    .hero-subtitle {{
        color: #24523E;
        font-family: 'DM Sans', sans-serif;
        font-size: 15px;
        line-height: 1.9;
        font-weight: 500;
        text-align: center;
    }}

    .eyebrow {{
        color: #245D43;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 4px;
        text-align: center;
    }}

    .hero-small {{
        color: #32664A;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 3px;
        text-align: center;
    }}

    /* ACCESOS */

    .access-title {{
        color: #F2FFF5;
        font-family: 'Playfair Display', serif;
        font-size: 42px;
        text-align: center;
    }}

    .access-description {{
        color: #D1E9D9;
        font-size: 14px;
        text-align: center;
    }}

    .access-label {{
        color: #B7E8C9;
        font-size: 10px;
        font-weight: 800;
        letter-spacing: 4px;
        text-align: center;
    }}

    /* TARJETAS */

    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: rgba(231, 248, 237, 0.96);
        border: 1px solid rgba(255,255,255,0.55);
        border-radius: 4px;
        padding: 22px;
        box-shadow: 0 12px 35px rgba(0, 25, 17, 0.15);
    }}

    .card-number {{
        color: #659575;
        font-family: 'DM Sans', sans-serif;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 2px;
    }}

    .card-title {{
        color: #123F32;
        font-family: 'Playfair Display', serif;
        font-size: 29px;
        font-weight: 600;
    }}

    .card-description {{
        color: #587064;
        font-family: 'DM Sans', sans-serif;
        font-size: 13px;
        line-height: 1.8;
    }}

    /* BOTONES */

    div[data-testid="stPageLink"] a {{
        background: #B8E56B;
        color: #123D2C !important;
        border-radius: 2px;
        padding: 13px 16px;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 1px;
    }}

    div[data-testid="stPageLink"] a:hover {{
        background: #24583A;
        color: white !important;
    }}

    /* PIE */

    .footer-text {{
        color: #B7D8C3;
        font-size: 11px;
        letter-spacing: 1px;
        text-align: center;
    }}

    /* MÓVILES */

    @media (max-width: 768px) {{

        .block-container {{
            padding: 0.7rem 1rem 3rem 1rem;
        }}

        .hero-title {{
            font-size: 48px;
        }}

        .hero-subtitle {{
            font-size: 13px;
        }}

        .access-title {{
            font-size: 32px;
        }}

    }}

    </style>
    """,
    unsafe_allow_html=True
)


# =====================================================
# 4. BARRA SUPERIOR
# =====================================================

col_brand, col_nav = st.columns([1, 2])

with col_brand:
    st.markdown(
        '<p class="brand-text">✳ GRANJACONECTA</p>',
        unsafe_allow_html=True
    )

with col_nav:
    st.markdown(
        '<p class="nav-text">BIENESTAR  |  TECNOLOGÍA  |  AUTOMATIZACIÓN</p>',
        unsafe_allow_html=True
    )


# =====================================================
# 5. PORTADA
# =====================================================

if fondo:

    st.write("")
    st.write("")
    st.write("")

    st.markdown(
        '<p class="eyebrow">TECNOLOGÍA PARA EL CAMPO</p>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<h1 class="hero-title">GranjaConecta</h1>',
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <p class="hero-subtitle">
        Conectamos la tecnología con el bienestar animal.<br>
        Una propuesta de monitoreo y automatización inteligente
        para hacer más eficiente el cuidado de los espacios de una granja.
        </p>
        """,
        unsafe_allow_html=True
    )

    st.write("")
    st.markdown(
        '<p class="hero-small">INNOVACIÓN · CONTROL · BIENESTAR ANIMAL</p>',
        unsafe_allow_html=True
    )

else:
    st.error(
        "No se encontró fondogranja.jpg. "
        "Coloca la imagen junto a Inicioapp.py."
    )


# =====================================================
# 6. SECCIÓN DE ACCESO
# =====================================================

st.write("")
st.write("")
st.write("")

st.markdown(
    '<p class="access-label">EXPLORA TU GRANJA</p>',
    unsafe_allow_html=True
)

st.markdown(
    '<h2 class="access-title">Un espacio, dos áreas conectadas</h2>',
    unsafe_allow_html=True
)

st.markdown(
    '<p class="access-description">Selecciona el área que deseas supervisar y controlar.</p>',
    unsafe_allow_html=True
)

st.write("")
st.write("")


# =====================================================
# 7. TARJETAS DE NAVEGACIÓN
# =====================================================

col_corral, col_bebedero = st.columns(2, gap="large")


# CORRAL

with col_corral:

    with st.container(border=True):

        st.markdown(
            '<p class="card-number">01 / CONTROL ANIMAL</p>',
            unsafe_allow_html=True
        )

        st.markdown("### 🐄")

        st.markdown(
            '<p class="card-title">El corral</p>',
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <p class="card-description">
            Supervisa el acceso al corral y controla la apertura
            de la puerta y la ventilación mediante reconocimiento
            de gestos.
            </p>
            """,
            unsafe_allow_html=True
        )

        st.page_link(
            "pages/2_Corral.py",
            label="EXPLORAR CORRAL →",
            use_container_width=True
        )


# BEBEDERO

with col_bebedero:

    with st.container(border=True):

        st.markdown(
            '<p class="card-number">02 / CONTROL HÍDRICO</p>',
            unsafe_allow_html=True
        )

        st.markdown("### 💧")

        st.markdown(
            '<p class="card-title">El bebedero</p>',
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <p class="card-description">
            Consulta el nivel de agua, la temperatura y la humedad.
            Controla la válvula mediante comandos de voz o texto.
            </p>
            """,
            unsafe_allow_html=True
        )

        st.page_link(
            "pages/1_Bebedero.py",
            label="EXPLORAR BEBEDERO →",
            use_container_width=True
        )


# =====================================================
# 8. PIE DE PÁGINA
# =====================================================

st.write("")
st.write("")

st.markdown(
    """
    <p class="footer-text">
    GRANJACONECTA<br><br>
    Tecnología al servicio del bienestar animal.
    </p>
    """,
    unsafe_allow_html=True
)
