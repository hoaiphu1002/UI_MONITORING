from PyQt6.QtCore import pyqtSignal
from .mqtt_subscriber import MQTTSubscriberThread

class AttendanceSubscriberThread(MQTTSubscriberThread):
    attendance_update = pyqtSignal(str, str)  # Signal để gửi giá trị tên về main window

    def __init__(self, mqtt_host, mqtt_port, mqtt_topic="robot/attendance", mqtt_username=None, mqtt_password=None):
        super().__init__(mqtt_host, mqtt_port, mqtt_topic, mqtt_username=mqtt_username, mqtt_password=mqtt_password)

    def on_message(self, client, userdata, msg):
        """Callback khi nhận được message"""
        try:
            message = msg.payload.decode('utf-8')
            print(f"Received attendance data: {message}")

            # Giả sử dữ liệu tên là một chuỗi đơn giản hoặc JSON chứa key 'name'
            try:
                import json
                data = json.loads(message)
                if isinstance(data, dict) and 'message' in data:
                    name = str(data['message'])
                    time_str = str(data.get('time', ''))
                else:
                    name = str(message)
                    time_str = ""
            except (json.JSONDecodeError, ValueError):
                name = str(message)
                time_str = ""

            self.attendance_update.emit(name, time_str)

        except (ValueError, TypeError) as e:
            print(f"Error parsing attendance data: {e}")