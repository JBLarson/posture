import asyncio
import json
import math
import time
from collections import deque
from pathlib import Path
from bleak import BleakScanner, BleakClient
import struct

TARGET_NAME = "UprightGO2"
POSTURE_UUID = "0000bac4-0000-1000-8000-00805f9b34fb"
VIBRATE_UUID = "0000baa2-0000-1000-8000-00805f9b34fb"
CONFIG_FILE = "posture_config.json"

class PostureMonitor:
    def __init__(self):
        self.baseline = None
        self.recent_readings = deque(maxlen=10)  # 2-3 second smoothing at ~3Hz
        self.last_vibration = 0
        self.vibration_cooldown = 5  # seconds between vibrations
        self.load_config()
        
    def load_config(self):
        """Load calibration data from config file"""
        if Path(CONFIG_FILE).exists():
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                if 'baseline' in config:
                    self.baseline = tuple(config['baseline'])
                    print(f"Loaded baseline: {self.baseline}")
        
    def save_config(self):
        """Save calibration data to config file"""
        config = {'baseline': self.baseline}
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"Saved baseline to {CONFIG_FILE}")
    
    def decode_posture(self, data: bytes):
        """Decode raw posture data from device"""
        if len(data) != 6:
            return None
        x, y, z = struct.unpack("<hhh", data)
        return (x, y, z)
    
    def calculate_angle(self, current, baseline):
        """Calculate angle between current position and baseline using dot product"""
        # Convert to vectors
        curr_vec = [current[0], current[1], current[2]]
        base_vec = [baseline[0], baseline[1], baseline[2]]
        
        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(curr_vec, base_vec))
        
        # Calculate magnitudes
        curr_mag = math.sqrt(sum(x * x for x in curr_vec))
        base_mag = math.sqrt(sum(x * x for x in base_vec))
        
        # Avoid division by zero
        if curr_mag == 0 or base_mag == 0:
            return 0
            
        # Calculate angle in degrees
        cos_angle = dot_product / (curr_mag * base_mag)
        cos_angle = max(-1, min(1, cos_angle))  # Clamp to [-1, 1]
        angle_rad = math.acos(cos_angle)
        angle_deg = math.degrees(angle_rad)
        
        return angle_deg
    
    def get_posture_status(self, angle):
        """Classify posture based on angle from baseline"""
        if angle < 15:
            return "GOOD", "🟢"
        elif angle < 30:
            return "MILD_SLOUCH", "🟡"
        elif angle < 45:
            return "POOR", "🟠"
        else:
            return "VERY_POOR", "🔴"
    
    def get_smoothed_reading(self):
        """Get average of recent readings for noise reduction"""
        if not self.recent_readings:
            return None
            
        avg_x = sum(r[0] for r in self.recent_readings) / len(self.recent_readings)
        avg_y = sum(r[1] for r in self.recent_readings) / len(self.recent_readings)
        avg_z = sum(r[2] for r in self.recent_readings) / len(self.recent_readings)
        
        return (avg_x, avg_y, avg_z)
    
    async def calibrate(self, client):
        """Calibration mode - record baseline posture"""
        print("\n=== CALIBRATION MODE ===")
        print("Sit in your BEST posture now!")
        print("Keep this position steady for 30 seconds...")
        input("Press Enter when ready...")
        
        readings = []
        
        def collect_calibration(_, data):
            decoded = self.decode_posture(data)
            if decoded:
                readings.append(decoded)
                if len(readings) % 10 == 0:  # Progress indicator
                    print(f"Collected {len(readings)} samples...")
        
        await client.start_notify(POSTURE_UUID, collect_calibration)
        
        print("Recording baseline... hold your posture!")
        await asyncio.sleep(30)
        
        await client.stop_notify(POSTURE_UUID)
        
        if len(readings) < 50:  # Need decent sample size
            print("Not enough calibration data collected!")
            return False
            
        # Calculate average baseline
        avg_x = sum(r[0] for r in readings) / len(readings)
        avg_y = sum(r[1] for r in readings) / len(readings)
        avg_z = sum(r[2] for r in readings) / len(readings)
        
        self.baseline = (avg_x, avg_y, avg_z)
        self.save_config()
        
        print(f"\n✅ Calibration complete!")
        print(f"Baseline set to: x={avg_x:.1f}, y={avg_y:.1f}, z={avg_z:.1f}")
        print(f"Collected {len(readings)} samples")
        
        return True
    
    async def monitor_posture(self, client):
        """Main monitoring loop"""
        if not self.baseline:
            print("❌ No calibration data! Please calibrate first.")
            return
            
        print("\n=== POSTURE MONITORING ===")
        print("Monitoring your posture... Ctrl+C to quit")
        print(f"Baseline: x={self.baseline[0]:.1f}, y={self.baseline[1]:.1f}, z={self.baseline[2]:.1f}")
        print("-" * 60)
        
        async def handle_posture(_, data):
            decoded = self.decode_posture(data)
            if not decoded:
                return
                
            self.recent_readings.append(decoded)
            
            # Only analyze if we have enough recent data
            if len(self.recent_readings) < 5:
                return
                
            smoothed = self.get_smoothed_reading()
            angle = self.calculate_angle(smoothed, self.baseline)
            status, emoji = self.get_posture_status(angle)
            
            # Print status
            print(f"{emoji} {status:12} | Angle: {angle:5.1f}° | "
                  f"x={smoothed[0]:6.0f} y={smoothed[1]:6.0f} z={smoothed[2]:6.0f}")
            
            # Vibrate if slouching (with cooldown)
            current_time = time.time()
            if (status in ["POOR", "VERY_POOR"] and 
                current_time - self.last_vibration > self.vibration_cooldown):
                try:
                    await client.write_gatt_char(VIBRATE_UUID, b'\x01', response=True)
                    self.last_vibration = current_time
                    print("   📳 Posture reminder sent!")
                except Exception as e:
                    print(f"   ❌ Vibration failed: {e}")
        
        await client.start_notify(POSTURE_UUID, handle_posture)
        
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping posture monitoring...")
        finally:
            await client.stop_notify(POSTURE_UUID)

