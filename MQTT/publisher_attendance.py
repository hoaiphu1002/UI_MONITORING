#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys
import json
import time
import random
from datetime import datetime, timedelta
from MQTT.mqtt_publisher_config import MQTTTemplate, get_topic


# Danh sách nhân viên
ta = [
    {"id": "E001", "name": "Ky"},
    {"id": "E002", "name": "Duy"},
    {"id": "E003", "name": "Phu"},
    {"id": "E004", "name": "Thu"},
    {"id": "E005", "name": "Loi"},
    {"id": "E006", "name": "Thien"},
]

# Thời gian: từ 7:30 đến 8:00 hôm nay
today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
start_time = today + timedelta(hours=7, minutes=30)


class AttendancePublisher(MQTTTemplate):
    def __init__(self):
        MQTTTemplate.__init__(self)
        self.topic = get_topic("attendance")

    def publish_one(self, user_id, name, timestamp):
        message_data = {
            "message": name,
            "user": user_id,
            "time": timestamp  # Chỉ đến giây
        }
        message_json = json.dumps(message_data)
        self.publish_and_exit(self.topic, message_json, delay=0.1)
        print("Published: {} ({} at {})".format(name, user_id, timestamp))


def main():
    for person in ta:
        # Random từ 0 đến 30 phút
        minutes_offset = random.randint(0, 30)
        seconds_offset = random.randint(0, 59)

        arrival_time = start_time + timedelta(minutes=minutes_offset, seconds=seconds_offset)
        timestamp = arrival_time.strftime("%Y-%m-%d %H:%M:%S")  # BỎ MILIGIÂY

        publisher = AttendancePublisher()
        publisher.publish_one(person["id"], person["name"], timestamp)
        time.sleep(0.2)

    print("All attendance data published!")


if __name__ == "__main__":
    main()