import net from "net";

const TCP_HOST = process.env.TCP_FORWARD_HOST || "localhost";
const TCP_PORT = Number(process.env.TCP_FORWARD_PORT || "8766");

export const runtime = "nodejs";

export async function GET(req: Request) {
  const encoder = new TextEncoder();
  let socket: net.Socket | null = null;
  let buffered = "";

  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      socket = net.createConnection({host: TCP_HOST, port: TCP_PORT});

      socket.on("connect", () => {
        // noop; just keep connection
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

      socket.on("error", (err) => {
        controller.error(err);
      });

      socket.on("close", () => {
        controller.close();
      });

      const abort = () => {
        socket?.destroy();
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
