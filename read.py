import asyncio
from bleak import BleakScanner, BleakClient
import struct

TARGET_NAME = "UprightGO2"
POSTURE_UUID = "0000bac4-0000-1000-8000-00805f9b34fb"

def decode_posture(data: bytes):
    if len(data) != 6:
        return None
    # Interpret as 3 signed 16-bit integers (little-endian)
    x, y, z = struct.unpack("<hhh", data)
    return (x, y, z)

async def main():
    print("Scanning...")
    devices = await BleakScanner.discover(timeout=6.0)
    target = None
    for d in devices:
        if d.name and TARGET_NAME.lower() in d.name.lower():
            target = d
            break
    if not target:
        raise SystemExit("Device not found.")

    async with BleakClient(target) as client:
        print("Connected:", client.is_connected)

        def handle_posture(_, data: bytearray):
            decoded = decode_posture(data)
            if decoded:
                print(f"x={decoded[0]:>6}  y={decoded[1]:>6}  z={decoded[2]:>6}")

        await client.start_notify(POSTURE_UUID, handle_posture)
        print("Streaming posture data... (Ctrl+C to quit)")
        await asyncio.sleep(30)

        await client.stop_notify(POSTURE_UUID)

asyncio.run(main())
