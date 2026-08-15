import os
import json
import time
import ssl
import paho.mqtt.client as mqtt
from ground_station.src.config import config

class MQTTPublisher:
    def __init__(self):
        self.broker = config.MQTT_BROKER
        self.port = config.MQTT_PORT
        self.username = config.MQTT_USERNAME
        self.password = config.MQTT_PASSWORD
        self.topic = config.MQTT_TOPIC
        self.client_id = config.MQTT_CLIENT_ID
        self.client = None
        self.connected = False

    def connect(self):
        self.client = mqtt.Client(client_id=self.client_id)
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
        if config.MQTT_TLS:
            self.client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"[MQTT] Connection error: {e}")
            return False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            print(f"[MQTT] Connected to {self.broker}:{self.port} with TLS")
        else:
            self.connected = False
            print(f"[MQTT] Connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        print("[MQTT] Disconnected from broker")

    def publish(self, data):
        if not self.connected:
            return False
        try:
            payload = json.dumps({'timestamp': time.time(), 'data': data})
            result = self.client.publish(self.topic, payload, qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                return True
            else:
                print(f"[MQTT] Publish failed with code {result.rc}")
                return False
        except Exception as e:
            print(f"[MQTT] Publish error: {e}")
            return False

    def disconnect(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
