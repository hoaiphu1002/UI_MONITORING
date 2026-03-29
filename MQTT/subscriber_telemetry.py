from PyQt6.QtCore import pyqtSignal
from .mqtt_subscriber import MQTTSubscriberThread
import json

class TelemetrySubscriberThread(MQTTSubscriberThread):
    telemetry_update = pyqtSignal(int, int, int)

    def __init__(self, mqtt_host, mqtt_port, mqtt_topic="robot/telemetry", mqtt_username=None, mqtt_password=None):
        super().__init__(mqtt_host, mqtt_port, mqtt_topic, mqtt_username=mqtt_username, mqtt_password=mqtt_password)

    def on_message(self, client, userdata, msg):
        try:
            message = msg.payload.decode("utf-8")
            data = json.loads(message)

            imu = int(data.get("imu", 0))
            odom = int(data.get("odom", 0))
            send = int(data.get("send", 0))

            self.telemetry_update.emit(imu, odom, send)

        except Exception as e:
            print("[MQTT] Telemetry parsing error:", e)
