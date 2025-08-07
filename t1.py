import asyncio
from bleak import BleakScanner, BleakClient

TARGET_NAME = "UprightGO2"
PAYLOADS = [b"\x01", b"\x01\x00"]

WRITE_UUIDS = [
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
#'''

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
        for uuid in WRITE_UUIDS:
            for payload in PAYLOADS:
                try:
                    await client.write_gatt_char(uuid, payload, response=True)
                    print(f"[OK] Write to {uuid} <- {payload.hex()}")
                except Exception as e:
                    print(f"[FAIL] Write to {uuid} <- {payload.hex()}  {e}")

asyncio.run(main())
