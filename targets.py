import asyncio
from bleak import BleakScanner, BleakClient

TARGET_NAME = "UprightGO2"

# UUIDs we previously found to be writeable
KNOWN_WRITE_UUIDS = [
    "0000baa2-0000-1000-8000-00805f9b34fb",
    "0000bae3-0000-1000-8000-00805f9b34fb",
    "0000bae6-0000-1000-8000-00805f9b34fb",
    "0000bae7-0000-1000-8000-00805f9b34fb",
    "0000bae8-0000-1000-8000-00805f9b34fb",
    "0000bab3-0000-1000-8000-00805f9b34fb",
    "0000bab4-0000-1000-8000-00805f9b34fb",
    "0000bad3-0000-1000-8000-00805f9b34fb",
    "0000bad4-0000-1000-8000-00805f9b34fb"
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
        svcs = client.services
        all_chars = [char.uuid.lower() for service in svcs for char in service.characteristics]

        print("\n=== Available Characteristics ===")
        for uuid in all_chars:
            print(uuid)

        print("\n=== UUID Status ===")
        for uuid in KNOWN_WRITE_UUIDS:
            if uuid in all_chars:
                print(f"[FOUND]  {uuid}")
            else:
                print(f"[MISSING] {uuid}")

asyncio.run(main())
