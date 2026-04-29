import socket
import threading
from queue import Empty, Queue
from typing import Optional


class P2PClient:
    """Game-side TCP client that talks to the local C P2P node."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9001) -> None:
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.incoming_queue: "Queue[str]" = Queue()
        self._stop_event = threading.Event()
        self._rx_thread: Optional[threading.Thread] = None

    def connect(self) -> None:
        self.sock = socket.create_connection((self.host, self.port), timeout=10)
        self.sock.settimeout(None)

    def send_message(self, msg: str) -> None:
        """Send one newline-delimited text message."""
        if self.sock is None:
            raise RuntimeError("Socket is not connected")
        payload = (msg.rstrip("\n") + "\n").encode("utf-8")
        self.sock.sendall(payload)

    def receive_messages(self) -> None:
        """Continuously receive messages and enqueue complete lines."""
        if self.sock is None:
            return

        buffer = ""
        while not self._stop_event.is_set():
            try:
                data = self.sock.recv(4096)
            except OSError:
                break

            if not data:
                break

            buffer += data.decode("utf-8", errors="replace")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if line:
                    self.incoming_queue.put(line)

    def start_receiver_thread(self) -> None:
        if self.sock is None:
            raise RuntimeError("Call connect() before starting receiver")
        self._rx_thread = threading.Thread(target=self.receive_messages, daemon=True)
        self._rx_thread.start()

    def try_get_message(self) -> Optional[str]:
        try:
            return self.incoming_queue.get_nowait()
        except Empty:
            return None

    def close(self) -> None:
        self._stop_event.set()
        if self.sock is not None:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.sock.close()
            self.sock = None


def main() -> None:
    """Small manual test runner for this client."""
    client = P2PClient(host="127.0.0.1", port=9001)
    client.connect()
    client.start_receiver_thread()
    client.send_message("HELLO|python|game-client")

    print("Connected. Type protocol lines. 'quit' to exit.")
    try:
        while True:
            while True:
                msg = client.try_get_message()
                if msg is None:
                    break
                print(f"[NET] {msg}")

            line = input("> ").strip()
            if not line:
                continue
            if line.lower() == "quit":
                break
            client.send_message(line)
    finally:
        client.close()


if __name__ == "__main__":
    main()
