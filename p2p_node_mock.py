import socket
import sys
import select
import random
import json

def main():
    if len(sys.argv) < 6:
        print("Usage: python p2p_node_mock.py [port_local_net] [remote_ip] [remote_port] [port_ipc_in] [port_ipc_out]")
        sys.exit(1)

    port_net = int(sys.argv[1])
    remote_ip = sys.argv[2]
    remote_port = int(sys.argv[3])
    port_ipc_in = int(sys.argv[4])
    port_ipc_out = int(sys.argv[5])

    sock_ipc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_ipc.bind(("127.0.0.1", port_ipc_in))

    sock_net = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_net.bind(("0.0.0.0", port_net))

    print("==================================================")
    print("  ROUTEUR P2P MOCK (PYTHON) - Mode secours sans GCC ")
    print("==================================================")
    print(f"  [IPC] Port locale   : {port_ipc_in} (In) / {port_ipc_out} (Out)")
    print(f"  [NET] Ecoute P2P    : {port_net}")
    print(f"  [NET] Destinataire  : {remote_ip}:{remote_port}")
    print("==================================================\n")

    while True:
        try:
            r, _, _ = select.select([sock_ipc, sock_net], [], [])
            for s in r:
                data, addr = s.recvfrom(65536)
                if s == sock_ipc:
                    sock_net.sendto(data, (remote_ip, remote_port))
                    sock_ipc.sendto(b'{"type": "ack", "status": "ok"}', addr)
                        
                elif s == sock_net:
                    sock_ipc.sendto(data, ("127.0.0.1", port_ipc_out))
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Erreur: {e}")

if __name__ == "__main__":
    main()
