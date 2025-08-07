import asyncio
from bleak import BleakScanner, BleakClient
import time

TARGET_NAME = "UprightGO2"
UUID = "0000bae3-0000-1000-8000-00805f9b34fb"

# Known buzz-on command
BUZZ_ON = b"\x01"

# Candidates to stop the buzz
STOP_ATTEMPTS = [
    (b"\x01", "duplicate (b'\\x01')"),
    (b"\x00", "stop guess (b'\\x00')"),
    (b"\xff", "stop guess (b'\\xff')")
]

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

        for stop_value, label in STOP_ATTEMPTS:
            print(f"\nTesting buzz followed by: {label}")
            try:
                await client.write_gatt_char(UUID, BUZZ_ON, response=True)
                print("Sent buzz-on command.")
            except Exception as e:
                print(f"Buzz-on write failed: {e}")
                continue

            await asyncio.sleep(1.0)

            try:
                await client.write_gatt_char(UUID, stop_value, response=True)
                print(f"Sent stop command: {label}")
            except Exception as e:
                print(f"Stop write failed: {e}")

            print("Wait 10 seconds before next test...")
            await asyncio.sleep(10.0)

asyncio.run(main())
