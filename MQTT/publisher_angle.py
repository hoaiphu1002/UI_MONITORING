#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
from MQTT.mqtt_publisher_config import MQTTTemplate, get_topic

class AnglePublisher(MQTTTemplate):
    def __init__(self):
        super().__init__()
        self.topic = get_topic("deviation")

    def publish_angle(self, payload):
        """Publish angle as plain integer payload in [0, 359]."""
        try:
            if isinstance(payload, dict) and "angle" in payload:
                angle_value = float(payload["angle"])
            else:
                angle_value = float(payload)

            payload = int(angle_value % 360.0)
            self.publish_and_exit(self.topic, payload, delay=self.delay)
            print("Published deviation successfully!")
        except Exception as e:
            print(f"Failed to publish deviation: {e}")
