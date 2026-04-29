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

#define RECV_CHUNK 2048
#define INITIAL_LINE_CAP 1024

typedef struct Connection {
    SOCKET socket;
    char label[64];
    char *line_buffer;
    size_t line_len;
    size_t line_cap;
} Connection;

typedef struct ConnectionList {
    Connection *items;
    size_t count;
    size_t cap;
} ConnectionList;

static bool init_winsock(void) {
    WSADATA wsa_data;
    int result = WSAStartup(MAKEWORD(2, 2), &wsa_data);
    if (result != 0) {
        printf("[ERROR] WSAStartup failed: %d\n", result);
        return false;
    }
    return true;
}

static bool parse_port(const char *text, unsigned short *port_out) {
    long value = strtol(text, NULL, 10);
    if (value <= 0 || value > 65535) {
        return false;
    }
    *port_out = (unsigned short)value;
    return true;
}

static bool parse_peer_target(const char *peer, char *ip_out, size_t ip_out_size, unsigned short *port_out) {
    const char *sep = strrchr(peer, ':');
    if (sep == NULL) {
        return false;
    }

    size_t ip_len = (size_t)(sep - peer);
    if (ip_len == 0 || ip_len >= ip_out_size) {
        return false;
    }

    memcpy(ip_out, peer, ip_len);
    ip_out[ip_len] = '\0';

    return parse_port(sep + 1, port_out);
}

static bool ensure_connection_capacity(ConnectionList *list) {
    if (list->count < list->cap) {
        return true;
    }

    size_t next_cap = (list->cap == 0) ? 16 : list->cap * 2;
    Connection *next = (Connection *)realloc(list->items, next_cap * sizeof(Connection));
    if (next == NULL) {
        return false;
    }

    list->items = next;
    list->cap = next_cap;
    return true;
}

static bool append_connection(ConnectionList *list, SOCKET sock, const char *label) {
    if (!ensure_connection_capacity(list)) {
        return false;
    }

    Connection *c = &list->items[list->count];
    c->socket = sock;
    c->line_cap = INITIAL_LINE_CAP;
    c->line_len = 0;
    c->line_buffer = (char *)malloc(c->line_cap);
    if (c->line_buffer == NULL) {
        return false;
    }
    c->line_buffer[0] = '\0';
    _snprintf_s(c->label, sizeof(c->label), _TRUNCATE, "%s", label);

    list->count++;
    return true;
}

static void remove_connection(ConnectionList *list, size_t index) {
    if (index >= list->count) {
        return;
    }

    Connection *c = &list->items[index];
    printf("[INFO] disconnected: %s\n", c->label);
    closesocket(c->socket);
    free(c->line_buffer);

    if (index != list->count - 1) {
        list->items[index] = list->items[list->count - 1];
    }
    list->count--;
}

static int send_all(SOCKET sock, const char *data, int len) {
    int sent_total = 0;
    while (sent_total < len) {
        int sent_now = send(sock, data + sent_total, len - sent_total, 0);
        if (sent_now == SOCKET_ERROR) {
            return SOCKET_ERROR;
        }
        sent_total += sent_now;
    }
    return sent_total;
}

static void broadcast_message(ConnectionList *list, size_t sender_index, const char *line, int line_len) {
    size_t i = 0;
    while (i < list->count) {
        if (i == sender_index) {
            i++;
            continue;
        }

        Connection *peer = &list->items[i];
        if (send_all(peer->socket, line, line_len) == SOCKET_ERROR) {
            printf("[WARN] send failed to %s (err=%d)\n", peer->label, WSAGetLastError());
            remove_connection(list, i);
            if (sender_index == list->count) {
                break;
            }
            if (i < sender_index) {
                sender_index--;
            }
            continue;
        }
        i++;
    }
}

static bool grow_line_buffer(Connection *c) {
    size_t next_cap = c->line_cap * 2;
    char *next = (char *)realloc(c->line_buffer, next_cap);
    if (next == NULL) {
        return false;
    }
    c->line_buffer = next;
    c->line_cap = next_cap;
    return true;
}

