#include "tcp_relay_server.h"
#include "server.h"
#include "connection.h"

int init_server(unsigned short listen_port) {
    int listen_sock = socket(AF_INET, SOCK_STREAM, 0);
    if (listen_sock == -1) {
        printf("[ERROR] socket failed: %d\n", errno);
        return -1;
    }

    int opt = 1;
    if (setsockopt(listen_sock, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) == -1) {
        printf("[WARN] SO_REUSEADDR failed: %d\n", errno);
    }

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(listen_port);

    if (bind(listen_sock, (struct sockaddr *)&addr, sizeof(addr)) == -1) {
        printf("[ERROR] bind failed on port %u (err=%d)\n", listen_port, errno);
        close(listen_sock);
        return -1;
    }

    if (listen(listen_sock, SOMAXCONN) == -1) {
        printf("[ERROR] listen failed (err=%d)\n", errno);
        close(listen_sock);
        return -1;
    }

    return listen_sock;
}

bool accept_new_connection(int listen_sock, ConnectionList *list) {
    struct sockaddr_in addr;
    socklen_t addr_len = sizeof(addr);
    int incoming = accept(listen_sock, (struct sockaddr *)&addr, &addr_len);
    if (incoming == -1) {
        printf("[WARN] accept failed (err=%d)\n", errno);
        return false;
    }

    char label[64];
    snprintf(label, sizeof(label), "%s:%u", inet_ntoa(addr.sin_addr), ntohs(addr.sin_port));

    if (!append_connection(list, incoming, label)) {
        printf("[ERROR] cannot track new connection %s\n", label);
        close(incoming);
        return false;
    }

    printf("[INFO] accepted connection: %s (total=%llu)\n", label, (unsigned long long)list->count);
    return true;
}

bool connect_to_peer(ConnectionList *list, const char *ip, unsigned short port) {
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock == -1) {
        printf("[WARN] socket() failed for peer %s:%u\n", ip, port);
        return false;
    }

    struct sockaddr_in peer_addr;
    memset(&peer_addr, 0, sizeof(peer_addr));
    peer_addr.sin_family = AF_INET;
    peer_addr.sin_port = htons(port);

    if (inet_pton(AF_INET, ip, &peer_addr.sin_addr) != 1) {
        printf("[WARN] invalid peer address: %s\n", ip);
        close(sock);
        return false;
    }

    if (connect(sock, (struct sockaddr *)&peer_addr, sizeof(peer_addr)) == -1) {
        printf("[WARN] connect failed to %s:%u (err=%d)\n", ip, port, errno);
        close(sock);
        return false;
    }

    char label[64];
    snprintf(label, sizeof(label), "%s:%u", ip, port);

    if (!append_connection(list, sock, label)) {
        printf("[ERROR] cannot track outbound peer %s\n", label);
        close(sock);
        return false;
    }

    printf("[INFO] connected to peer: %s (total=%llu)\n", label, (unsigned long long)list->count);
    return true;
}

void run_event_loop(int listen_sock, ConnectionList *connections) {
    printf("[INFO] P2P node started.\n");
    printf("[INFO] newline-delimited protocol examples:\n");
    printf("[INFO]   MOVE|player1|10|5\n");
    printf("[INFO]   ATTACK|player1|enemy2\n");

    while (1) {
        fd_set read_set;
        FD_ZERO(&read_set);
        FD_SET(listen_sock, &read_set);

        for (size_t i = 0; i < connections->count; i++) {
            FD_SET(connections->items[i].socket, &read_set);
        }

        int ready = select(FD_SETSIZE, &read_set, NULL, NULL, NULL);
        if (ready == -1) {
            printf("[ERROR] select failed: %d\n", errno);
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

            if (n == -1) {
                printf("[WARN] recv error from %s (err=%d)\n", c->label, errno);
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