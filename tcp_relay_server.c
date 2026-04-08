#define _WINSOCK_DEPRECATED_NO_WARNINGS
#define FD_SETSIZE 1024

#include <winsock2.h>
#include <ws2tcpip.h>

#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _MSC_VER
#pragma comment(lib, "Ws2_32.lib")
#endif

#define MAX_CLIENTS FD_SETSIZE
#define RECV_CHUNK 1024
#define LINE_BUFFER 8192

typedef struct Client {
    SOCKET socket;
    char addr_text[64];
    char buffer[LINE_BUFFER];
    int buffer_len;
    bool active;
} Client;

static int g_client_count = 0;

static void close_client(Client *c) {
    if (!c->active) {
        return;
    }

    closesocket(c->socket);
    c->active = false;
    c->buffer_len = 0;
    c->addr_text[0] = '\0';
    g_client_count--;
}

static int send_all(SOCKET s, const char *data, int len) {
    int total = 0;
    while (total < len) {
        int sent = send(s, data + total, len - total, 0);
        if (sent == SOCKET_ERROR) {
            return SOCKET_ERROR;
        }
        total += sent;
    }
    return total;
}

static void broadcast_line(Client clients[], int sender_index, const char *line, int line_len) {
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (!clients[i].active) {
            continue;
        }
        if (i == sender_index) {
            continue;
        }

        if (send_all(clients[i].socket, line, line_len) == SOCKET_ERROR) {
            printf("[WARN] send failed to %s, dropping client\n", clients[i].addr_text);
            close_client(&clients[i]);
        }
    }
}

static void handle_complete_line(Client clients[], int sender_index, const char *line, int line_len) {
    printf("[RECV] %s -> %.*s", clients[sender_index].addr_text, line_len - 1, line);
    broadcast_line(clients, sender_index, line, line_len);
}

static void process_incoming_bytes(Client clients[], int sender_index, const char *data, int data_len) {
    Client *sender = &clients[sender_index];

    for (int i = 0; i < data_len; i++) {
        char ch = data[i];

        if (sender->buffer_len >= LINE_BUFFER - 1) {
            printf("[WARN] line too long from %s, dropping partial line\n", sender->addr_text);
            sender->buffer_len = 0;
        }

        sender->buffer[sender->buffer_len++] = ch;

        if (ch == '\n') {
            sender->buffer[sender->buffer_len] = '\0';
            handle_complete_line(clients, sender_index, sender->buffer, sender->buffer_len);
            sender->buffer_len = 0;
        }
    }
}

static bool init_winsock(void) {
    WSADATA wsa_data;
    int result = WSAStartup(MAKEWORD(2, 2), &wsa_data);
    if (result != 0) {
        printf("[ERROR] WSAStartup failed: %d\n", result);
        return false;
    }
    return true;
}

static SOCKET create_listen_socket(unsigned short port) {
    SOCKET listen_sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (listen_sock == INVALID_SOCKET) {
        printf("[ERROR] socket failed: %d\n", WSAGetLastError());
        return INVALID_SOCKET;
    }

    BOOL opt = TRUE;
    if (setsockopt(listen_sock, SOL_SOCKET, SO_REUSEADDR, (const char *)&opt, sizeof(opt)) == SOCKET_ERROR) {
        printf("[WARN] setsockopt SO_REUSEADDR failed: %d\n", WSAGetLastError());
    }

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(port);

    if (bind(listen_sock, (struct sockaddr *)&addr, sizeof(addr)) == SOCKET_ERROR) {
        printf("[ERROR] bind failed: %d\n", WSAGetLastError());
        closesocket(listen_sock);
        return INVALID_SOCKET;
    }

    if (listen(listen_sock, SOMAXCONN) == SOCKET_ERROR) {
        printf("[ERROR] listen failed: %d\n", WSAGetLastError());
        closesocket(listen_sock);
        return INVALID_SOCKET;
    }

    return listen_sock;
}

