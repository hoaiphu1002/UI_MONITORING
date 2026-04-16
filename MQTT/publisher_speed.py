import time
import json
from MQTT.mqtt_publisher_config import MQTTTemplate, get_topic

class SpeedPublisher(MQTTTemplate):
    def __init__(self):
        super().__init__()
        self.topic = get_topic("speed")

    def publish_speed(self, speed):
        self.publish_and_exit(self.topic, str(speed), delay=0.05)
        print(f"Published speed: {speed}")
