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


import unicodedata

def remove_accents(input_str):
    """Remove Vietnamese accents from a string"""
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

class GoalPublisher(MQTTTemplate):
    def __init__(self):
        MQTTTemplate.__init__(self)
        self.topic = get_topic("goal")  

    def publish_goal(self, goal):
        """Publish goal as JSON message, with only non-accented name"""
        try:
            # Nếu goal là JSON string, parse ra dict để xử lý tên
            goal_obj = json.loads(goal)
            if 'name' in goal_obj:
                goal_obj['name'] = remove_accents(goal_obj['name'])
            goal = json.dumps(goal_obj, ensure_ascii=False)
        except Exception:
            # Nếu không phải JSON hoặc lỗi, gửi nguyên bản
            pass
        self.publish_and_exit(self.topic, goal, delay=0.05)
        print("Published goal successfully!")

def main():
    if len(sys.argv) < 2:
        print("Usage: python2 goal_publisher.py '<json_goal>'")
        return 1

    try:
        goal_json = sys.argv[1]
        pub = GoalPublisher()
        pub.publish_goal(goal_json)
        print("Published goal successfully!")
        return 0
    except Exception as e:
        print("Error: {}".format(e))
        return 1

if __name__ == "__main__":
    sys.exit(main())