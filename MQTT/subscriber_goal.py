from PyQt6.QtCore import pyqtSignal
from .mqtt_subscriber import MQTTSubscriberThread
import json

class GoalSubscriberThread(MQTTSubscriberThread):
    goal_update = pyqtSignal(str)  # Signal để gửi giá trị tên về main window

    def __init__(self, mqtt_host, mqtt_port, mqtt_topic="robot/goal", mqtt_username=None, mqtt_password=None):
        super().__init__(mqtt_host, mqtt_port, mqtt_topic, mqtt_username=mqtt_username, mqtt_password=mqtt_password)

    def on_message(self, client, userdata, msg):
        """Callback khi nhận được message"""
        try:
            message = msg.payload.decode('utf-8')
            print(f"Received goal data: {message}")

            name = json.loads(message)

            self.goal_update.emit(name)

        except (ValueError, TypeError) as e:
            print(f"Error parsing goal data: {e}")