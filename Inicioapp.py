
import streamlit as st
from pathlib import Path
import base64
import mimetypes

# =====================================================
# CONFIGURACIÓN
# =====================================================

st.set_page_config(
    page_title="GranjaConecta",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

BASE_DIR = Path(__file__).resolve().parent
IMAGE_PATH = BASE_DIR / "fondogranja.jpg"


# =====================================================
# CARGAR IMAGEN
# =====================================================

def cargar_imagen(ruta):
    if ruta.is_file():
        with open(ruta, "rb") as archivo:
            contenido = base64.b64encode(archivo.read()).decode("utf-8")

        tipo, _ = mimetypes.guess_type(str(ruta))
        if tipo is None:
            tipo = "image/jpeg"

        return f"data:{tipo};base64,{contenido}"

    return None


imagen = cargar_imagen(IMAGE_PATH)


# =====================================================
# ESTILOS
# =====================================================

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');

:root {
    --verde-oscuro: #063C2E;
    --verde-medio: #176344;
    --verde-lima: #B8E36B;
    --verde-menta: #E9F6EE;
    --texto: #183D30;
}

/* CONFIGURACIÓN GENERAL */

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
}

.stApp {
    background: #F1F8F2;
    color: var(--texto);
}

.block-container {
    max-width: 1250px;
    padding: 1.5rem 2.5rem 4rem 2.5rem;
}

/* OCULTAR ELEMENTOS DE STREAMLIT */

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

header[data-testid="stHeader"] {
    background: transparent;
}

/* BARRA LATERAL */

section[data-testid="stSidebar"] {
    background: linear-gradient(
        180deg,
        #052F25 0%,
        #07513A 55%,
        #0B6946 100%
    );
}

section[data-testid="stSidebar"] * {
    color: #F1FFF5 !important;
}

section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #D6F1DF !important;
}

/* ELEMENTOS DESPLEGABLES */

div[data-testid="stExpander"] {
    background: linear-gradient(
        135deg,
        #063C2E,
        #0B6848
    );
    border: 1px solid #397D5B;
    border-radius: 12px;
}

div[data-testid="stExpander"] summary,
div[data-testid="stExpander"] summary p {
    color: white !important;
    font-weight: 700;
}

/* MARCA */

.brand {
    color: #174D37;
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 2px;
}

/* PORTADA */

.hero {
    width: 100%;
    min-height: 390px;
    border-radius: 18px;
    background-position: center 52%;
    background-size: cover;
    background-repeat: no-repeat;
    display: flex;
    align-items: flex-end;
    padding: 45px 55px;
    box-sizing: border-box;
    overflow: hidden;
    position: relative;
    box-shadow: 0 15px 40px rgba(4, 53, 37, 0.18);
}

.hero::before {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(
        90deg,
        rgba(2, 38, 29, 0.78) 0%,
        rgba(2, 45, 32, 0.38) 55%,
        rgba(2, 45, 32, 0.05) 100%
    );
}

.hero-content {
    position: relative;
    z-index: 1;
    max-width: 650px;
}

.hero-label {
    color: #D5F4C0;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 4px;
    margin-bottom: 12px;
}

.hero-title {
    color: #FFFFFF;
    font-family: 'DM Sans', sans-serif;
    font-size: clamp(42px, 6vw, 76px);
    font-weight: 800;
    line-height: 1.05;
    letter-spacing: -2px;
    margin: 0;
}

.hero-description {
    color: #F0FFF3;
    font-size: 15px;
    font-weight: 500;
    line-height: 1.8;
    margin-top: 17px;
    max-width: 520px;
}

.hero-line {
    width: 55px;
    height: 4px;
    background: #B8E36B;
    border-radius: 10px;
    margin-top: 22px;
}

/* INFORMACIÓN */

.section-label {
    color: #43805C;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 3px;
}

.section-title {
    color: #103E2E;
    font-family: 'DM Sans', sans-serif;
    font-size: 34px;
    font-weight: 800;
    letter-spacing: -1px;
    line-height: 1.3;
}

.section-description {
    color: #587263;
    font-size: 15px;
    font-weight: 500;
    line-height: 1.9;
    max-width: 950px;
}

/* TARJETAS DE CONTROL */

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(
        145deg,
        #063C2E 0%,
        #07533B 50%,
        #11714A 100%
    ) !important;
    border: 1px solid #397D5B !important;
    border-radius: 18px !important;
    padding: 22px !important;
    box-shadow: 0 12px 28px rgba(3, 52, 36, 0.14);
    transition: transform 0.25s ease;
}

div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    transform: translateY(-4px);
}

/* TEXTO INTERNO DE LAS TARJETAS */

.card-number {
    color: #B8E36B;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 2px;
}

.card-heading {
    color: #FFFFFF;
    font-size: 26px;
    font-weight: 800;
    margin-top: 8px;
    letter-spacing: -0.5px;
}

.card-description {
    color: #E0F1E5;
    font-size: 14px;
    font-weight: 500;
    line-height: 1.8;
    min-height: 85px;
}

.card-icon {
    font-size: 37px;
    margin-top: 14px;
    margin-bottom: 8px;
}

.card-tag {
    display: inline-block;
    color: #D9F5B8;
    background: rgba(184, 227, 107, 0.13);
    border: 1px solid rgba(184, 227, 107, 0.35);
    border-radius: 30px;
    padding: 7px 12px;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1px;
}

/* BOTONES */

div[data-testid="stPageLink"] a {
    background: #B8E36B !important;
    color: #123C2A !important;
    border: none !important;
    border-radius: 9px !important;
    min-height: 46px;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 12px !important;
    font-weight: 800 !important;
    letter-spacing: 1px;
    justify-content: center;
    transition: all 0.2s ease;
}

