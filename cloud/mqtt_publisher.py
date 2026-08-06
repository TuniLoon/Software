"""
mqtt_publisher.py
Publish telemetry data to MQTT cloud broker.
"""

import json
import time
import threading
from datetime import datetime
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("[ERROR] paho-mqtt not installed. Run: pip install paho-mqtt")
    sys.exit(1)

class MQTTPublisher:
    """Publish telemetry data to MQTT broker."""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or "config/cloud_config.json"
        self.load_config()
        
        self.client = None
        self.connected = False
        self.running = False
        self.packet_count = 0
    
    def load_config(self):
        """Load MQTT configuration."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                self.mqtt_config = config.get('mqtt', {})
                print(f"[INFO] MQTT config loaded from {self.config_path}")
        except Exception as e:
            print(f"[ERROR] Failed to load config: {e}")
            self.mqtt_config = {
                'broker': 'broker.hivemq.com',
                'port': 1883,
                'topic': 'tuniloon/telemetry'
            }
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback when connected to broker."""
        if rc == 0:
            self.connected = True
            print(f"[MQTT] Connected to {self.mqtt_config.get('broker')}")
        else:
            self.connected = False
            print(f"[MQTT] Connection failed with code {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from broker."""
        self.connected = False
        print("[MQTT] Disconnected from broker")
    
    def connect(self):
        """Connect to MQTT broker."""
        broker = self.mqtt_config.get('broker', 'broker.hivemq.com')
        port = self.mqtt_config.get('port', 1883)
        client_id = self.mqtt_config.get('client_id', 'tuniloon_groundstation')
        
        self.client = mqtt.Client(client_id=client_id)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        
        # Set credentials if provided
        username = self.mqtt_config.get('username', '')
        password = self.mqtt_config.get('password', '')
        if username and password:
            self.client.username_pw_set(username, password)
        
        try:
            self.client.connect(broker, port, keepalive=60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"[MQTT] Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        self.running = False
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
    
    def publish(self, data: dict) -> bool:
        """
        Publish telemetry data to MQTT broker.
        
        Args:
            data: Telemetry data dict
        
        Returns:
            True if published successfully
        """
        if not self.connected:
            return False
        
        try:
            topic = self.mqtt_config.get('topic', 'tuniloon/telemetry')
            
            # Add metadata
            payload = {
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            # Convert to JSON
            message = json.dumps(payload)
            
            # Publish
            result = self.client.publish(topic, message, qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.packet_count += 1
                if self.packet_count % 10 == 0:
                    print(f"[MQTT] Published {self.packet_count} packets to {topic}")
                return True
            else:
                print(f"[MQTT] Publish failed with code {result.rc}")
                return False
                
        except Exception as e:
            print(f"[MQTT] Publish error: {e}")
            return False
    
    def publish_loop(self, data_generator, interval: int = 1):
        """
        Continuously publish data from a generator.
        
        Args:
            data_generator: Function that yields telemetry data
            interval: Publish interval in seconds
        """
        self.running = True
        
        if not self.connect():
            print("[MQTT] Failed to connect. Exiting.")
            return
        
        print(f"[MQTT] Starting publish loop (interval: {interval}s)")
        
        try:
            while self.running:
                data = data_generator()
                if data:
                    self.publish(data)
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[MQTT] Stopped by user")
        finally:
            self.disconnect()


# Standalone test
if __name__ == "__main__":
    # Test the MQTT publisher with sample data
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    from payload_simulator.src.MockPayload import MockPayload
    
    print("=" * 60)
    print("  TuniLoon MQTT Publisher Test")
    print("=" * 60)
    print()
    
    # Create mock payload
    payload = MockPayload(continuous=True)
    payload.generate_flight()
    
    def get_data():
        data = payload.get_next_packet()
        if data:
            print(f"[TEST] Publishing: Alt={data['altitude']:.0f}m")
        return data
    
    # Create publisher and run
    publisher = MQTTPublisher()
    
    # Override config for testing
    publisher.mqtt_config = {
        'broker': 'broker.hivemq.com',
        'port': 1883,
        'topic': 'tuniloon/telemetry/test'
    }
    
    publisher.publish_loop(get_data, interval=1)
