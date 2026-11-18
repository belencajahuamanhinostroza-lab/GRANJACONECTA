
import json
import threading
import time

import paho.mqtt.client as mqtt


# ---------------------------------
# CONFIGURACIÓN MQTT
# ---------------------------------

BROKER = "broker.hivemq.com"
PORT = 1883

TOPIC_COMANDOS = "granjaconecta/comandos"
TOPIC_TELEMETRIA = "granjaconecta/telemetria"
TOPIC_RESPUESTAS = "granjaconecta/respuestas"


# ---------------------------------
# DATOS COMPARTIDOS
# ---------------------------------

_lock = threading.Lock()

_latest_telemetry = {}
_responses = []

_client = None
_connected = False
_started = False


# ---------------------------------
# RECEPCIÓN DE MENSAJES
# ---------------------------------

def on_connect(client, userdata, flags, reason_code, properties):
    global _connected

    if reason_code == 0:
        _connected = True

        client.subscribe(TOPIC_TELEMETRIA)
        client.subscribe(TOPIC_RESPUESTAS)

    else:
        _connected = False


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    global _connected
    _connected = False


def on_message(client, userdata, message):
    global _latest_telemetry, _responses

    try:
        payload = message.payload.decode("utf-8")

        if message.topic == TOPIC_TELEMETRIA:

            data = json.loads(payload)

            if isinstance(data, dict):
                with _lock:
                    _latest_telemetry = data

        elif message.topic == TOPIC_RESPUESTAS:

            try:
                response = json.loads(payload)
            except json.JSONDecodeError:
                response = payload

            with _lock:
                _responses.append(response)
                _responses = _responses[-30:]

    except Exception as error:
        print("Error recibiendo MQTT:", error)


# ---------------------------------
# INICIAR CONEXIÓN
# ---------------------------------

def start_mqtt():

    global _client, _started

    if _started and _client is not None:
        return

    try:

        _client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"GranjaConecta_Streamlit_{int(time.time())}"
        )

        _client.on_connect = on_connect
        _client.on_disconnect = on_disconnect
        _client.on_message = on_message

        _client.reconnect_delay_set(
            min_delay=1,
            max_delay=30
        )

        _client.connect_async(
            BROKER,
            PORT,
            keepalive=60
        )

        _client.loop_start()

        _started = True

    except Exception as error:

        _client = None
        _started = False

        print("Error iniciando MQTT:", error)


# ---------------------------------
# ESTADO DE CONEXIÓN
# ---------------------------------

def mqtt_status():

    start_mqtt()

    return _connected


# ---------------------------------
# OBTENER TELEMETRÍA
# ---------------------------------

def get_latest_telemetry():

    start_mqtt()

    with _lock:
        return _latest_telemetry.copy()


# ---------------------------------
# OBTENER RESPUESTAS
# ---------------------------------

def get_responses():

    start_mqtt()

    with _lock:
        return _responses.copy()


# ---------------------------------
# ENVIAR COMANDOS AL ESP32
# ---------------------------------

def publish_command(command):

    start_mqtt()

    if _client is None:
        return False, "No se pudo iniciar la conexión MQTT."

    if not _connected:
        return False, "Todavía no hay conexión con el broker MQTT."

    try:

        payload = json.dumps({
            "comando": command
        })

        result = _client.publish(
            TOPIC_COMANDOS,
            payload,
            qos=0
        )

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            return True, f"Orden enviada: {command}"

        return False, "No se pudo publicar la orden MQTT."

    except Exception as error:

        return False, f"Error MQTT: {error}"


# Iniciar la conexión al importar el módulo
start_mqtt()
