#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import asyncio
import sys
from typing import Optional

import websockets

DEFAULT_WS_URI = "ws://localhost:8765"

RETRY_BASE_SEC = 1.0        # 再接続の初期待ち
RETRY_MAX_SEC = 30.0        # 再接続最大待ち
READ_TIMEOUT_SEC = 3600.0   # 受信が途絶した場合のタイムアウト

# QZQSMフィルタ


def is_qzqsm_line(s: str) -> bool:
    s = s.strip()
    return s.startswith("$QZQSM,")


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


async def consume_websocket(ws_uri: str, queue: "asyncio.Queue[str]"):
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
        except (OSError, ConnectionError, websockets.ConnectionClosedError, websockets.InvalidStatusCode) as e:
            print(
                f"[WS] connection error: {e}. retrying in {backoff:.1f}s", file=sys.stderr)
        except Exception as e:
            print(
                f"[WS] unexpected error: {e}. retrying in {backoff:.1f}s", file=sys.stderr)

        await asyncio.sleep(backoff)
        backoff = min(backoff * 2.0, RETRY_MAX_SEC)


async def main(ws_uri: str):
    q: asyncio.Queue[str] = asyncio.Queue(maxsize=512)

    proc = await start_azarashi()

    tasks = [
        asyncio.create_task(pump_qzqsm_to_decoder(q, proc)),
        asyncio.create_task(read_decoder_stdout(proc)),
        asyncio.create_task(read_decoder_stderr(proc)),
        asyncio.create_task(consume_websocket(ws_uri, q)),
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
