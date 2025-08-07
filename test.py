import asyncio
from bleak import BleakScanner, BleakClient

# UUIDs for posture stream and vibration command
POSTURE_UUID = "0000bac4-0000-1000-8000-00805f9b34fb"
VIBRATE_UUID = "0000baa2-0000-1000-8000-00805f9b34fb"
TARGET_NAME = "UprightGO2"

def decode_posture(data: bytes):
    return {
        "raw_hex": data.hex(),
        "byte_values": list(data),
    }

async def main():
    print("Scanning...")
    devices = await BleakScanner.discover(timeout=6.0)
    target = None
    for d in devices:
        if d.name and TARGET_NAME.lower() in d.name.lower():
            target = d
            break
    if not target:
        raise SystemExit("Device not found. Check name or wake the device.")

    async with BleakClient(target) as client:
        print(f"Connected: {client.is_connected}")

        def handle_posture(_, data: bytearray):
            decoded = decode_posture(data)
            print(f"[POSTURE] {decoded}")

        await client.start_notify(POSTURE_UUID, handle_posture)
        print("Subscribed to posture updates...")

        try:
            await client.write_gatt_char(VIBRATE_UUID, b'\x01', response=True)
            print("Sent vibration command.")
        except Exception as e:
            print(f"Vibration write failed: {e}")

        print("\nDID THE DEVICE BUZZ? (y/n): ", end="")
        buzzed = input().strip().lower()
        if buzzed == 'y':
            print("✓ Confirmed: Vibration UUID works.")
        else:
            print("✗ No buzz — may need a different payload or characteristic.")

        print("Listening to posture updates for 20 seconds...")
        await asyncio.sleep(20)
        await client.stop_notify(POSTURE_UUID)

asyncio.run(main())
