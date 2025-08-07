import asyncio
from bleak import BleakScanner, BleakClient

TARGET_NAME = "UprightGO2"
TEST_UUID = "0000bae3-0000-1000-8000-00805f9b34fb"

# Test payloads (skipping 01)
PAYLOADS = [
    #b"\x01",
    #b"\x02",
    b"\x10",
    b"\x00",
    b"\xff",
    b"\x01\x00",
    b"\x02\x00",
    b"\x10\x00",
    b"\x0a",
    b"\x05"
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

        for payload in PAYLOADS:
            input(f"\nReady to test payload: {payload.hex()}\nPress Enter to send...")

            try:
                await client.write_gatt_char(TEST_UUID, payload, response=True)
                print("Write succeeded.")
            except Exception as e:
                print(f"Write failed: {e}")
                continue

            while True:
                response = input("Did it buzz? (y/n): ").strip().lower()
                if response in ["y", "n"]:
                    result = "BUZZED" if response == "y" else "no buzz"
                    print(f"Recorded: [{payload.hex()}] --> {result}")
                    break
                else:
                    print("Invalid input. Enter y or n.")

asyncio.run(main())
