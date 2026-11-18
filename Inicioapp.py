
import streamlit as st
from pathlib import Path

# --------------------------------
# CONFIGURACIÓN
# --------------------------------

st.set_page_config(
    page_title="GranjaConecta",
    page_icon="🐄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------
# ESTILOS
# --------------------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Nunito Sans', sans-serif;
}

.stApp {
    background: #F5F9F3;
}

.block-container {
    max-width: 1180px;
    padding-top: 2rem;
    padding-bottom: 2rem;
}

header[data-testid="stHeader"] {
    background: transparent;
}

.brand {
    color: #183D2A;
    font-size: 36px;
    font-weight: 800;
    letter-spacing: -1px;
}

.brand span {
    color: #8DBB37;
}

.tagline {
    color: #647568;
    font-size: 16px;
    margin-top: -8px;
}

.hero {
    background: #E8F2E4;
    border-radius: 22px;
    padding: 25px 30px;
    margin: 22px 0;
    text-align: center;
}

.hero h2 {
    color: #183D2A;
    font-size: 28px;
    margin-bottom: 8px;
}

.hero p {
    color: #506452;
    font-size: 16px;
    margin-bottom: 0;
}

.section-heading {
    color: #183D2A;
    font-size: 25px;
    font-weight: 800;
    margin-top: 28px;
    margin-bottom: 5px;
}

.section-description {
    color: #657568;
    font-size: 15px;
    margin-bottom: 20px;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: white;
    border: 1px solid #E1EBDD;
    border-radius: 18px;
    padding: 15px;
}

.card-title {
    color: #183D2A;
    font-size: 23px;
    font-weight: 800;
}

.card-description {
    color: #5E6D61;
    font-size: 15px;
    min-height: 70px;
}

div.stButton > button,
div[data-testid="stPageLink"] a {
    background: #24583A;
    color: white !important;
    border: none;
    border-radius: 12px;
    font-weight: 700;
    padding: 12px 18px;
    transition: 0.2s;
}

div.stButton > button:hover,
div[data-testid="stPageLink"] a:hover {
    background: #A6D63D;
    color: #173B27 !important;
    border: none;
}

footer {
    visibility: hidden;
}

</style>
""", unsafe_allow_html=True)

# --------------------------------
# BARRA LATERAL
# --------------------------------

with st.sidebar:
    st.markdown("## 🐄 GranjaConecta")
    st.caption("Monitoreo inteligente de granjas")

    st.divider()

    st.markdown("### Navegación")
    st.page_link("app.py", label="Inicio", icon="🏠")
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
    st.caption("Tecnología al servicio del bienestar animal.")

# --------------------------------
# ENCABEZADO
# --------------------------------

st.markdown("""
<div class="brand">Granja<span>Conecta</span> 🐄</div>
<div class="tagline">
Tecnología, bienestar animal y gestión inteligente
</div>
""", unsafe_allow_html=True)

# --------------------------------
# BIENVENIDA
# --------------------------------

st.markdown("""
<div class="hero">
    <h2>¡Bienvenido a tu granja!</h2>
    <p>
    Un espacio para supervisar y controlar las áreas
    principales de GranjaConecta.
    </p>
</div>
""", unsafe_allow_html=True)

# --------------------------------
# ILUSTRACIÓN DE LA GRANJA
# --------------------------------

image_path = Path("assets/granja_conecta.png")

if image_path.exists():
    st.image(
        str(image_path),
        use_container_width=True
    )
else:
    st.warning(
        "Agrega la ilustración en assets/granja_conecta.png"
    )

# --------------------------------
# ACCESOS A LAS DOS SECCIONES
# --------------------------------

st.markdown(
    '<div class="section-heading">Explora tu granja</div>',
    unsafe_allow_html=True
)

st.markdown("""
<div class="section-description">
Selecciona el área que deseas consultar o controlar.
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")

with col1:
    with st.container(border=True):
        st.markdown(
            '<div class="card-title">🐄 El corral</div>',
            unsafe_allow_html=True
        )

        st.markdown("""
        <div class="card-description">
        Supervisa el acceso al corral, controla la puerta
        y regula la ventilación mediante reconocimiento
        de gestos.
        </div>
        """, unsafe_allow_html=True)

        st.page_link(
            "pages/2_Corral.py",
            label="INGRESAR AL CORRAL",
            icon="➡️",
            use_container_width=True
        )

with col2:
    with st.container(border=True):
        st.markdown(
            '<div class="card-title">💧 El bebedero</div>',
            unsafe_allow_html=True
        )

        st.markdown("""
        <div class="card-description">
        Consulta el nivel de agua, la temperatura y la
        humedad. Controla la válvula mediante voz o texto.
        </div>
        """, unsafe_allow_html=True)

        st.page_link(
            "pages/1_Bebedero.py",
            label="INGRESAR AL BEBEDERO",
            icon="➡️",
            use_container_width=True
        )

# --------------------------------
# PIE DE PÁGINA
# --------------------------------

st.divider()

st.markdown("""
<div style="text-align:center; color:#718074; padding:10px;">
    <b>GranjaConecta</b><br>
    Innovación para una gestión ganadera inteligente
</div>
""", unsafe_allow_html=True)
