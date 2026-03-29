import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from MQTT.subscriber_arrival import ArrivalSubscriberThread
from manager.manager_base import BaseManager
from mqtt_config import MQTTConfig

ARRIVAL_CONFIG = MQTTConfig.get_config("arrival")

class ArrivalManager(BaseManager):
    def __init__(self, ui):
        super().__init__(ui, ArrivalSubscriberThread, ARRIVAL_CONFIG)
        self.arrival = "false"
        self.has_arrived = False  # Thêm cờ để chỉ emit 1 lần

    def _connect_signals(self):
        self.subscriber_thread.arrival_update.connect(self.handle_arrival_update)

    def start_arrival_subscriber(self):
        self.start_subscriber()
        self.has_arrived = False  # Reset khi bắt đầu lại

    def stop_arrival_subscriber(self):
        self.stop_subscriber()

    def handle_arrival_update(self, arrived):
        if arrived == "true" and not self.has_arrived:
            self.has_arrived = True
            self.arrival = arrived
            self.subscriber_thread.arrival_update.emit(arrived)  # Chỉ emit 1 lần
        elif arrived == "false":
            self.arrival = arrived
            # Không emit lại nếu đang false