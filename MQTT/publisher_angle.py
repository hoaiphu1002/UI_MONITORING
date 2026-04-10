#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
from MQTT.mqtt_publisher_config import MQTTTemplate, get_topic

class AnglePublisher(MQTTTemplate):
    def __init__(self):
        super().__init__()
        self.topic = get_topic("xoay")  # Default to robot/xoay

    def publish_angle(self, payload):
        """Publish angle as plain integer payload [0-359] to robot/xoay."""
        try:
            if isinstance(payload, dict) and "angle" in payload:
                angle_value = float(payload["angle"])
            else:
                angle_value = float(payload)

            angle_int = int(angle_value % 360.0)
            self.publish_and_exit(self.topic, angle_int, delay=self.delay)
            print(f"Published angle {angle_int} to {self.topic} successfully!")
        except Exception as e:
            print(f"Failed to publish angle: {e}")