static bool handle_incoming_data(ConnectionList *list, size_t sender_index, const char *data, int len) {
    Connection *sender = &list->items[sender_index];

    for (int i = 0; i < len; i++) {
        char ch = data[i];

        if (sender->line_len + 1 >= sender->line_cap) {
            if (!grow_line_buffer(sender)) {
                printf("[ERROR] out of memory growing line buffer for %s\n", sender->label);
                return false;
            }
        }

        sender->line_buffer[sender->line_len++] = ch;

        if (ch == '\n') {
            sender->line_buffer[sender->line_len] = '\0';
            printf("[RECV] %s -> %s", sender->label, sender->line_buffer);
            broadcast_message(list, sender_index, sender->line_buffer, (int)sender->line_len);
            sender->line_len = 0;
        }
    }

    return true;
}

static SOCKET init_server(unsigned short listen_port) {
    SOCKET listen_sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (listen_sock == INVALID_SOCKET) {
        printf("[ERROR] socket failed: %d\n", WSAGetLastError());
        return INVALID_SOCKET;
    }

    BOOL opt = TRUE;
    if (setsockopt(listen_sock, SOL_SOCKET, SO_REUSEADDR, (const char *)&opt, sizeof(opt)) == SOCKET_ERROR) {
        printf("[WARN] SO_REUSEADDR failed: %d\n", WSAGetLastError());
    }

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(listen_port);

    if (bind(listen_sock, (struct sockaddr *)&addr, sizeof(addr)) == SOCKET_ERROR) {
        printf("[ERROR] bind failed on port %u (err=%d)\n", listen_port, WSAGetLastError());
        closesocket(listen_sock);
        return INVALID_SOCKET;
    }

    if (listen(listen_sock, SOMAXCONN) == SOCKET_ERROR) {
        printf("[ERROR] listen failed (err=%d)\n", WSAGetLastError());
        closesocket(listen_sock);
        return INVALID_SOCKET;
    }

    return listen_sock;
}

static bool accept_new_connection(SOCKET listen_sock, ConnectionList *list) {
    struct sockaddr_in addr;
    int addr_len = sizeof(addr);
    SOCKET incoming = accept(listen_sock, (struct sockaddr *)&addr, &addr_len);
    if (incoming == INVALID_SOCKET) {
        printf("[WARN] accept failed (err=%d)\n", WSAGetLastError());
        return false;
    }

    char label[64];
    _snprintf_s(label, sizeof(label), _TRUNCATE, "%s:%u", inet_ntoa(addr.sin_addr), ntohs(addr.sin_port));

    if (!append_connection(list, incoming, label)) {
        printf("[ERROR] cannot track new connection %s\n", label);
        closesocket(incoming);
        return false;
    }

    printf("[INFO] accepted connection: %s (total=%llu)\n", label, (unsigned long long)list->count);
    return true;
}

static bool connect_to_peer(ConnectionList *list, const char *ip, unsigned short port) {
    SOCKET sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET) {
        printf("[WARN] socket() failed for peer %s:%u\n", ip, port);
        return false;
    }

    struct sockaddr_in peer_addr;
    memset(&peer_addr, 0, sizeof(peer_addr));
    peer_addr.sin_family = AF_INET;
    peer_addr.sin_port = htons(port);

    if (inet_pton(AF_INET, ip, &peer_addr.sin_addr) != 1) {
        printf("[WARN] invalid peer address: %s\n", ip);
        closesocket(sock);
        return false;
    }

    if (connect(sock, (struct sockaddr *)&peer_addr, sizeof(peer_addr)) == SOCKET_ERROR) {
        printf("[WARN] connect failed to %s:%u (err=%d)\n", ip, port, WSAGetLastError());
        closesocket(sock);
        return false;
    }

    char label[64];
    _snprintf_s(label, sizeof(label), _TRUNCATE, "%s:%u", ip, port);

    if (!append_connection(list, sock, label)) {
        printf("[ERROR] cannot track outbound peer %s\n", label);
        closesocket(sock);
        return false;
    }

    printf("[INFO] connected to peer: %s (total=%llu)\n", label, (unsigned long long)list->count);
    return true;
}

