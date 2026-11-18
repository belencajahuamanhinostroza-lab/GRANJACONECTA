
import streamlit as st
import base64
from pathlib import Path
import mimetypes

# ==========================================
# CONFIGURACIÓN GENERAL
# ==========================================

st.set_page_config(
    page_title="GranjaConecta",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# CARGA DE LA IMAGEN DE PORTADA
# ==========================================

RUTA_IMAGEN = Path(__file__).parent / "fondogranja.jpg"

def cargar_imagen(ruta):
    if ruta.exists():
        with open(ruta, "rb") as archivo:
            imagen = base64.b64encode(archivo.read()).decode()

        tipo, _ = mimetypes.guess_type(str(ruta))

        if tipo is None:
            tipo = "image/jpeg"

        return f"data:{tipo};base64,{imagen}"

    return None


imagen_fondo = cargar_imagen(RUTA_IMAGEN)

# ==========================================
# ESTILOS CSS
# ==========================================

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

/* CONFIGURACIÓN GENERAL */

html, body, [class*="css"] {
    font-family: 'Manrope', sans-serif !important;
}

.stApp {
    background: linear-gradient(
        180deg,
        #F1F9F3 0%,
        #EAF5ED 100%
    );
    color: #123D2D;
}

/* OCULTAR ELEMENTOS INNECESARIOS */

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

header {
    background: transparent !important;
}

/* ESPACIADO GENERAL */

.block-container {
    max-width: 1250px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}

/* MARCA SUPERIOR */

.brand {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #103D2C;
    font-size: 17px;
    font-weight: 800;
    letter-spacing: 1.5px;
    margin-bottom: 30px;
}

.brand-symbol {
    color: #67A94E;
    font-size: 25px;
}

/* PORTADA */

.hero {
    width: 100%;
    min-height: 440px;
    border-radius: 24px;
    background-position: center;
    background-size: cover;
    background-repeat: no-repeat;
    display: flex;
    align-items: center;
    padding: 55px;
    box-sizing: border-box;
    position: relative;
    overflow: hidden;
    box-shadow: 0 15px 40px rgba(3, 49, 34, 0.16);
}

.hero::before {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(
        90deg,
        rgba(2, 35, 27, 0.88) 0%,
        rgba(2, 49, 34, 0.70) 43%,
        rgba(2, 49, 34, 0.12) 100%
    );
}

.hero-content {
    position: relative;
    z-index: 2;
    max-width: 660px;
}

.hero-label {
    color: #C7F29B;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 4px;
    margin-bottom: 20px;
    text-transform: uppercase;
}

.hero-title {
    color: #FFFFFF;
    font-family: 'Manrope', sans-serif;
    font-size: clamp(46px, 6vw, 76px);
    font-weight: 800;
    line-height: 1.08;
    letter-spacing: -3px;
    margin: 0;
}

.hero-description {
    color: #F0FFF4;
    font-size: 16px;
    font-weight: 500;
    line-height: 1.9;
    margin-top: 22px;
    max-width: 530px;
}

.hero-line {
    width: 65px;
    height: 4px;
    background: #BDEB79;
    border-radius: 10px;
    margin-top: 25px;
}

.hero-small {
    color: #D3EBDD;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 2px;
    margin-top: 18px;
}

/* SECCIÓN DE ACCESO */

.access-section {
    margin-top: 55px;
    margin-bottom: 25px;
}

.section-label {
    color: #54865D;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 10px;
}

.section-title {
    color: #103F2E;
    font-size: clamp(27px, 3vw, 37px);
    font-weight: 800;
    letter-spacing: -1.3px;
    line-height: 1.3;
    margin-bottom: 10px;
}

.section-description {
    color: #60796A;
    font-size: 15px;
    font-weight: 500;
    line-height: 1.8;
}

/* TARJETAS */

.control-card {
    background: linear-gradient(
        145deg,
        #06392C 0%,
        #07533B 48%,
        #11714A 100%
    );
    border: 1px solid rgba(193, 235, 169, 0.20);
    border-radius: 21px;
    padding: 30px;
    min-height: 300px;
    box-shadow: 0 12px 30px rgba(3, 52, 36, 0.15);
    transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.control-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 18px 38px rgba(3, 52, 36, 0.22);
}

.card-number {
    color: #BDEB8B;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 3px;
}

.card-icon {
    font-size: 39px;
    margin-top: 23px;
    margin-bottom: 12px;
}

.card-heading {
    color: #FFFFFF;
    font-size: 28px;
    font-weight: 800;
    letter-spacing: -0.8px;
    margin-bottom: 12px;
}

.card-description {
    color: #DCEFE3;
    font-size: 14px;
    font-weight: 500;
    line-height: 1.9;
    min-height: 80px;
    margin-bottom: 22px;
}

.card-tag {
    display: inline-block;
    background: rgba(190, 235, 139, 0.15);
    color: #D6F5B3;
    border: 1px solid rgba(190, 235, 139, 0.3);
    border-radius: 30px;
    padding: 7px 13px;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1px;
}

/* BOTONES DE NAVEGACIÓN */

.stPageLink a {
    background: #C1EB7C !important;
    color: #123D2B !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Manrope', sans-serif !important;
    font-weight: 800 !important;
    font-size: 13px !important;
    min-height: 48px;
    transition: all 0.2s ease;
    justify-content: center !important;
}

.stPageLink a:hover {
    background: #A9DE68 !important;
    color: #06392C !important;
    transform: translateY(-2px);
}

/* PIE DE PÁGINA */

.footer {
    border-top: 1px solid #D6E7D9;
    margin-top: 65px;
    padding-top: 22px;
    text-align: center;
    color: #789080;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
}

/* DISEÑO RESPONSIVE */

@media(max-width: 768px) {

    .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }

    .hero {
        min-height: 370px;
        padding: 25px;
        background-position: center;
    }

    .hero-title {
        font-size: 44px;
        letter-spacing: -2px;
    }

    .hero-description {
        font-size: 13px;
    }

    .control-card {
        padding: 24px;
        min-height: 280px;
    }

    .section-title {
        font-size: 27px;
    }
}

