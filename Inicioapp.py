
import streamlit as st
from pathlib import Path

# ==================================================
# 1. CONFIGURACIÓN
# ==================================================

st.set_page_config(
    page_title="GranjaConecta",
    page_icon="🐄",
    layout="wide",
    initial_sidebar_state="expanded"
)

BASE_DIR = Path(__file__).resolve().parent
IMAGE_PATH = BASE_DIR / "assets" / "granja_conecta.png"


# ==================================================
# 2. ESTILOS VISUALES
# ==================================================

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background-color: #F4FAF5;
    color: #172C20;
}

.block-container {
    max-width: 1450px;
    padding: 1.5rem 2rem 2rem 2rem;
}

/* SIDEBAR */

section[data-testid="stSidebar"] {
    background-color: #FFFFFF;
    border-right: 1px solid #E5EEE6;
}

section[data-testid="stSidebar"] h2 {
    color: #19472D;
    font-weight: 800;
}

section[data-testid="stSidebar"] p {
    color: #718174;
}

/* ENCABEZADO */

.breadcrumb {
    color: #87968A;
    font-size: 12px;
    margin-bottom: 12px;
}

.main-title {
    color: #173F29;
    font-size: 32px;
    font-weight: 800;
    letter-spacing: -1.2px;
    margin-bottom: 4px;
}

.main-subtitle {
    color: #718174;
    font-size: 14px;
    margin-bottom: 20px;
}

/* ETIQUETAS */

.status-label {
    display: inline-block;
    background: #E5F5E4;
    color: #39743D;
    padding: 7px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
}

/* PANELES */

.panel {
    background: #FFFFFF;
    border: 1px solid #E6EEE6;
    border-radius: 17px;
    padding: 17px;
    margin-bottom: 13px;
}

.panel-title {
    color: #244B33;
    font-size: 15px;
    font-weight: 700;
    margin-bottom: 12px;
}

.metric-name {
    color: #7B897E;
    font-size: 12px;
    margin-bottom: 3px;
}

.metric-value {
    color: #214A31;
    font-size: 28px;
    font-weight: 800;
}

.metric-note {
    color: #89968B;
    font-size: 10px;
}

/* INDICADORES */

.indicator {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 10px 0;
    border-bottom: 1px solid #EDF2ED;
    color: #405747;
    font-size: 12px;
}

.indicator:last-child {
    border-bottom: none;
}

.dot {
    width: 9px;
    height: 9px;
    min-width: 9px;
    border-radius: 50%;
    background: #A5C94C;
}

/* TARJETAS INFERIORES */

.section-title {
    color: #204A30;
    font-size: 23px;
    font-weight: 800;
    margin-top: 20px;
}

.section-subtitle {
    color: #7A897D;
    font-size: 13px;
    margin-bottom: 15px;
}

.card-title {
    color: #214B32;
    font-size: 19px;
    font-weight: 800;
}

.card-description {
    color: #738175;
    font-size: 13px;
    min-height: 65px;
    line-height: 1.6;
}

/* ENLACES */

div[data-testid="stPageLink"] a {
    background-color: #244F34;
    color: white !important;
    border-radius: 10px;
    border: none;
    font-weight: 700;
    font-size: 13px;
}

div[data-testid="stPageLink"] a:hover {
    background-color: #B5DD65;
    color: #193B26 !important;
}

/* PIE */

.footer {
    text-align: center;
    color: #849287;
    font-size: 11px;
    padding-top: 12px;
}

</style>
""", unsafe_allow_html=True)


# ==================================================
# 3. MENÚ LATERAL
# ==================================================

with st.sidebar:

    st.markdown("""
    <div style="font-size:25px; font-weight:800; color:#19472D;">
        🌱 GranjaConecta
    </div>
    <div style="font-size:11px; color:#839186;">
        SMART FARM MANAGEMENT
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown("**MENÚ PRINCIPAL**")

    st.page_link(
        "Inicioapp.py",
        label="Inicio",
        icon="🏠"
    )

    st.page_link(
        "pages/2_Corral.py",
        label="Corral",
        icon="🐄"
    )

    st.page_link(
        "pages/1_Bebedero.py",
        label="Bebedero",
        icon="💧"
    )

    st.divider()

    st.markdown("**SOBRE EL PROYECTO**")

    st.caption(
        "Sistema de monitoreo y automatización "
        "para el cuidado y gestión ganadera."
    )

    st.divider()

    st.markdown("""
    <div style="font-size:11px; color:#839186;">
        Tecnología para una granja<br>
        más inteligente y conectada.
    </div>
    """, unsafe_allow_html=True)


# ==================================================
# 4. ENCABEZADO PRINCIPAL
# ==================================================

st.markdown(
    '<div class="breadcrumb">GranjaConecta &nbsp; / &nbsp; Inicio</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="main-title">Panel de control</div>',
    unsafe_allow_html=True
)

st.markdown("""
<div class="main-subtitle">
    Bienvenido a tu espacio de monitoreo y gestión ganadera.
</div>
""", unsafe_allow_html=True)

st.markdown(
    '<span class="status-label">● SISTEMA PREPARADO PARA CONEXIÓN</span>',
    unsafe_allow_html=True
)


# ==================================================
# 5. DISTRIBUCIÓN PRINCIPAL DEL DASHBOARD
# ==================================================

