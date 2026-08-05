"""
Receiver.py
Receive telemetry packets from payload (serial, UDP, or mock).
"""

import time
import threading
from typing import Optional, Callable
from pathlib import Path
import sys

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.Config import Config
from src.Decoder import TelemetryDecoder
from src.Logger import TelemetryLogger

class TelemetryReceiver:
    """Receive and process telemetry packets."""
    
    def __init__(self, config_path: str = None):
        self.config = Config(config_path)
        self.decoder = TelemetryDecoder()
        
        # Setup logger
        data_dir = self.config.get_data_dir()
        self.logger = TelemetryLogger(data_dir=data_dir)
        
        # Callbacks
        self.packet_callback = None
        self.error_callback = None
        
        # State
        self.is_running = False
        self.packet_count = 0
        self.error_count = 0
    
    def on_packet(self, callback: Callable):
        """Register callback for valid packets."""
        self.packet_callback = callback
    
    def on_error(self, callback: Callable):
        """Register callback for errors."""
        self.error_callback = callback
    
    def process_packet(self, raw_packet: str) -> bool:
        """
        Process a single packet.
        
        Args:
            raw_packet: Raw packet string
        
        Returns:
            True if packet was valid
        """
        # Decode the packet
        data = self.decoder.decode(raw_packet)
        
        if data is None:
            self.error_count += 1
            if self.error_callback:
                self.error_callback(raw_packet)
            return False
        
        # Log the data
        self.logger.log(data)
        self.packet_count += 1
        
        # Call the packet callback
        if self.packet_callback:
            self.packet_callback(data)
        
        return True
    
    def read_serial(self, com_port: str = None, baud: int = None):
        """
        Read from serial port.
        
        Args:
            com_port: COM port name (e.g., 'COM10' or '/dev/ttyUSB0')
            baud: Baud rate
        """
        try:
            import serial
        except ImportError:
            print("[ERROR] pyserial not installed. Run: pip install pyserial")
            return
        
        com_port = com_port or self.config.get_com_port()
        baud = baud or self.config.get_baud_rate()
        
        try:
            ser = serial.Serial(com_port, baud, timeout=1)
            print(f"[INFO] Connected to {com_port} at {baud} baud")
            self.is_running = True
            
            while self.is_running:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    self.process_packet(line)
            
            ser.close()
            
        except Exception as e:
            print(f"[ERROR] Serial error: {e}")
            self.is_running = False
    
    def read_udp(self, port: int = 5000):
        """Read from UDP socket."""
        import socket
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)
            sock.bind(('0.0.0.0', port))
            print(f"[INFO] Listening on UDP port {port}")
            self.is_running = True
            
            while self.is_running:
                try:
                    data, addr = sock.recvfrom(1024)
                    packet = data.decode('utf-8').strip()
                    if packet:
                        print(f"[INFO] Received from {addr}: {packet}")
                        self.process_packet(packet)
                except socket.timeout:
                    continue
            
            sock.close()
            
        except Exception as e:
            print(f"[ERROR] UDP error: {e}")
            self.is_running = False
    
    def read_mock(self, mock_payload, interval: int = 30):
        """
        Read from mock payload (for testing).
        
        Args:
            mock_payload: MockPayload instance
            interval: Polling interval
        """
        print("[INFO] Reading from mock payload")
        self.is_running = True
        
        while self.is_running:
            # This is a placeholder - in reality, mock payload would
            # be sending data via serial or UDP
            time.sleep(1)
    
    def stop(self):
        """Stop the receiver."""
        self.is_running = False
        print("[INFO] Receiver stopped")
    
    def get_stats(self) -> dict:
        """Get receiver statistics."""
        return {
            'packet_count': self.packet_count,
            'error_count': self.error_count,
            'log_stats': self.logger.get_stats()
        }
    
    def close(self):
        """Close resources."""
        self.logger.close()


if __name__ == "__main__":
    # Test the receiver
    print("[INFO] Starting receiver in test mode...")
    print("[INFO] This will look for packets on COM10 (default)")
    print("[INFO] Press Ctrl+C to stop")
    
    receiver = TelemetryReceiver()
    
    try:
        # In a real scenario, you would run this in a thread
        # receiver.read_serial()
        pass
    except KeyboardInterrupt:
        receiver.stop()
        receiver.close()
