import base64
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


# ==================================================
# CONFIGURACIÓN
# ==================================================

st.set_page_config(
    page_title="GranjaConecta",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

CARPETA = Path(__file__).resolve().parent
RUTA_IMAGEN = CARPETA / "fondogranja.jpg"


# ==================================================
# CARGAR IMAGEN
# ==================================================

def cargar_imagen(ruta):
    if not ruta.exists():
        return None

    extension = ruta.suffix.lower()
    tipos = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }

    tipo = tipos.get(extension)
    if tipo is None:
        return None

    with open(ruta, "rb") as archivo:
        contenido = base64.b64encode(archivo.read()).decode("utf-8")

    return f"data:{tipo};base64,{contenido}"


imagen_portada = cargar_imagen(RUTA_IMAGEN)


# ==================================================
# ESTILOS GENERALES DE STREAMLIT
# ==================================================

st.markdown(
    """
    <style>
    .stApp {
        background-color: #f4faf5;
        color: #183d2b;
    }

    [data-testid="stHeader"] {
        background-color: transparent;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1250px;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #123d2b 0%, #1c5638 100%);
    }

    [data-testid="stSidebar"] * {
        color: white;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: white;
    }

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

    @media (max-width: 700px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ==================================================
# MENÚ LATERAL
# ==================================================

with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center; padding:20px 5px 25px 5px;">
            <div style="font-size:42px;">🌱</div>
            <div style="font-size:23px; font-weight:800; color:white;">
                GranjaConecta
            </div>
            <div style="font-size:11px; letter-spacing:2px; color:#c6f36a; margin-top:5px;">
                TECNOLOGÍA PARA EL CAMPO
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")
    st.markdown("### Navegación")

    st.page_link("Inicioapp.py", label="🏠 Inicio")
    st.page_link("pages/1_Bebedero.py", label="💧 Bebedero")
    st.page_link("pages/2_Corral.py", label="🐄 Corral")

    st.markdown("---")
    st.caption("Sistema inteligente para el cuidado animal")


# ==================================================
# PORTADA: HTML EN COMPONENTE INDEPENDIENTE
# ==================================================

if imagen_portada:
    fondo_css = f"background-image: linear-gradient(90deg, rgba(8,39,25,.88) 0%, rgba(12,54,33,.65) 55%, rgba(12,54,33,.10) 100%), url('{imagen_portada}');"
else:
    fondo_css = "background: linear-gradient(135deg, #174a32, #246642);"

html_portada = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
* {{ box-sizing: border-box; }}
html, body {{
    margin: 0;
    padding: 0;
    width: 100%;
    font-family: Arial, Helvetica, sans-serif;
}}
.hero {{
    width: 100%;
    min-height: 390px;
    border-radius: 22px;
    overflow: hidden;
    display: flex;
    align-items: center;
    background-color: #1b5638;
    background-size: cover;
    background-position: center;
    {fondo_css}
}}
.hero-content {{
    padding: 55px;
    max-width: 700px;
}}
.hero-label {{
    color: #c6f36a;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 3px;
    margin-bottom: 18px;
}}
.hero-title {{
    color: white;
    font-size: clamp(38px, 6vw, 65px);
    font-weight: 800;
    line-height: 1.05;
    margin: 0 0 20px 0;
}}
.hero-description {{
    color: #f1f8f1;
    font-size: 17px;
    line-height: 1.7;
    max-width: 570px;
}}
.hero-line {{
    width: 85px;
    height: 5px;
    background-color: #c6f36a;
    border-radius: 10px;
    margin-top: 25px;
}}
@media (max-width: 700px) {{
    .hero {{ min-height: 360px; }}
    .hero-content {{ padding: 28px; }}
    .hero-description {{ font-size: 15px; }}
}}
</style>
</head>
<body>
    <div class="hero">
        <div class="hero-content">
            <div class="hero-label">TECNOLOGÍA PARA EL CAMPO</div>
            <h1 class="hero-title">GranjaConecta</h1>
            <div class="hero-description">
                Conectamos la tecnología con el bienestar animal.
                Una granja inteligente donde el monitoreo y la
                automatización facilitan el cuidado diario.
            </div>
            <div class="hero-line"></div>
        </div>
    </div>
</body>
</html>
"""

components.html(html_portada, height=410, scrolling=False)

if not imagen_portada:
    st.warning(
        "No se encontró fondogranja.jpg. "
        "Coloca la imagen en la misma carpeta que Inicioapp.py."
    )


# ==================================================
# PRESENTACIÓN
# ==================================================

st.markdown(
    """
    <div class="section-title">Bienvenido a GranjaConecta</div>
    <div class="section-description">
        Una solución tecnológica diseñada para facilitar
        el monitoreo y la automatización de las actividades
        de una granja, conectando sensores, dispositivos
        y herramientas digitales en un solo lugar.
    </div>
    """,
    unsafe_allow_html=True
)


# ==================================================
# TARJETAS: HTML EN COMPONENTES INDEPENDIENTES
# ==================================================

def mostrar_tarjeta(icono, titulo, descripcion):
    html_tarjeta = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
    * {{ box-sizing: border-box; }}
    html, body {{
        margin: 0;
        padding: 0;
        width: 100%;
        font-family: Arial, Helvetica, sans-serif;
    }}
    .card-box {{
        background: linear-gradient(145deg, #174a32 0%, #246642 100%);
        border-radius: 20px;
        padding: 28px;
        min-height: 225px;
        border: 1px solid rgba(255,255,255,.12);
        box-shadow: 0 8px 22px rgba(20,65,42,.10);
    }}
    .card-icon {{
        font-size: 38px;
        margin-bottom: 14px;
    }}
    .card-title {{
        color: white;
        font-size: 24px;
        font-weight: 800;
        margin-bottom: 12px;
    }}
    .card-description {{
        color: #e1f0e4;
        font-size: 14px;
        line-height: 1.6;
        min-height: 65px;
    }}
    </style>
    </head>
    <body>
        <div class="card-box">
            <div class="card-icon">{icono}</div>
            <div class="card-title">{titulo}</div>
            <div class="card-description">{descripcion}</div>
        </div>
    </body>
    </html>
    """
    components.html(html_tarjeta, height=245, scrolling=False)


col1, col2 = st.columns(2, gap="large")

with col1:
    mostrar_tarjeta(
        "🐄",
        "Corral inteligente",
        "Controla el acceso del corral, reconoce gestos "
        "y regula la ventilación para favorecer el "
        "bienestar de los animales."
    )

    if st.button(
        "Ingresar al Corral →",
        key="boton_corral",
        use_container_width=True
    ):
        st.switch_page("pages/2_Corral.py")


with col2:
    mostrar_tarjeta(
        "💧",
        "Bebedero inteligente",
        "Supervisa el nivel de agua y las condiciones "
        "ambientales, y controla el suministro mediante "
        "comandos de voz o texto."
    )

    if st.button(
        "Ingresar al Bebedero →",
        key="boton_bebedero",
        use_container_width=True
    ):
        st.switch_page("pages/1_Bebedero.py")


# ==================================================
# PIE DE PÁGINA
# ==================================================

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
