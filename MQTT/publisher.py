# Import package
import paho.mqtt.client as mqtt
import json
import time
import threading

# Define Variables
MQTT_HOST = "45.117.177.157" #"192.168.0.130" #"192.168.0.200"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 5
MQTT_USERNAME = "usname"
MQTT_PASSWORD = "passwd"
MQTT_TOPIC = "robot/attendance"
MQTT_MSG = "Ky"

# Define on_connect event Handler
def on_connect(mosq, obj, rc):
	print ("Connected to MQTT Broker")

# Define on_publish event Handler
def on_publish(client, userdata, mid):
	print ("Message Published...")

# Initiate MQTT Client
mqttc = mqtt.Client()

# Set authentication
mqttc.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

# Register Event Handlers
mqttc.on_publish = on_publish
mqttc.on_connect = on_connect

# Connect with MQTT Broker
mqttc.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL) 

'''# Publish message to MQTT Topic 
mqttc.publish(MQTT_TOPIC,MQTT_MSG)

# Disconnect from MQTT_Broker
mqttc.disconnect()'''


BATTERY_TOPIC = "robot/battery"
ATTENDANCE_TOPIC = "robot/attendance"
ATTENDANCE_LIST = ["Phu", "Ky", "Duy", "Thu", "Loi", "Thien"]

# ---------- Thread 1: Battery ----------
def publish_battery(stop_event):
    battery = 88
    while battery >= 0 and not stop_event.is_set():
        msg = json.dumps({"battery": battery})
        mqttc.publish(BATTERY_TOPIC, msg)
        print(f"[Battery] Sent: {msg}")
        battery -= 1
        time.sleep(1)
        
# ---------- Thread 2: Attendance ----------
def publish_attendance(stop_event):
    while not stop_event.is_set():
        for name in ATTENDANCE_LIST:
            if stop_event.is_set():
                break
            msg = json.dumps({
                "name": name,
                "time": time.strftime("%H:%M:%S")
            })
            mqttc.publish(ATTENDANCE_TOPIC, msg)
            print(f"[Attendance] Sent: {msg}")
            time.sleep(5)
            
# ---------- Start threads ----------
stop_event = threading.Event()

battery_thread = threading.Thread(target=publish_battery, args=(stop_event,))
attendance_thread = threading.Thread(target=publish_attendance, args=(stop_event,))

try:
    battery_thread.start()
    attendance_thread.start()

    battery_thread.join()
    attendance_thread.join()

except KeyboardInterrupt:
    print("\n❌ Đã dừng bằng Ctrl+C, đang thoát...")
    stop_event.set()
    battery_thread.join()
    attendance_thread.join()
    mqttc.disconnect()
    print("✅ MQTT client đã ngắt kết nối an toàn.")