left, center, right = st.columns(
    [1.05, 2.5, 1.05],
    gap="medium"
)


# --------------------------------------------------
# PANEL IZQUIERDO: INDICADORES
# --------------------------------------------------

with left:

    st.markdown("""
    <div class="panel">
        <div class="panel-title">Indicadores</div>
        <div class="metric-name">Nivel del agua</div>
        <div class="metric-value">-- %</div>
        <div class="metric-note">Esperando sensor ultrasónico</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="panel">
        <div class="panel-title">Ambiente</div>
        <div class="metric-name">Temperatura</div>
        <div class="metric-value">-- °C</div>
        <div class="metric-note">Esperando sensor DHT22</div>
        <br>
        <div class="metric-name">Humedad</div>
        <div class="metric-value">-- %</div>
        <div class="metric-note">Esperando lectura del sensor</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="panel">
        <div class="panel-title">Automatización</div>
        <div class="indicator">
            <span class="dot"></span>
            Puerta del corral
        </div>
        <div class="indicator">
            <span class="dot"></span>
            Válvula de agua
        </div>
        <div class="indicator">
            <span class="dot"></span>
            Ventilación
        </div>
    </div>
    """, unsafe_allow_html=True)


# --------------------------------------------------
# CENTRO: ILUSTRACIÓN DE LA GRANJA
# --------------------------------------------------

with center:

    st.markdown("""
    <div style="
        background:#EAF5E9;
        border:1px solid #DFEBDD;
        border-radius:18px;
        padding:15px;
        margin-bottom:10px;
        text-align:center;
    ">
        <div style="
            color:#244B33;
            font-size:17px;
            font-weight:800;
        ">
            Nuestra granja
        </div>
        <div style="
            color:#829084;
            font-size:12px;
        ">
            Un espacio conectado para el bienestar animal
        </div>
    </div>
    """, unsafe_allow_html=True)

    if IMAGE_PATH.exists():

        st.image(
            str(IMAGE_PATH),
            use_container_width=True
        )

    else:

        st.warning(
            "No se encontró la ilustración. "
            "Verifica assets/granja_conecta.png"
        )

    st.caption(
        "Vista ilustrativa de las áreas principales de GranjaConecta."
    )


# --------------------------------------------------
# PANEL DERECHO: ESTADO DE LAS ÁREAS
# --------------------------------------------------

with right:

    st.markdown("""
    <div class="panel">
        <div class="panel-title">Áreas de gestión</div>

        <div class="indicator">
            <span class="dot"></span>
            Corral
        </div>

        <div style="font-size:10px; color:#89968B;">
            Control de puerta y ventilación
        </div>

        <br>

        <div class="indicator">
            <span class="dot"></span>
            Bebedero
        </div>

        <div style="font-size:10px; color:#89968B;">
            Nivel de agua y válvula
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="panel">
        <div class="panel-title">Conectividad</div>

        <div style="color:#879488; font-size:11px;">
            Comunicación MQTT
        </div>

        <div style="
            color:#B18A37;
            font-size:14px;
            font-weight:800;
            margin-top:5px;
        ">
            Pendiente
        </div>

        <div style="color:#879488; font-size:10px;">
            Esperando conexión con ESP32
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="panel">
        <div class="panel-title">Objetivo</div>
        <div style="
            color:#647669;
            font-size:12px;
            line-height:1.7;
        ">
            Facilitar el monitoreo y la automatización
            de las actividades esenciales de la granja.
        </div>
    </div>
    """, unsafe_allow_html=True)


# ==================================================
# 6. ACCESOS A LAS DOS SECCIONES
# ==================================================

st.markdown(
    '<div class="section-title">Explora las áreas de tu granja</div>',
    unsafe_allow_html=True
)

st.markdown("""
<div class="section-subtitle">
    Selecciona una sección para ingresar a sus funciones de control.
</div>
""", unsafe_allow_html=True)

col_corral, col_bebedero = st.columns(2, gap="large")


with col_corral:

    with st.container(border=True):

        st.markdown(
            '<div class="card-title">🐄 Control del corral</div>',
            unsafe_allow_html=True
        )

        st.markdown("""
        <div class="card-description">
            Gestiona la puerta del corral y regula la ventilación
            mediante reconocimiento de gestos.
            Supervisa los estados de los actuadores.
        </div>
        """, unsafe_allow_html=True)

        st.page_link(
            "pages/2_Corral.py",
            label="INGRESAR AL CORRAL",
            icon="➡️",
            use_container_width=True
        )


with col_bebedero:

    with st.container(border=True):

        st.markdown(
            '<div class="card-title">💧 Control del bebedero</div>',
            unsafe_allow_html=True
        )

        st.markdown("""
        <div class="card-description">
            Consulta el nivel de agua, la temperatura y la humedad.
            Controla la válvula mediante comandos de voz o texto.
        </div>
        """, unsafe_allow_html=True)

        st.page_link(
            "pages/1_Bebedero.py",
            label="INGRESAR AL BEBEDERO",
            icon="➡️",
            use_container_width=True
        )


# ==================================================
# 7. PIE DE PÁGINA
# ==================================================

st.divider()

st.markdown("""
<div class="footer">
    <b>GranjaConecta</b><br>
    Innovación, tecnología y bienestar animal.
</div>
""", unsafe_allow_html=True)
