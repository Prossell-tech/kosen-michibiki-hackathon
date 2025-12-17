import net from "net";

const TCP_HOST = process.env.TCP_FORWARD_HOST || "localhost";
const TCP_PORT = Number(process.env.TCP_FORWARD_PORT || "8766");

export const runtime = "nodejs";

export async function GET(req: Request) {
  const encoder = new TextEncoder();
  let socket: net.Socket | null = null;
  let buffered = "";
  let aborted = false;
  let backoffMs = 500;

  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      const connect = () => {
        if (aborted) return;
        socket = net.createConnection({host: TCP_HOST, port: TCP_PORT});

        socket.on("connect", () => {
          backoffMs = 500;
        });

        socket.on("data", (chunk: Buffer) => {
          buffered += chunk.toString("utf-8");
          const lines = buffered.split(/\r?\n/);
          buffered = lines.pop() ?? "";
          for (const line of lines) {
            if (!line) continue;
            const payload = `data: ${line}\n\n`;
            controller.enqueue(encoder.encode(payload));
          }
        });

        const scheduleReconnect = () => {
          if (aborted) return;
          backoffMs = Math.min(backoffMs * 2, 10000);
          setTimeout(connect, backoffMs);
        };

        socket.on("error", () => {
          socket?.destroy();
          scheduleReconnect();
        });

        socket.on("close", () => {
          scheduleReconnect();
        });
      };

      connect();

      const abort = () => {
        aborted = true;
        socket?.destroy();
        try {
          controller.close();
        } catch (_) {
          /* noop */
        }
      };
      req.signal.addEventListener("abort", abort);
    },
    cancel() {
      socket?.destroy();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
