import os
import socket
import struct
import threading
from queue import Empty, Queue
from typing import Optional

class P2PIPCClient:
    """Python-side IPC client to talk to the local C P2P network node."""

    def __init__(self, player_id: str, ipc_path: Optional[str] = None) -> None:
        self.player_id = player_id
        self.ipc_path = ipc_path or self._default_ipc_path(player_id)
        self.sock: Optional[socket.socket] = None
        self.incoming_queue: "Queue[str]" = Queue()
        self._stop_event = threading.Event()
        self._rx_thread: Optional[threading.Thread] = None

    def _default_ipc_path(self, player_id: str) -> str:
        if os.name == "nt":
            return r"\\.\pipe\p2p_game_%s" % player_id
        return f"/tmp/p2p_game_{player_id}.sock"

    def connect(self, timeout: float = 10.0) -> None:
        if self.sock is not None:
            return

        if os.name == "nt":
            raise RuntimeError("Windows named pipe support is not implemented in this client yet")

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect(self.ipc_path)
        self.sock.settimeout(None)

    def close(self) -> None:
        self._stop_event.set()
        if self.sock is not None:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.sock.close()
            self.sock = None

    def send_message(self, msg: str) -> None:
        if self.sock is None:
            raise RuntimeError("IPC socket is not connected")

        payload = msg.encode("utf-8")
        header = struct.pack("!I", len(payload))
        self.sock.sendall(header + payload)

    def _receive_messages(self) -> None:
        if self.sock is None:
            return

        buffer = b""
        while not self._stop_event.is_set():
            try:
                data = self.sock.recv(4096)
            except OSError:
                break

            if not data:
                break

            buffer += data
            while len(buffer) >= 4:
                length = struct.unpack("!I", buffer[:4])[0]
                if len(buffer) < 4 + length:
                    break

                payload = buffer[4 : 4 + length]
                buffer = buffer[4 + length :]
                try:
                    text = payload.decode("utf-8")
                except UnicodeDecodeError:
                    text = payload.decode("utf-8", errors="replace")
                self.incoming_queue.put(text)

    def start_receiver_thread(self) -> None:
        if self.sock is None:
            raise RuntimeError("Call connect() before starting receiver")
        self._rx_thread = threading.Thread(target=self._receive_messages, daemon=True)
        self._rx_thread.start()

    def try_get_message(self) -> Optional[str]:
        try:
            return self.incoming_queue.get_nowait()
        except Empty:
            return None


def main() -> None:
    client = P2PIPCClient(player_id="player_a")
    client.connect()
    client.start_receiver_thread()
    print("Connected to IPC server. Type commands, 'quit' to exit.")

    try:
        while True:
            while True:
                msg = client.try_get_message()
                if msg is None:
                    break
                print(f"[IPC IN] {msg}")

            user_input = input("> ").strip()
            if not user_input:
                continue
            if user_input.lower() == "quit":
                break
            client.send_message(user_input)
    finally:
        client.close()


if __name__ == "__main__":
    main()
