"""
network_ipc.py — Pont de communication Python <-> C
Fournit une interface pour envoyer et recevoir des données via le routeur C.
"""

import socket
import json
import select

class IPCClient:
    def __init__(self, ip="127.0.0.1", port_in=5000, port_out=5001):
        self.ip = ip
        self.port_in = port_in   # Port d'entrée du routeur C
        self.port_out = port_out # Port de sortie (notre écoute)
        self.buffer_size = 65536
        
        # Socket pour l'envoi
        self.sock_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Socket pour la réception (bindé sur PORT_IPC_OUT)
        self.sock_in = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_in.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock_in.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65535)
        self.sock_out.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65535)
        try:
            self.sock_in.bind((self.ip, self.port_out))
            self.sock_in.setblocking(False)
            print(f"[IPC] Listening for C updates on {self.ip}:{self.port_out}")
        except Exception as e:
            print(f"[IPC] Warning: Could not bind to {self.ip}:{self.port_out}: {e}")

    def send(self, data: dict):
        """Sérialise et envoie un dictionnaire au processus C."""
        try:
            payload = json.dumps(data).encode("utf-8")
            self.sock_out.sendto(payload, (self.ip, self.port_in))
        except Exception as e:
            print(f"[IPC] Error sending data: {e}")

    def receive(self):
        """
        Tente de lire un message JSON depuis le processus C.
        Retourne le dictionnaire ou None s'il n'y a rien.
        """
        try:
            # Vérifier s'il y a des données sans bloquer
            ready = select.select([self.sock_in], [], [], 0)
            if ready[0]:
                data, addr = self.sock_in.recvfrom(self.buffer_size)
                return json.loads(data.decode("utf-8"))
        except (socket.error, json.JSONDecodeError, UnicodeDecodeError):
            pass
        return None

    def close(self):
        self.sock_in.close()
        self.sock_out.close()

# Pour le test unitaire
if __name__ == "__main__":
    client = IPCClient()
    print("Envoi d'un test...")
    client.send({"type": "test", "content": "hello world"})
    client.close()
