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
        # Gửi tốc độ phù hợp khi đến điểm nguy hiểm
        from MQTT.publisher_speed import SpeedPublisher
        speed_publisher = SpeedPublisher()
        # Lấy danh sách các điểm nguy hiểm
        special_wps = ["wp3", "meeting room", "restroom"]
        speed = 1.0
        # Nếu có location_tab và đã đến
        if arrived == True and hasattr(self, "location_tab") and self.location_tab is not None:
            # Lấy vị trí hiện tại
            curx, cury, _ = self.location_tab.last_position
            # Lấy danh sách goals
            goals = self.location_tab.goals if hasattr(self.location_tab, "goals") else {}
            wp_names = [wp.lower() for wp in goals.keys()]
            for wp in special_wps:
                if wp in wp_names:
                    idx = wp_names.index(wp)
                    special_coord = goals[list(goals.keys())[idx]]
                    # Nếu vị trí hiện tại gần điểm nguy hiểm
                    if np.linalg.norm(np.array([curx, cury]) - np.array(special_coord)) < 1.0:
                        speed = 0.5
                        break
            speed_publisher.publish_speed(speed)
        elif arrived == False:
            speed_publisher.publish_speed(1.0)
        # Giữ lại logic cũ
        if arrived == True and not self.has_arrived:
            self.has_arrived = True
            self.arrival = arrived
            self.subscriber_thread.arrival_update.emit(arrived)  # Chỉ emit 1 lần
        elif arrived == False:
            self.arrival = arrived
            # Không emit lại nếu đang false