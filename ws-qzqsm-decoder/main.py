#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import asyncio
import json
import sys
from datetime import date, datetime

import websockets
import azarashi

DEFAULT_WS_URI = "ws://localhost:8765"

RETRY_BASE_SEC = 1.0        # 再接続の初期待ち
RETRY_MAX_SEC = 30.0        # 再接続最大待ち
READ_TIMEOUT_SEC = 3600.0   # 受信が途絶した場合のタイムアウト

# パラメータ転送先
FORWARD_HOST = "localhost"
FORWARD_PORT = 8766

# QZQSMフィルタ


def is_qzqsm_line(s: str) -> bool:
    s = s.strip()
    return s.startswith("$QZQSM,")


def _json_default(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return str(obj)


async def start_azarashi() -> asyncio.subprocess.Process:
    proc = await asyncio.create_subprocess_exec(
        "azarashi", "nmea",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    print("[DECODER] started: `azarashi nmea`", file=sys.stderr)
    return proc


async def pump_qzqsm_to_decoder(queue: "asyncio.Queue[str]", proc: asyncio.subprocess.Process):
    assert proc.stdin is not None
    try:
        while True:
            line = await queue.get()
            data = (line.strip() + "\n").encode("utf-8", errors="replace")
            try:
                proc.stdin.write(data)
                await proc.stdin.drain()
            except (BrokenPipeError, ConnectionResetError) as e:
                print(f"[DECODER] stdin write failed: {e}", file=sys.stderr)
                break
            finally:
                queue.task_done()
    except asyncio.CancelledError:
        pass


async def read_decoder_stdout(proc: asyncio.subprocess.Process):
    assert proc.stdout is not None
    try:
        while True:
            line = await proc.stdout.readline()
            if not line:
                print("[DECODER] stdout closed.", file=sys.stderr)
                return
            sys.stdout.write(line.decode("utf-8", errors="replace"))
            sys.stdout.flush()
    except asyncio.CancelledError:
        pass


async def read_decoder_stderr(proc: asyncio.subprocess.Process):
    assert proc.stderr is not None
    try:
        while True:
            line = await proc.stderr.readline()
            if not line:
                return
            sys.stderr.write("[DECODER][stderr] " +
                             line.decode("utf-8", errors="replace"))
    except asyncio.CancelledError:
        pass


async def consume_websocket(ws_uri: str, queue: "asyncio.Queue[str]", params_queue: "asyncio.Queue[dict]"):
    backoff = RETRY_BASE_SEC
    while True:
        try:
            async with websockets.connect(ws_uri) as ws:
                peer = ws.remote_address
                print(f"[WS] connected to {peer} ({ws_uri})", file=sys.stderr)
                backoff = RETRY_BASE_SEC

                while True:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=READ_TIMEOUT_SEC)
                    except asyncio.TimeoutError:
                        raise RuntimeError("WebSocket receive timeout")

                    if isinstance(msg, bytes):
                        try:
                            msg = msg.decode("utf-8", errors="replace")
                        except Exception:
                            msg = str(msg)

                    for raw in msg.splitlines():
                        line = raw.strip()
                        if not line:
                            continue
                        if is_qzqsm_line(line):
                            try:
                                queue.put_nowait(line)
                            except asyncio.QueueFull:
                                try:
                                    _ = queue.get_nowait()
                                    queue.task_done()
                                except Exception:
                                    pass
                                queue.put_nowait(line)

                            # 解析して params を転送キューへ
                            try:
                                report = azarashi.decode(line, 'nmea')
                                params = report.get_params()
                                try:
                                    params_queue.put_nowait(params)
                                except asyncio.QueueFull:
                                    try:
                                        _ = params_queue.get_nowait()
                                        params_queue.task_done()
                                    except Exception:
                                        pass
                                    params_queue.put_nowait(params)
                            except Exception as e:
                                print(
                                    f"[DECODE] failed to decode line: {e}", file=sys.stderr)
        except (OSError, ConnectionError, websockets.ConnectionClosedError, websockets.InvalidStatusCode) as e:
            print(
                f"[WS] connection error: {e}. retrying in {backoff:.1f}s", file=sys.stderr)
        except Exception as e:
            print(
                f"[WS] unexpected error: {e}. retrying in {backoff:.1f}s", file=sys.stderr)

        await asyncio.sleep(backoff)
        backoff = min(backoff * 2.0, RETRY_MAX_SEC)


async def forward_params_server(params_queue: "asyncio.Queue[dict]"):
    clients: set[asyncio.StreamWriter] = set()
    lock = asyncio.Lock()

    async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        peer = writer.get_extra_info("peername")
        print(f"[FWD] client connected: {peer}", file=sys.stderr)
        async with lock:
            clients.add(writer)
        try:
            # クライアントからの入力は想定しないので、接続が切れるまで読み続ける
            while True:
                data = await reader.read(1024)
                if not data:
                    break
        except asyncio.CancelledError:
            pass
        finally:
            async with lock:
                clients.discard(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            print(f"[FWD] client disconnected: {peer}", file=sys.stderr)

    async def broadcast():
        while True:
            params = await params_queue.get()
            try:
                payload = (
                    json.dumps(params, ensure_ascii=False,
                               default=_json_default) + "\n"
                ).encode("utf-8")
                async with lock:
                    targets = list(clients)

                dead: list[asyncio.StreamWriter] = []
                for w in targets:
                    try:
                        w.write(payload)
                        await w.drain()
                    except Exception:
                        dead.append(w)

                if dead:
                    async with lock:
                        for w in dead:
                            clients.discard(w)
                            try:
                                w.close()
                                await w.wait_closed()
                            except Exception:
                                pass
            finally:
                params_queue.task_done()

    server = await asyncio.start_server(handle_client, FORWARD_HOST, FORWARD_PORT)
    sockets = server.sockets or []
    addrs = ", ".join(str(s.getsockname())
                      for s in sockets) if sockets else f"{FORWARD_HOST}:{FORWARD_PORT}"
    print(f"[FWD] serving on {addrs}", file=sys.stderr)

    async with server:
        await asyncio.gather(server.serve_forever(), broadcast())


async def main(ws_uri: str):
    q: asyncio.Queue[str] = asyncio.Queue(maxsize=512)
    params_q: asyncio.Queue[dict] = asyncio.Queue(maxsize=512)

    proc = await start_azarashi()

    tasks = [
        asyncio.create_task(pump_qzqsm_to_decoder(q, proc)),
        asyncio.create_task(read_decoder_stdout(proc)),
        asyncio.create_task(read_decoder_stderr(proc)),
        asyncio.create_task(consume_websocket(ws_uri, q, params_q)),
        asyncio.create_task(forward_params_server(params_q)),
    ]

    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for d in done:
            exc = d.exception()
            if exc:
                print(
                    f"[MAIN] task finished with error: {exc}", file=sys.stderr)
    finally:
        for t in tasks:
            t.cancel()
        try:
            if proc.stdin and not proc.stdin.at_eof():
                proc.stdin.close()
            await asyncio.wait_for(proc.wait(), timeout=3.0)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Decode QZQSM from WebSocket stream via `azarashi nmea`.")
    parser.add_argument("--ws", dest="ws_uri", default=DEFAULT_WS_URI,
                        help=f"WebSocket URI (default: {DEFAULT_WS_URI})")
    args = parser.parse_args()

    try:
        asyncio.run(main(args.ws_uri))
    except KeyboardInterrupt:
        print("\n[MAIN] stopped by user", file=sys.stderr)
