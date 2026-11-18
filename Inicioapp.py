
import streamlit as st
from pathlib import Path
import base64

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
    if ruta.exists():
        with open(ruta, "rb") as archivo:
            return base64.b64encode(archivo.read()).decode()
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

/* FONDO GENERAL */

.stApp {
    background: #F1F8F2;
    font-family: 'DM Sans', sans-serif;
}

.block-container {
    max-width: 1250px;
    padding: 1.5rem 2.5rem 4rem 2.5rem;
}

/* TIPOGRAFÍA */

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* OCULTAR ELEMENTOS */

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

/* EXPANDERS Y ELEMENTOS DESPLEGABLES */

div[data-testid="stExpander"] {
    background: linear-gradient(
        135deg,
        #063C2E,
        #0B6848
    );
    border: 1px solid #397D5B;
    border-radius: 12px;
    color: white;
}

div[data-testid="stExpander"] summary {
    color: white !important;
    font-weight: 700;
}

div[data-testid="stExpander"] summary p {
    color: white !important;
}

/* MARCA SUPERIOR */

.brand {
    color: #174D37;
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 2px;
}

/* HERO */

.hero {
    width: 100%;
    min-height: 390px;
    border-radius: 18px;
    background-position: center 52%;
    background-size: cover;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    align-items: flex-start;
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
    font-size: clamp(42px, 6vw, 76px);
    font-weight: 800;
    line-height: 1.05;
    letter-spacing: -2px;
    margin: 0;
}

.hero-description {
    color: #F0FFF3;
    font-size: 15px;
    line-height: 1.8;
    margin-top: 17px;
    max-width: 520px;
}

/* SECCIÓN DE INFORMACIÓN */

.section-label {
    color: #43805C;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 3px;
}

.section-title {
    color: #103E2E;
    font-size: 34px;
    font-weight: 800;
    letter-spacing: -1px;
    line-height: 1.2;
}

.section-description {
    color: #587263;
    font-size: 14px;
    line-height: 1.9;
}

/* TARJETAS */

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #FFFFFF;
    border: 1px solid #DCECE0;
    border-radius: 15px;
    padding: 22px;
    box-shadow: 0 8px 25px rgba(12, 65, 41, 0.06);
}

.card-number {
    color: #7AAB87;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 2px;
}

.card-heading {
    color: #123F2E;
    font-size: 26px;
    font-weight: 800;
    margin-top: 8px;
}

.card-description {
    color: #607568;
    font-size: 13px;
    line-height: 1.8;
    min-height: 75px;
}

/* BOTONES STREAMLIT */

.stButton > button,
.stPageLink > a {
    background: #B8E36B !important;
    color: #123C2A !important;
    border: none !important;
    border-radius: 8px !important;
    min-height: 46px;
    font-size: 12px !important;
    font-weight: 800 !important;
    letter-spacing: 1px;
    transition: all 0.2s ease;
}

.stButton > button:hover,
.stPageLink > a:hover {
    background: #174F37 !important;
    color: white !important;
    border: none !important;
    transform: translateY(-2px);
}

/* PIE */

.footer {
    color: #6E8B79;
    font-size: 11px;
    letter-spacing: 1px;
    text-align: center;
    padding-top: 25px;
}

/* RESPONSIVE */

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
# PORTADA CON IMAGEN Y TÍTULO
# =====================================================

if imagen:

    st.markdown(
        f"""
        <div class="hero"
        style="background-image:
        url('data:image/jpeg;base64,{imagen}');">

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
    '<p class="section-title">Una granja conectada, '
    'un cuidado más inteligente.</p>',
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
# DOS ÁREAS DE LA APLICACIÓN
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

        st.markdown("## 🐄")

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
            """,
            unsafe_allow_html=True
        )

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

        st.markdown("## 💧")

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
