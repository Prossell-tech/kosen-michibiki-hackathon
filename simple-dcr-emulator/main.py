import asyncio
import websockets
from utils import open_serial, read_serial_line, select_dummy_qzqsm

HOST = "localhost"
PORT = 8765
WS_URI = f"ws://{HOST}:{PORT}"

SERIAL_PORT = "/dev/cu.usbserial-A101AVPA"
BAUDRATE = 115200

clients = set()

DUMMY_QZQSM = select_dummy_qzqsm()
print(f"Using dummy QZQSM: {DUMMY_QZQSM}")


async def handler(ws, path=None):
    clients.add(ws)
    peer = ws.remote_address
    print(f"[SERVER] Connection opened: {peer}")
    try:
        await ws.wait_closed()
    finally:
        clients.remove(ws)
        print(f"[SERVER] Connection closed: {peer}")


async def serial_reader():
    ser = open_serial(SERIAL_PORT, BAUDRATE)
    while True:
        line = await read_serial_line(ser)
        if not line:
            continue

        if clients:
            # NMEA行を送信
            tasks = [ws.send(line) for ws in clients]
            # ダミーQZQSM行を送信
            tasks += [ws.send(DUMMY_QZQSM) for ws in clients]
            await asyncio.gather(*tasks, return_exceptions=True)
            print(
                f"[SERIAL → WS] Sent NMEA and dummy QZQSM to {len(clients)} client(s):")
            print(line)
            print(DUMMY_QZQSM)


async def main():
    print(f"[MAIN] Starting server at {WS_URI}")
    server = await websockets.serve(handler, HOST, PORT)
    asyncio.create_task(serial_reader())
    await server.wait_closed()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[MAIN] Server stopped by user")
