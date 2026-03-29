from PyQt6.QtCore import pyqtSignal
from .mqtt_subscriber import MQTTSubscriberThread
import json

class LocationSubscriberThread(MQTTSubscriberThread):
    location_update = pyqtSignal(float, float, float)  # x, y, theta

    def __init__(self, mqtt_host, mqtt_port, mqtt_topic="robot/location", mqtt_username=None, mqtt_password=None):
        super().__init__(mqtt_host, mqtt_port, mqtt_topic, mqtt_username=mqtt_username, mqtt_password=mqtt_password)

    def on_message(self, client, userdata, msg):
        """Callback khi nhận được message từ MQTT"""
        try:
            message = msg.payload.decode('utf-8')
            #print(f"[MQTT] Received location data: {message}")

            data = json.loads(message)
            x = float(data.get('x', 0.0))
            y = float(data.get('y', 0.0))
            theta = float(data.get('theta', 0.0))

            self.location_update.emit(x, y, theta)

        except (json.JSONDecodeError, ValueError, TypeError) as e:
            print(f"[MQTT] Error parsing location data: {e}")