</style>
""", unsafe_allow_html=True)


# ==========================================
# MARCA
# ==========================================

st.markdown("""
<div class="brand">
    <span class="brand-symbol">✳</span>
    GRANJACONECTA
</div>
""", unsafe_allow_html=True)


# ==========================================
# PORTADA PRINCIPAL
# ==========================================

if imagen_fondo:

    st.markdown(f"""
    <div class="hero"
        style="background-image: url('{imagen_fondo}');">

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

            <div class="hero-small">
                INNOVACIÓN · CONTROL · BIENESTAR ANIMAL
            </div>

        </div>
    </div>
    """, unsafe_allow_html=True)

else:

    st.warning(
        "No se encontró fondogranja.jpg. "
        "Coloca la imagen en la raíz del repositorio, "
        "junto a Inicioapp.py."
    )

    st.markdown("""
    <div class="hero" style="
        background: linear-gradient(
            120deg,
            #06392C,
            #11714A
        );">

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

            <div class="hero-small">
                INNOVACIÓN · CONTROL · BIENESTAR ANIMAL
            </div>

        </div>
    </div>
    """, unsafe_allow_html=True)


# ==========================================
# SECCIÓN DE ACCESO A LAS ÁREAS
# ==========================================

st.markdown("""
<div class="access-section">

    <div class="section-label">
        EXPLORA TU GRANJA
    </div>

    <div class="section-title">
        Dos áreas, un mismo propósito.
    </div>

    <div class="section-description">
        Selecciona el espacio que deseas supervisar y controlar.
        Cada área cuenta con herramientas diseñadas para facilitar
        el cuidado y la automatización de la granja.
    </div>

</div>
""", unsafe_allow_html=True)


# ==========================================
# TARJETAS DE CONTROL
# ==========================================

col1, col2 = st.columns(2, gap="large")


# ---------- CORRAL ----------

with col1:

    st.markdown("""
    <div class="control-card">

        <div class="card-number">
            01 / CONTROL ANIMAL
        </div>

        <div class="card-icon">
            🐄
        </div>

        <div class="card-heading">
            El Corral
        </div>

        <div class="card-description">
            Supervisa y controla el espacio del ganado.
            Gestiona la apertura y cierre de la puerta,
            y regula la ventilación mediante reconocimiento
            de gestos.
        </div>

        <div class="card-tag">
            GESTOS · AUTOMATIZACIÓN
        </div>

    </div>
    """, unsafe_allow_html=True)

    st.write("")

    st.page_link(
        "pages/2_Corral.py",
        label="INGRESAR AL CORRAL  →",
        use_container_width=True
    )


# ---------- BEBEDERO ----------

with col2:

    st.markdown("""
    <div class="control-card">

        <div class="card-number">
            02 / CONTROL HÍDRICO
        </div>

        <div class="card-icon">
            💧
        </div>

        <div class="card-heading">
            El Bebedero
        </div>

        <div class="card-description">
            Monitorea el nivel de agua, la temperatura
            y la humedad. Controla la válvula de suministro
            mediante comandos de voz o texto.
        </div>

        <div class="card-tag">
            VOZ · MONITOREO · SENSORES
        </div>

    </div>
    """, unsafe_allow_html=True)

    st.write("")

    st.page_link(
        "pages/1_Bebedero.py",
        label="INGRESAR AL BEBEDERO  →",
        use_container_width=True
    )


# ==========================================
# PIE DE PÁGINA
# ==========================================

st.markdown("""
<div class="footer">
    GRANJACONECTA · INNOVACIÓN PARA EL BIENESTAR ANIMAL
    <br><br>
    MONITOREO · AUTOMATIZACIÓN · TECNOLOGÍA
</div>
""", unsafe_allow_html=True)
