import asyncio
import time
import websockets
from utils import open_serial, read_serial_line, select_dummy_qzqsm

HOST = "localhost"
PORT = 8765
WS_URI = f"ws://{HOST}:{PORT}"

SERIAL_PORT = "/dev/cu.usbserial-A101AVPA"
BAUDRATE = 115200

DUMMY_INTERVAL = 1.0

clients: dict[websockets.WebSocketServerProtocol, asyncio.Queue[str]] = {}

DUMMY_QZQSM = select_dummy_qzqsm()
print(f"Using dummy QZQSM: {DUMMY_QZQSM}")


async def sender(ws: websockets.WebSocketServerProtocol, q: asyncio.Queue[str]):
    try:
        while True:
            msg = await q.get()
            try:
                await ws.send(msg)
            except Exception as e:
                print(f"[SENDER] send failed {ws.remote_address}: {e}")
                return
            finally:
                q.task_done()
    except asyncio.CancelledError:
        pass


async def handler(ws: websockets.WebSocketServerProtocol, path: str | None = None):
    q: asyncio.Queue[str] = asyncio.Queue(maxsize=256)
    clients[ws] = q
    tx_task = asyncio.create_task(sender(ws, q))

    peer = ws.remote_address
    print(f"[SERVER] Connection opened: {peer}")

    try:
        await ws.wait_closed()
    finally:
        tx_task.cancel()
        try:
            await tx_task
        except Exception:
            pass
        clients.pop(ws, None)
        print(f"[SERVER] Connection closed: {peer}")


def _normalize_line(line: str | bytes) -> str:
    if isinstance(line, (bytes, bytearray)):
        try:
            line = line.decode("utf-8", errors="replace")
        except Exception:
            line = str(line)
    return line.strip("\r\n")


async def broadcast(msgs: list[str]):
    for ws, q in list(clients.items()):
        for m in msgs:
            try:
                q.put_nowait(m)
            except asyncio.QueueFull:
                try:
                    _ = q.get_nowait()
                    q.task_done()
                except Exception:
                    pass
                try:
                    q.put_nowait(m)
                except Exception:
                    print(
                        f"[BROADCAST] queue saturated for {ws.remote_address}")


async def serial_reader():
    ser = open_serial(SERIAL_PORT, BAUDRATE)
    last_dummy_ts = 0.0

    while True:
        line = await read_serial_line(ser)
        if not line:
            continue

        norm = _normalize_line(line)
        if not norm:
            continue

        msgs = [norm]

        now = time.time()
        if now - last_dummy_ts >= DUMMY_INTERVAL:
            msgs.append(DUMMY_QZQSM)
            last_dummy_ts = now

        if clients:
            await broadcast(msgs)
            print(
                f"[SERIAL → WS] broadcast {len(msgs)} msg(s) to {len(clients)} client(s):")
            for m in msgs:
                print(m)


async def main():
    print(f"[MAIN] Starting server at {WS_URI}")
    async with websockets.serve(
        handler,
        HOST,
        PORT,
        max_queue=32,
        ping_interval=20,
        ping_timeout=20,
        close_timeout=5,
    ):

        sr_task = asyncio.create_task(serial_reader())

        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            pass
        finally:
            sr_task.cancel()
            try:
                await sr_task
            except Exception:
                pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[MAIN] Server stopped by user")
