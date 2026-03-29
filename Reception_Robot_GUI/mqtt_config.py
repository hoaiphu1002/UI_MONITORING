"""
MQTT Configuration file
Tập trung quản lý các thông số MQTT để tránh hard-code ở nhiều nơi
"""

class MQTTConfig:
    """Class chứa tất cả cấu hình MQTT"""
    
    MQTT_HOST = "45.117.177.157" #127.0.0.1 #192.168.0.130
    MQTT_PORT = 1883
    MQTT_KEEPALIVE = 60
    MQTT_USERNAME = "client"
    MQTT_PASSWORD = "viam1234"
    
    # Các MQTT Topics
    TOPICS = {
        "battery": "robot/battery",
        "attendance": "robot/attendance",
        "camera": "robot/camera", 
        "status": "robot/status",
        "location": "robot/location",
        "velocity": "robot/velocity",
        "waypoints" : "robot/waypoints",
        "arrival": "robot/arrival",
        "telemetry": "robot/telemetry",
        "goal": "robot/goal"
    }
    
    @classmethod
    def get_config(cls, topic_name):
        """
        Lấy cấu hình MQTT cho một topic cụ thể
        
        Args:
            topic_name (str): Tên topic cần lấy config
            
        Returns:
            dict: Dictionary chứa mqtt_host, mqtt_port, mqtt_topic, mqtt_username, mqtt_password
        """
        if topic_name not in cls.TOPICS:
            raise ValueError(f"Topic '{topic_name}' không tồn tại. Available topics: {list(cls.TOPICS.keys())}")
            
        return {
            "mqtt_host": cls.MQTT_HOST,
            "mqtt_port": cls.MQTT_PORT,
            "mqtt_topic": cls.TOPICS[topic_name],
            "mqtt_username": cls.MQTT_USERNAME,
            "mqtt_password": cls.MQTT_PASSWORD
        }
    
    @classmethod
    def get_all_configs(cls):
        """Lấy tất cả config cho các topic"""
        return {topic: cls.get_config(topic) for topic in cls.TOPICS.keys()}
    
    @classmethod
    def update_host(cls, new_host):
        """Cập nhật MQTT host"""
        cls.MQTT_HOST = new_host
        print(f"MQTT Host updated to: {new_host}")
    
    @classmethod
    def update_port(cls, new_port):
        """Cập nhật MQTT port"""
        cls.MQTT_PORT = new_port
        print(f"MQTT Port updated to: {new_port}")
    
    @classmethod
    def update_credentials(cls, username, password):
        """Cập nhật MQTT username và password"""
        cls.MQTT_USERNAME = username
        cls.MQTT_PASSWORD = password
        print(f"MQTT credentials updated for user: {username}")
        
    @classmethod
    def add_topic(cls, topic_name, topic_path):
        """Thêm topic mới"""
        cls.TOPICS[topic_name] = topic_path
        print(f"Added new topic: {topic_name} -> {topic_path}")

# Các default configs cho từng loại manager
BATTERY_CONFIG = MQTTConfig.get_config("battery")
ATTENDANCE_CONFIG = MQTTConfig.get_config("attendance")
LOCATION_CONFIG = MQTTConfig.get_config("location")
VELOCITY_CONFIG = MQTTConfig.get_config("velocity")
ARRIVAL_CONFIG = MQTTConfig.get_config("arrival")
GOAL_CONFIG = MQTTConfig.get_config("goal")