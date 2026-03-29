import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from MQTT.subscriber_battery import BatterySubscriberThread
from manager.manager_base import BaseManager
from mqtt_config import BATTERY_CONFIG

class BatteryManager(BaseManager):
    def __init__(self, ui):
        super().__init__(ui, BatterySubscriberThread, BATTERY_CONFIG)
        
        # Khoi tao trang thai cua mqtt 
        self.mqtt_status = "connected"
        self.ui.label_mqtt.setText(self.mqtt_status)
        self.ui.label_mqtt_3.setText(self.mqtt_status)
        self.ui.label_mqtt_4.setText(self.mqtt_status)

        # Khởi tạo giá trị mặc định cho battery
        self.battery_percent = '88'
        self.ui.label_battery.setText(f"{self.battery_percent}%")
        self.ui.label_battery_3.setText(f"{self.battery_percent}%")
        self.ui.label_battery_4.setText(f"{self.battery_percent}%")
        
    def _connect_signals(self):
        """Kết nối signal cho battery subscriber"""
        self.subscriber_thread.battery_update.connect(self.handle_data_update)

    def start_battery_subscriber(self):
        """Khởi tạo và bắt đầu battery subscriber thread"""
        self.start_subscriber()

    def stop_battery_subscriber(self):
        """Dừng battery subscriber thread"""
        self.stop_subscriber()

    def handle_data_update(self, battery_percent):
        """Cập nhật hiển thị phần trăm pin trên UI"""
        self.battery_percent = battery_percent
        self.ui.label_battery.setText(f"{battery_percent}%")
        self.ui.label_battery_2.setText(f"{battery_percent}%")
        self.ui.label_battery_3.setText(f"{battery_percent}%")
        print(f"Battery updated to: {battery_percent}%")
