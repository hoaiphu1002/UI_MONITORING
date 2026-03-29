import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from MQTT.subscriber_velocity import VelocitySubscriberThread
from manager.manager_base import BaseManager
from mqtt_config import MQTTConfig

VELOCITY_CONFIG = MQTTConfig.get_config("velocity")

class VelocityManager(BaseManager):
    def __init__(self, ui):
        super().__init__(ui, VelocitySubscriberThread, VELOCITY_CONFIG)
        # Khoi tao 
        self.velocity = {'left': '??', 'right': '??'}
        self._update_velocity_labels()

    def _connect_signals(self):
        self.subscriber_thread.velocity_update.connect(self.handle_data_update)

    def start_velocity_subscriber(self):
        self.start_subscriber()

    def stop_velocity_subscriber(self):
        self.stop_subscriber()

    def handle_data_update(self, left, right):
        self.velocity = {
            'left': f"{left:.2f}",
            'right': f"{right:.2f}"
        }
        self._update_velocity_labels()

    def _update_velocity_labels(self):
        self.ui.label_left.setText(f"Left: {self.velocity['left']}")
        self.ui.label_left_2.setText(f"Left: {self.velocity['left']}")
        self.ui.label_left_3.setText(f"Left: {self.velocity['left']}")
        self.ui.label_right.setText(f"Right: {self.velocity['right']}")
        self.ui.label_right_2.setText(f"Right: {self.velocity['right']}")
        self.ui.label_right_3.setText(f"Right: {self.velocity['right']}")