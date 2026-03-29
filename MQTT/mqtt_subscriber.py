import paho.mqtt.client as mqtt
from PyQt6.QtCore import QThread

class MQTTSubscriberThread(QThread):
    def __init__(self, mqtt_host, mqtt_port, mqtt_topic="default/topic", mqtt_keepalive=60, mqtt_username=None, mqtt_password=None):
        super().__init__()
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.mqtt_topic = mqtt_topic
        self.mqtt_keepalive = mqtt_keepalive
        self.mqtt_username = mqtt_username
        self.mqtt_password = mqtt_password
        self.client = None
        self._stop_requested = False

    def on_connect(self, client, userdata, flags, rc):
        """Callback khi kết nối thành công"""
        if rc == 0:
            print(f"Connected to MQTT Broker at {self.mqtt_host}")
            client.subscribe(self.mqtt_topic)
            print(f"Subscribed to topic: {self.mqtt_topic}")
        else:
            print(f"Failed to connect to MQTT Broker. Return code: {rc}")

    def on_message(self, client, userdata, msg):
        """Callback khi nhận được message, sẽ được override bởi lớp con"""
        pass

    def on_disconnect(self, client, userdata, rc):
        """Callback khi ngắt kết nối"""
        print("Disconnected from MQTT Broker")

    def run(self):
        """Main thread execution"""
        try:
            self.client = mqtt.Client()
            
            # Set username and password if provided
            if self.mqtt_username and self.mqtt_password:
                self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
                print(f"MQTT authentication set for user: {self.mqtt_username}")
            
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.on_disconnect = self.on_disconnect
            self.client.connect(self.mqtt_host, self.mqtt_port, self.mqtt_keepalive)
            while not self._stop_requested:
                self.client.loop(timeout=1.0)
        except Exception as e:
            print(f"MQTT Thread error: {e}")
        finally:
            if self.client:
                self.client.disconnect()

    def stop(self):
        """Dừng thread"""
        self._stop_requested = True
        if self.client:
            self.client.disconnect()
        self.wait()