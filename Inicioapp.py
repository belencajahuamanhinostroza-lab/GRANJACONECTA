
import streamlit as st
from pathlib import Path

# =====================================================
# CONFIGURACIÓN DE LA APLICACIÓN
# =====================================================

st.set_page_config(
    page_title="GranjaConecta | Inicio",
    page_icon="🐄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ruta principal del proyecto
BASE_DIR = Path(__file__).resolve().parent
IMAGE_PATH = BASE_DIR / "assets" / "granja_conecta.png"


# =====================================================
# DISEÑO Y ESTILOS
# =====================================================

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@400;500;600;700;800;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Nunito Sans', sans-serif;
}

.stApp {
    background-color: #F5F9F3;
    color: #17251B;
}

.block-container {
    max-width: 1200px;
    padding-top: 2rem;
    padding-bottom: 2rem;
}

/* BARRA LATERAL */

section[data-testid="stSidebar"] {
    background-color: #E8F1E5;
}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #204B32;
}

/* ENCABEZADO */

.brand {
    font-size: 38px;
    font-weight: 900;
    color: #204B32;
    letter-spacing: -1.5px;
}

.brand span {
    color: #91BD36;
}

.tagline {
    color: #68796C;
    font-size: 15px;
    margin-top: -8px;
}

/* PRESENTACIÓN */

.hero {
    background: linear-gradient(120deg, #E6F1E2, #F1F7E9);
    border: 1px solid #DCE9D7;
    border-radius: 22px;
    padding: 28px;
    margin-top: 25px;
    margin-bottom: 22px;
}

.hero h2 {
    color: #204B32;
    font-size: 29px;
    font-weight: 900;
    margin-bottom: 8px;
}

.hero p {
    color: #526656;
    font-size: 16px;
    margin-bottom: 0;
}

/* SECCIONES */

.section-heading {
    color: #204B32;
    font-size: 26px;
    font-weight: 900;
    margin-top: 28px;
}

.section-description {
    color: #68796C;
    font-size: 15px;
    margin-bottom: 20px;
}

/* TARJETAS */

div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #FFFFFF;
    border: 1px solid #E0E9DD;
    border-radius: 18px;
    padding: 18px;
}

.card-title {
    color: #204B32;
    font-size: 24px;
    font-weight: 900;
    margin-bottom: 8px;
}

.card-description {
    color: #627165;
    font-size: 15px;
    min-height: 75px;
}

/* BOTONES Y ENLACES */

div[data-testid="stPageLink"] a {
    background-color: #24583A;
    color: white !important;
    border-radius: 12px;
    border: none;
    font-weight: 800;
    padding: 12px;
    text-decoration: none;
}

div[data-testid="stPageLink"] a:hover {
    background-color: #A6D63D;
    color: #17251B !important;
}

/* PIE DE PÁGINA */

.footer {
    text-align: center;
    color: #758477;
    font-size: 13px;
    padding: 15px;
}

</style>
""", unsafe_allow_html=True)


# =====================================================
# BARRA LATERAL Y NAVEGACIÓN
# =====================================================

with st.sidebar:

    st.markdown(
        "<h2 style='color:#204B32;'>🐄 GranjaConecta</h2>",
        unsafe_allow_html=True
    )

    st.caption("Sistema inteligente de monitoreo ganadero")

    st.divider()

    st.markdown("### Menú principal")

    st.page_link(
        "Inicioapp.py",
        label="Inicio",
        icon="🏠"
    )

    st.page_link(
        "pages/1_Bebedero.py",
        label="Control del bebedero",
        icon="💧"
    )

    st.page_link(
        "pages/2_Corral.py",
        label="Control del corral",
        icon="🐄"
    )

    st.divider()

    st.markdown("### Nuestro propósito")

    st.caption(
        "Integrar tecnología y automatización "
        "para apoyar el cuidado y la gestión "
        "de una granja ganadera."
    )


# =====================================================
# ENCABEZADO PRINCIPAL
# =====================================================

st.markdown("""
<div class="brand">
    Granja<span>Conecta</span> 🐄
</div>

<div class="tagline">
    Tecnología, bienestar animal y gestión inteligente
</div>
""", unsafe_allow_html=True)


# =====================================================
# MENSAJE DE BIENVENIDA
# =====================================================

st.markdown("""
<div class="hero">

    <h2>¡Bienvenido a tu granja!</h2>

    <p>
        Con GranjaConecta puedes supervisar y controlar
        áreas importantes de tu granja mediante herramientas
        tecnológicas que facilitan el monitoreo y la automatización.
    </p>

</div>
""", unsafe_allow_html=True)


# =====================================================
# ILUSTRACIÓN PRINCIPAL DE LA GRANJA
# =====================================================

if IMAGE_PATH.exists():

    st.image(
        str(IMAGE_PATH),
        use_container_width=True
    )

else:

    st.warning(
        "No se encontró la imagen de la granja. "
        "Verifica que esté guardada en assets/granja_conecta.png"
    )


# =====================================================
# ACCESO A LAS SECCIONES
# =====================================================

st.markdown(
    '<div class="section-heading">Explora tu granja</div>',
    unsafe_allow_html=True
)

st.markdown("""
<div class="section-description">
    Selecciona el área que deseas consultar o controlar.
</div>
""", unsafe_allow_html=True)


col_corral, col_bebedero = st.columns(2, gap="large")


# -----------------------------------------------------
# TARJETA DEL CORRAL
# -----------------------------------------------------

with col_corral:

    with st.container(border=True):

        st.markdown(
            '<div class="card-title">🐄 Control del corral</div>',
            unsafe_allow_html=True
        )

        st.markdown("""
        <div class="card-description">
            Supervisa el acceso al corral, controla la apertura
            y el cierre de la puerta y regula la ventilación
            mediante reconocimiento de gestos.
        </div>
        """, unsafe_allow_html=True)

        st.page_link(
            "pages/2_Corral.py",
            label="INGRESAR AL CORRAL",
            icon="➡️",
            use_container_width=True
        )


# -----------------------------------------------------
# TARJETA DEL BEBEDERO
# -----------------------------------------------------

with col_bebedero:

    with st.container(border=True):

        st.markdown(
            '<div class="card-title">💧 Control del bebedero</div>',
            unsafe_allow_html=True
        )

        st.markdown("""
        <div class="card-description">
            Consulta el nivel de agua, la temperatura y la humedad.
            Controla la apertura y el cierre de la válvula
            mediante comandos de voz o texto.
        </div>
        """, unsafe_allow_html=True)

        st.page_link(
            "pages/1_Bebedero.py",
            label="INGRESAR AL BEBEDERO",
            icon="➡️",
            use_container_width=True
        )


# =====================================================
# PIE DE PÁGINA
# =====================================================

st.divider()

st.markdown("""
<div class="footer">
    <strong>GranjaConecta</strong><br>
    Innovación y tecnología para el sector ganadero.
</div>
""", unsafe_allow_html=True)