static void free_connection_list(ConnectionList *list) {
    for (size_t i = 0; i < list->count; i++) {
        closesocket(list->items[i].socket);
        free(list->items[i].line_buffer);
    }
    free(list->items);
    list->items = NULL;
    list->count = 0;
    list->cap = 0;
}

static void run_event_loop(SOCKET listen_sock, ConnectionList *connections) {
    printf("[INFO] P2P node started.\n");
    printf("[INFO] newline-delimited protocol examples:\n");
    printf("[INFO]   HELLO|python|player1\n");
    printf("[INFO]   PLAYER_JOINED|player1  (V1: announce arrival, trigger state sync)\n");
    printf("[INFO]   INITIAL_STATE_SYNC|player1|unit_id|x|y|hp|attack|range|speed|unit_type  (V1: synchronize snapshots)\n");
    printf("[INFO]   MOVE|player1|unit_id|x|y\n");
    printf("[INFO]   ATTACK|player1|attacker_id|target_id\n");
    printf("[INFO]   STATE|player1|unit_id|x|y|hp|alive|target_id\n");

    while (1) {
        fd_set read_set;
        FD_ZERO(&read_set);
        FD_SET(listen_sock, &read_set);

        for (size_t i = 0; i < connections->count; i++) {
            FD_SET(connections->items[i].socket, &read_set);
        }

        int ready = select(0, &read_set, NULL, NULL, NULL);
        if (ready == SOCKET_ERROR) {
            printf("[ERROR] select failed: %d\n", WSAGetLastError());
            break;
        }

        if (FD_ISSET(listen_sock, &read_set)) {
            accept_new_connection(listen_sock, connections);
        }

        size_t i = 0;
        while (i < connections->count) {
            Connection *c = &connections->items[i];
            if (!FD_ISSET(c->socket, &read_set)) {
                i++;
                continue;
            }

            char recv_buf[RECV_CHUNK];
            int n = recv(c->socket, recv_buf, sizeof(recv_buf), 0);

            if (n == 0) {
                remove_connection(connections, i);
                continue;
            }

            if (n == SOCKET_ERROR) {
                printf("[WARN] recv error from %s (err=%d)\n", c->label, WSAGetLastError());
                remove_connection(connections, i);
                continue;
            }

            if (!handle_incoming_data(connections, i, recv_buf, n)) {
                remove_connection(connections, i);
                continue;
            }

            i++;
        }
    }
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("Usage: %s <listen_port> [peer_ip:peer_port ...]\n", argv[0]);
        printf("Example: %s 9001 127.0.0.1:9002 127.0.0.1:9003\n", argv[0]);
        return 1;
    }

    unsigned short listen_port = 0;
    if (!parse_port(argv[1], &listen_port)) {
        printf("[ERROR] invalid listen port: %s\n", argv[1]);
        return 1;
    }

    if (!init_winsock()) {
        return 1;
    }

    SOCKET listen_sock = init_server(listen_port);
    if (listen_sock == INVALID_SOCKET) {
        WSACleanup();
        return 1;
    }

    printf("[INFO] listening on 0.0.0.0:%u\n", listen_port);

    ConnectionList connections;
    memset(&connections, 0, sizeof(connections));

    for (int i = 2; i < argc; i++) {
        char peer_ip[64];
        unsigned short peer_port = 0;
        if (!parse_peer_target(argv[i], peer_ip, sizeof(peer_ip), &peer_port)) {
            printf("[WARN] skip invalid peer target: %s\n", argv[i]);
            continue;
        }
        connect_to_peer(&connections, peer_ip, peer_port);
    }

    run_event_loop(listen_sock, &connections);

    free_connection_list(&connections);
    closesocket(listen_sock);
    WSACleanup();
    return 0;
}