div[data-testid="stPageLink"] a:hover {
    background: #D0F19B !important;
    color: #063C2E !important;
    transform: translateY(-2px);
}

/* PIE DE PÁGINA */

.footer {
    color: #6E8B79;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    text-align: center;
    padding-top: 25px;
}

/* MÓVILES */

@media (max-width: 768px) {

    .block-container {
        padding: 1rem;
    }

    .hero {
        min-height: 330px;
        padding: 25px;
        background-position: center;
    }

    .hero-title {
        font-size: 43px;
    }

    .hero-description {
        font-size: 13px;
    }

    .section-title {
        font-size: 27px;
    }

    .card-heading {
        font-size: 23px;
    }
}

</style>
""", unsafe_allow_html=True)


# =====================================================
# BARRA LATERAL
# =====================================================

with st.sidebar:

    st.markdown("## ✳ GRANJACONECTA")
    st.caption("TECNOLOGÍA PARA EL CAMPO")

    st.divider()

    st.markdown("### Navegación")

    st.page_link(
        "Inicioapp.py",
        label="Inicio",
        icon="🏠"
    )

    st.page_link(
        "pages/1_Bebedero.py",
        label="Bebedero",
        icon="💧"
    )

    st.page_link(
        "pages/2_Corral.py",
        label="Corral",
        icon="🐄"
    )

    st.divider()

    with st.expander("Acerca del proyecto"):
        st.write(
            "GranjaConecta integra sensores, automatización "
            "y reconocimiento de gestos para apoyar el "
            "bienestar animal."
        )

    st.caption("INNOVACIÓN · CONTROL · BIENESTAR")


# =====================================================
# ENCABEZADO
# =====================================================

st.markdown(
    '<p class="brand">✳ GRANJACONECTA</p>',
    unsafe_allow_html=True
)

st.write("")


# =====================================================
# PORTADA PRINCIPAL
# =====================================================

if imagen:

    st.markdown(
        f"""
        <div class="hero"
        style="background-image:
        url('{imagen}');">

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
        """,
        unsafe_allow_html=True
    )

else:

    st.warning(
        "No se encontró fondogranja.jpg. "
        "Coloca la imagen junto a Inicioapp.py."
    )


# =====================================================
# INFORMACIÓN DEL PROYECTO
# =====================================================

st.write("")
st.write("")

st.markdown(
    '<p class="section-label">NUESTRA PROPUESTA</p>',
    unsafe_allow_html=True
)

st.markdown(
    '<p class="section-title">'
    'Una granja conectada, un cuidado más inteligente.'
    '</p>',
    unsafe_allow_html=True
)

st.markdown(
    """
    <p class="section-description">
    GranjaConecta es una propuesta de monitoreo y automatización
    que integra tecnología IoT para mejorar la supervisión de
    espacios importantes de una granja.<br><br>

    Mediante sensores y controles inteligentes, permite consultar
    las condiciones del bebedero y gestionar funciones del corral,
    facilitando el cuidado de los animales.
    </p>
    """,
    unsafe_allow_html=True
)


# =====================================================
# ACCESO A LAS DOS ÁREAS
# =====================================================

st.write("")
st.write("")

st.markdown(
    '<p class="section-label">EXPLORA TU GRANJA</p>',
    unsafe_allow_html=True
)

st.markdown(
    '<p class="section-title">Dos áreas, un mismo propósito.</p>',
    unsafe_allow_html=True
)

st.markdown(
    '<p class="section-description">'
    'Selecciona el espacio que deseas supervisar y controlar.'
    '</p>',
    unsafe_allow_html=True
)

st.write("")

col1, col2 = st.columns(2, gap="large")


# =====================================================
# TARJETA CORRAL
# =====================================================

with col1:

    with st.container(border=True):

        st.markdown(
            '<p class="card-number">01 / CONTROL ANIMAL</p>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="card-icon">🐄</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<p class="card-heading">El Corral</p>',
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <p class="card-description">
            Supervisa el acceso al corral mediante el control
            de la puerta y la ventilación. Utiliza reconocimiento
            de gestos para ejecutar las acciones.
            </p>
            <span class="card-tag">
            GESTOS · AUTOMATIZACIÓN
            </span>
            """,
            unsafe_allow_html=True
        )

        st.write("")

        st.page_link(
            "pages/2_Corral.py",
            label="INGRESAR AL CORRAL  →",
            use_container_width=True
        )


# =====================================================
# TARJETA BEBEDERO
# =====================================================

with col2:

    with st.container(border=True):

        st.markdown(
            '<p class="card-number">02 / CONTROL HÍDRICO</p>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="card-icon">💧</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<p class="card-heading">El Bebedero</p>',
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <p class="card-description">
            Consulta el nivel de agua, la temperatura y la
            humedad. Controla la apertura y el cierre de la
            válvula mediante comandos de voz o texto.
            </p>
            <span class="card-tag">
            VOZ · MONITOREO · SENSORES
            </span>
            """,
            unsafe_allow_html=True
        )

        st.write("")

        st.page_link(
            "pages/1_Bebedero.py",
            label="INGRESAR AL BEBEDERO  →",
            use_container_width=True
        )


# =====================================================
# PIE DE PÁGINA
# =====================================================

st.write("")
st.write("")

st.markdown(
    """
    <div class="footer">
        ✳ GRANJACONECTA
        <br><br>
        Tecnología al servicio del bienestar animal.
        <br>
        INNOVACIÓN · CONTROL · BIENESTAR
    </div>
    """,
    unsafe_allow_html=True
)
