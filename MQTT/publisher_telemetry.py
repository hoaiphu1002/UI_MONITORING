#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import sys
import signal
from mqtt_publisher_config import MQTTTemplate, get_topic

def signal_handler(sig, frame):
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


class TelemetryPublisherOnce(MQTTTemplate):
    """
        {
            "imu": <int>,
            "odom": <int>,
            "send": <int>
        }
    """

    def __init__(self):
        MQTTTemplate.__init__(self)
        self.topic = get_topic("telemetry")

    def publish_telemetry(self, imu_pkts, odom_pkts, send_pkts):
        msg = {
            "imu": imu_pkts,
            "odom": odom_pkts,
            "send": send_pkts
        }
        self.publish_and_exit(self.topic, msg, delay=0.1)


def main():
    if len(sys.argv) < 4:
        return 1

    try:
        imu = int(sys.argv[1])
        odom = int(sys.argv[2])
        send = int(sys.argv[3])
        
    except Exception as e:
        print("Invalid arguments: {}".format(e))
        return 1

    pub = TelemetryPublisherOnce()
    pub.publish_telemetry(imu, odom, send)
    return 0


if __name__ == "__main__":
    sys.exit(main())
