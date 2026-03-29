from PyQt6.QtCore import pyqtSignal
from .mqtt_subscriber import MQTTSubscriberThread
import json

class ArrivalSubscriberThread(MQTTSubscriberThread):
    arrival_update = pyqtSignal(bool)  # arrived

    def __init__(self, mqtt_host, mqtt_port, mqtt_topic="robot/arrival", mqtt_username=None, mqtt_password=None):
        super().__init__(mqtt_host, mqtt_port, mqtt_topic, mqtt_username=mqtt_username, mqtt_password=mqtt_password)

    def on_message(self, client, userdata, msg):
        """Callback khi nhận được message từ MQTT"""
        try:
            message = msg.payload.decode('utf-8').strip().lower()
            arrived = message == "true"
            self.arrival_update.emit(arrived)

        except (json.JSONDecodeError, ValueError, TypeError) as e:
            print(f"[MQTT] Error parsing location data: {e}")