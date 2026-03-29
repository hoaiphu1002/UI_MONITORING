import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from MQTT.subscriber_telemetry import TelemetrySubscriberThread
from manager.manager_base import BaseManager
from mqtt_config import MQTTConfig

TELEMETRY_CONFIG = MQTTConfig.get_config("telemetry")


class TelemetryManager(BaseManager):
    def __init__(self, ui, plot_telemetry):
        super().__init__(ui, TelemetrySubscriberThread, TELEMETRY_CONFIG)
        self.plot_telemetry = plot_telemetry
        
        # Khởi tạo giá trị mặc định
        self.data = {
            "imu": "0",
            "odom": "0",
            "send": "0"
        }

    def _connect_signals(self):
        self.subscriber_thread.telemetry_update.connect(self.handle_data_update)

    def start_telemetry_subscriber(self):
        self.start_subscriber()

    def stop_telemetry_subscriber(self):
        self.stop_subscriber()

    def handle_data_update(self, imu, odom, send):
        self.plot_telemetry.update_packet_loss(imu, odom, send)
