
import streamlit as st

# -----------------------------------------
# CONFIGURACIÓN GENERAL
# -----------------------------------------

st.set_page_config(
    page_title="GranjaConecta",
    page_icon="🐄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------
# ESTILO VISUAL
# -----------------------------------------

st.markdown("""
<style>
    .stApp {
        background-color: #F4F7F1;
    }

    .main-title {
        text-align: center;
        color: #24543B;
        font-size: 48px;
        font-weight: 800;
        margin-bottom: 5px;
    }

    .subtitle {
        text-align: center;
        color: #53665A;
        font-size: 18px;
        margin-bottom: 30px;
    }

    .welcome {
        background-color: #E3EDE2;
        padding: 25px;
        border-radius: 16px;
        text-align: center;
        color: #294B36;
        margin-bottom: 25px;
    }

    .section-title {
        color: #24543B;
        font-size: 24px;
        font-weight: bold;
    }

    div.stButton > button {
        background-color: #34734C;
        color: white;
        border-radius: 10px;
        border: none;
        height: 48px;
        font-weight: bold;
        width: 100%;
    }

    div.stButton > button:hover {
        background-color: #24543B;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------
# BARRA LATERAL
# -----------------------------------------

with st.sidebar:
    st.title("🐄 GranjaConecta")
    st.caption("Sistema inteligente de monitoreo y control")

    st.divider()

    st.write("**Navegación principal**")
    st.write("🏠 Inicio")
    st.write("💧 Control del bebedero")
    st.write("🏡 Control del corral")

    st.divider()

    st.caption("Proyecto de monitoreo y automatización ganadera.")

# -----------------------------------------
# ENCABEZADO
# -----------------------------------------

st.markdown(
    '<div class="main-title">🐄 GranjaConecta</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Tecnología inteligente para el cuidado y monitoreo ganadero'
    '</div>',
    unsafe_allow_html=True
)

# -----------------------------------------
# PRESENTACIÓN
# -----------------------------------------

st.markdown("""
<div class="welcome">
    <h2>¡Bienvenido a GranjaConecta!</h2>
    <p>
        Una propuesta tecnológica que integra monitoreo,
        automatización y control para facilitar la gestión
        de una granja ganadera.
    </p>
    <p>
        Selecciona el área que deseas gestionar para comenzar.
    </p>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------
# SECCIONES PRINCIPALES
# -----------------------------------------

col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown(
        '<div class="section-title">💧 Control del bebedero</div>',
        unsafe_allow_html=True
    )

    st.image(
        "https://images.unsplash.com/photo-1548839140-29a749e1cf4d"
        "?auto=format&fit=crop&w=900&q=80",
        use_container_width=True
    )

    st.write("""
    Consulta el nivel de agua, la temperatura y la humedad.
    También podrás controlar la apertura y el cierre de la válvula
    mediante comandos de voz o texto.
    """)

    st.page_link(
        "pages/1_Bebedero.py",
        label="Ingresar al bebedero 💧",
        icon="➡️",
        use_container_width=True
    )

with col2:
    st.markdown(
        '<div class="section-title">🏡 Control del corral</div>',
        unsafe_allow_html=True
    )

    st.image(
        "https://images.unsplash.com/photo-1500595046743-cd271d694d30"
        "?auto=format&fit=crop&w=900&q=80",
        use_container_width=True
    )

    st.write("""
    Gestiona la apertura y el cierre de la puerta del corral
    y regula la ventilación mediante reconocimiento de gestos.
    """)

    st.page_link(
        "pages/2_Corral.py",
        label="Ingresar al corral 🏡",
        icon="➡️",
        use_container_width=True
    )

# -----------------------------------------
# PIE DE PÁGINA
# -----------------------------------------

st.divider()

st.markdown(
    "<p style='text-align:center; color:#718074;'>"
    "GranjaConecta | Innovación y tecnología para el sector ganadero"
    "</p>",
    unsafe_allow_html=True
)
