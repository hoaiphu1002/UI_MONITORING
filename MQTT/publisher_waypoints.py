#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import sys
import signal
import json
from MQTT.mqtt_publisher_config import MQTTTemplate, get_topic

# Signal handler for clean exit
def signal_handler(sig, frame):
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

class WaypointsPublisher(MQTTTemplate):
    def __init__(self):
        MQTTTemplate.__init__(self)
        self.topic = get_topic("waypoints")  

    def publish_waypoints(self, waypoints):
        """Publish waypoints as JSON message"""
        self.publish_and_exit(self.topic, waypoints, delay=0.05)  # Reduce delay for fast publishing
        print("Published waypoints successfully!")

def main():
    if len(sys.argv) < 2:
        print("Usage: python2 waypoints_publisher.py '<json_waypoints>'")
        return 1

    try:
        waypoints_json = sys.argv[1]
        pub = WaypointsPublisher()
        pub.publish_waypoints(waypoints_json)
        print("Published waypoints successfully!")
        return 0
    except Exception as e:
        print("Error: {}".format(e))
        return 1

if __name__ == "__main__":
    sys.exit(main())