static void accept_client(SOCKET listen_sock, Client clients[]) {
    struct sockaddr_in addr;
    int addr_len = sizeof(addr);
    SOCKET client_sock = accept(listen_sock, (struct sockaddr *)&addr, &addr_len);
    if (client_sock == INVALID_SOCKET) {
        printf("[WARN] accept failed: %d\n", WSAGetLastError());
        return;
    }

    int slot = -1;
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (!clients[i].active) {
            slot = i;
            break;
        }
    }

    if (slot < 0) {
        printf("[WARN] max clients reached, rejecting new connection\n");
        closesocket(client_sock);
        return;
    }

    clients[slot].socket = client_sock;
    clients[slot].active = true;
    clients[slot].buffer_len = 0;
    _snprintf_s(clients[slot].addr_text, sizeof(clients[slot].addr_text), _TRUNCATE, "%s:%u", inet_ntoa(addr.sin_addr), ntohs(addr.sin_port));
    g_client_count++;

    printf("[INFO] client connected: %s (total=%d)\n", clients[slot].addr_text, g_client_count);
}

static void run_server_loop(SOCKET listen_sock) {
    Client *clients = (Client *)calloc(MAX_CLIENTS, sizeof(Client));
    if (clients == NULL) {
        printf("[ERROR] could not allocate client table\n");
        return;
    }

    printf("[INFO] relay running. Messages are newline-delimited text.\n");
    printf("[INFO] Example: MOVE|player1|10|5\n");
    printf("[INFO] Press Ctrl+C to stop.\n");

    while (1) {
        fd_set read_set;
        FD_ZERO(&read_set);
        FD_SET(listen_sock, &read_set);
        SOCKET max_fd = listen_sock;

        for (int i = 0; i < MAX_CLIENTS; i++) {
            if (clients[i].active) {
                FD_SET(clients[i].socket, &read_set);
                if (clients[i].socket > max_fd) {
                    max_fd = clients[i].socket;
                }
            }
        }

        int ready = select((int)(max_fd + 1), &read_set, NULL, NULL, NULL);
        if (ready == SOCKET_ERROR) {
            printf("[ERROR] select failed: %d\n", WSAGetLastError());
            break;
        }

        if (FD_ISSET(listen_sock, &read_set)) {
            accept_client(listen_sock, clients);
        }

        for (int i = 0; i < MAX_CLIENTS; i++) {
            if (!clients[i].active) {
                continue;
            }
            if (!FD_ISSET(clients[i].socket, &read_set)) {
                continue;
            }

            char recv_buf[RECV_CHUNK];
            int received = recv(clients[i].socket, recv_buf, sizeof(recv_buf), 0);

            if (received == 0) {
                printf("[INFO] client disconnected: %s\n", clients[i].addr_text);
                close_client(&clients[i]);
                continue;
            }

            if (received == SOCKET_ERROR) {
                printf("[WARN] recv error from %s: %d\n", clients[i].addr_text, WSAGetLastError());
                close_client(&clients[i]);
                continue;
            }

            process_incoming_bytes(clients, i, recv_buf, received);
        }
    }

    for (int i = 0; i < MAX_CLIENTS; i++) {
        close_client(&clients[i]);
    }

    free(clients);
}

int main(int argc, char *argv[]) {
    unsigned short port = 9000;

    if (argc >= 2) {
        int parsed = atoi(argv[1]);
        if (parsed <= 0 || parsed > 65535) {
            printf("Usage: %s [port]\n", argv[0]);
            return 1;
        }
        port = (unsigned short)parsed;
    }

    if (!init_winsock()) {
        return 1;
    }

    SOCKET listen_sock = create_listen_socket(port);
    if (listen_sock == INVALID_SOCKET) {
        WSACleanup();
        return 1;
    }

    printf("[INFO] listening on 0.0.0.0:%u\n", port);
    run_server_loop(listen_sock);

    closesocket(listen_sock);
    WSACleanup();
    return 0;
}