async def find_device():
    """Find and connect to UprightGO2 device"""
    print("Scanning for UprightGO2...")
    devices = await BleakScanner.discover(timeout=10.0)
    
    for device in devices:
        if device.name and TARGET_NAME.lower() in device.name.lower():
            print(f"Found: {device.name} ({device.address})")
            return device
    
    raise SystemExit("❌ UprightGO2 not found. Make sure device is on and nearby.")

async def main():
    monitor = PostureMonitor()
    device = await find_device()
    
    async with BleakClient(device) as client:
        print(f"Connected: {client.is_connected}")
        
        while True:
            print("\n" + "="*50)
            print("UPRIGHT GO2 POSTURE MONITOR")
            print("="*50)
            print("1. Calibrate (set baseline posture)")
            print("2. Monitor posture")
            print("3. Test vibration")
            print("4. Show current config")
            print("5. Quit")
            
            choice = input("\nChoice: ").strip()
            
            if choice == "1":
                await monitor.calibrate(client)
                
            elif choice == "2":
                await monitor.monitor_posture(client)
                
            elif choice == "3":
                try:
                    await client.write_gatt_char(VIBRATE_UUID, b'\x01', response=True)
                    print("📳 Test vibration sent!")
                except Exception as e:
                    print(f"❌ Vibration test failed: {e}")
                    
            elif choice == "4":
                if monitor.baseline:
                    print(f"Current baseline: x={monitor.baseline[0]:.1f}, "
                          f"y={monitor.baseline[1]:.1f}, z={monitor.baseline[2]:.1f}")
                else:
                    print("No calibration data found.")
                    
            elif choice == "5":
                break
                
            else:
                print("Invalid choice!")

if __name__ == "__main__":
    asyncio.run(main())
