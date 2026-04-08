import argparse
import socket
import threading
import time


def send_line(sock: socket.socket, line: str) -> None:
    """Send one newline-delimited protocol message."""
    payload = (line.rstrip("\n") + "\n").encode("utf-8")
    sock.sendall(payload)


def receiver_loop(sock: socket.socket, stop_event: threading.Event) -> None:
    """Receive text lines and print them as network updates."""
    buffer = ""
    try:
        while not stop_event.is_set():
            chunk = sock.recv(4096)
            if not chunk:
                print("[INFO] disconnected from relay")
                stop_event.set()
                break

            buffer += chunk.decode("utf-8", errors="replace")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if line:
                    print(f"[NET] {line}")
    except OSError as exc:
        print(f"[WARN] receiver stopped: {exc}")
        stop_event.set()


def run_script_mode(sock: socket.socket, name: str) -> None:
    """Send a tiny scripted message sequence for reproducible tests."""
    scripted_messages = [
        f"MOVE|{name}|10|5",
        f"ATTACK|{name}|enemy2",
        f"MOVE|{name}|12|7",
    ]
    for msg in scripted_messages:
        print(f"[SEND] {msg}")
        send_line(sock, msg)
        time.sleep(0.5)


def run_interactive_mode(sock: socket.socket, name: str, stop_event: threading.Event) -> None:
    """Read user input and forward each line to the relay server."""
    print("[INFO] Interactive mode")
    print("[INFO] Type protocol lines such as:")
    print(f"       MOVE|{name}|10|5")
    print(f"       ATTACK|{name}|enemy2")
    print("[INFO] Type 'quit' to exit")

    while not stop_event.is_set():
        try:
            line = input("> ").strip()
        except EOFError:
            break
        except KeyboardInterrupt:
            break

        if not line:
            continue
        if line.lower() == "quit":
            stop_event.set()
            break

        send_line(sock, line)


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple TCP client for relay testing")
    parser.add_argument("--host", default="127.0.0.1", help="Relay host")
    parser.add_argument("--port", type=int, default=9000, help="Relay port")
    parser.add_argument("--name", default="player1", help="Player/client name")
    parser.add_argument(
        "--script",
        action="store_true",
        help="Send a short scripted sequence then continue in interactive mode",
    )
    parser.add_argument(
        "--script-only",
        action="store_true",
        help="Send scripted messages and exit without entering interactive mode",
    )
    parser.add_argument(
        "--listen-seconds",
        type=float,
        default=0.0,
        help="Stay connected and only receive for N seconds before exiting",
    )
    args = parser.parse_args()

    stop_event = threading.Event()

    with socket.create_connection((args.host, args.port), timeout=10) as sock:
        sock.settimeout(None)
        print(f"[INFO] Connected to relay at {args.host}:{args.port}")

        send_line(sock, f"HELLO|python|{args.name}")

        receiver = threading.Thread(target=receiver_loop, args=(sock, stop_event), daemon=True)
        receiver.start()

        if args.script:
            run_script_mode(sock, args.name)

        if args.listen_seconds > 0:
            print(f"[INFO] listen-only mode for {args.listen_seconds:.1f}s")
            stop_event.wait(args.listen_seconds)
            stop_event.set()
            return

        if args.script_only:
            time.sleep(0.2)
            stop_event.set()
            return

        run_interactive_mode(sock, args.name, stop_event)
        stop_event.set()

    print("[INFO] client closed")


if __name__ == "__main__":
    main()
