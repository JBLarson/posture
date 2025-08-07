import asyncio
from bleak import BleakClient, BleakScanner

TARGET_NAME = "UprightGO2"   # or substring like "UPRIGHT" if needed
SAFE_PROBES = [b"\x00", b"\x01"]

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
        print("Connected:", client.is_connected)
        svcs = client.services

        notify_chars = []
        write_chars = []

        for s in svcs:
            for c in s.characteristics:
                props = ",".join(c.properties)
                print(f"{c.uuid}  [{props}]")
                if "notify" in c.properties:
                    notify_chars.append(c)
                if "write" in c.properties or "write-without-response" in c.properties:
                    write_chars.append(c)

        # subscribe to all notifications
        def handler(uuid):
            def _cb(_, data):
                print(f"[NOTIFY {uuid}] {data.hex()}  ({len(data)} bytes)")
            return _cb

        for c in notify_chars:
            await client.start_notify(c.uuid, handler(c.uuid))

        # probe writable characteristics with tiny payloads
        for c in write_chars:
            for p in SAFE_PROBES:
                try:
                    await client.write_gatt_char(c.uuid, p, response=True)
                    print(f"[WRITE OK] {c.uuid} <- {p.hex()}")
                    await asyncio.sleep(0.3)
                except Exception as e:
                    print(f"[WRITE FAIL] {c.uuid} <- {p.hex()}  {e}")

        print("Listening for 10s...")
        await asyncio.sleep(10)

        for c in notify_chars:
            try:
                await client.stop_notify(c.uuid)
            except:
                pass

asyncio.run(main())
