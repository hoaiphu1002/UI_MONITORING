import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

class BaseManager:
    """Base class cho các manager để tránh code trùng lắp"""
    
    def __init__(self, ui, subscriber_class, mqtt_config):
        self.ui = ui
        self.subscriber_class = subscriber_class
        self.mqtt_config = mqtt_config
        self.subscriber_thread = None
        self.is_running = False
        
    def start_subscriber(self):
        """Khởi tạo và bắt đầu subscriber thread"""
        if not hasattr(self, "subscriber_thread") or self.subscriber_thread is None:
            self.subscriber_thread = self.subscriber_class(**self.mqtt_config)
            self._connect_signals()
            self.subscriber_thread.start()
            self.is_running = True
            print(f"{self.__class__.__name__} subscriber started")

    def stop_subscriber(self):
        """Dừng subscriber thread"""
        if self.subscriber_thread:
            self.subscriber_thread.stop()
            self.subscriber_thread = None
            self.is_running = False
            print(f"{self.__class__.__name__} subscriber stopped")
            
    def restart_subscriber(self):
        """Khởi động lại subscriber (hữu ích khi thay đổi config)"""
        print(f"Restarting {self.__class__.__name__} subscriber...")
        self.stop_subscriber()
        self.start_subscriber()

    def update_mqtt_config(self, new_config):
        """Cập nhật config MQTT và khởi động lại subscriber nếu đang chạy"""
        was_running = self.is_running
        if was_running:
            self.stop_subscriber()
        
        self.mqtt_config = new_config
        print(f"Updated MQTT config for {self.__class__.__name__}: {new_config}")
        
        if was_running:
            self.start_subscriber()

    def _connect_signals(self):
        """Kết nối signals - sẽ được override bởi lớp con"""
        self.mqtt_status = "connected"
        self.ui.label_mqtt.setText(self.mqtt_status)
        self.ui.label_mqtt_2.setText(self.mqtt_status)
        self.ui.label_mqtt_3.setText(self.mqtt_status)
        raise NotImplementedError("Subclass must implement _connect_signals method")

    def handle_data_update(self, data):
        """Xử lý dữ liệu nhận được - sẽ được override bởi lớp con"""
        raise NotImplementedError("Subclass must implement handle_data_update method")

    def is_subscriber_running(self):
        """Kiểm tra trạng thái subscriber"""
        return self.is_running
        
    def get_current_config(self):
        """Lấy config hiện tại"""
        return self.mqtt_config.copy()
