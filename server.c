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

bool accept_new_connection(int listen_sock, ConnectionList *list, bool is_local_client) {
    struct sockaddr_in addr;
    socklen_t addr_len = sizeof(addr);
    int incoming = accept(listen_sock, (struct sockaddr *)&addr, &addr_len);
    if (incoming == -1) {
        printf("[WARN] accept failed (err=%d)\n", errno);
        return false;
    }

    char label[64];
    snprintf(label, sizeof(label), "%s:%u", inet_ntoa(addr.sin_addr), ntohs(addr.sin_port));

    if (!append_connection(list, incoming, label, is_local_client)) {
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

    if (!append_connection(list, sock, label, false)) {
        printf("[ERROR] cannot track outbound peer %s\n", label);
        close(sock);
        return false;
    }

    printf("[INFO] connected to peer: %s (total=%llu)\n", label, (unsigned long long)list->count);
    return true;
}

void run_event_loop(int peer_listen_sock, int ipc_listen_sock, ConnectionList *peer_connections, ConnectionList *ipc_connections, unsigned short node_port) {
    printf("[INFO] P2P node started.\n");
    printf("[INFO] newline-delimited protocol examples:\n");
    printf("[INFO]   MOVE|player1|10|5\n");
    printf("[INFO]   ATTACK|player1|enemy2\n");
    printf("[INFO] local Python client connects on IPC port separately from peer network.\n");

    while (1) {
        fd_set read_set;
        FD_ZERO(&read_set);
        FD_SET(peer_listen_sock, &read_set);
        FD_SET(ipc_listen_sock, &read_set);

        int max_fd = peer_listen_sock > ipc_listen_sock ? peer_listen_sock : ipc_listen_sock;

        for (size_t i = 0; i < peer_connections->count; i++) {
            FD_SET(peer_connections->items[i].socket, &read_set);
            if (peer_connections->items[i].socket > max_fd) {
                max_fd = peer_connections->items[i].socket;
            }
        }

        for (size_t i = 0; i < ipc_connections->count; i++) {
            FD_SET(ipc_connections->items[i].socket, &read_set);
            if (ipc_connections->items[i].socket > max_fd) {
                max_fd = ipc_connections->items[i].socket;
            }
        }

        int ready = select(max_fd + 1, &read_set, NULL, NULL, NULL);
        if (ready == -1) {
            printf("[ERROR] select failed: %d\n", errno);
            break;
        }

        if (FD_ISSET(peer_listen_sock, &read_set)) {
            accept_new_connection(peer_listen_sock, peer_connections, false);
        }

        if (FD_ISSET(ipc_listen_sock, &read_set)) {
            accept_new_connection(ipc_listen_sock, ipc_connections, true);
        }

        size_t i = 0;
        while (i < peer_connections->count) {
            Connection *c = &peer_connections->items[i];
            if (!FD_ISSET(c->socket, &read_set)) {
                i++;
                continue;
            }

            char recv_buf[RECV_CHUNK];
            int n = recv(c->socket, recv_buf, sizeof(recv_buf), 0);

            if (n == 0) {
                remove_connection(peer_connections, i);
                continue;
            }

            if (n == -1) {
                printf("[WARN] recv error from %s (err=%d)\n", c->label, errno);
                remove_connection(peer_connections, i);
                continue;
            }

            if (!handle_peer_incoming_data(peer_connections, ipc_connections, i, recv_buf, n)) {
                remove_connection(peer_connections, i);
                continue;
            }

            i++;
        }

        i = 0;
        while (i < ipc_connections->count) {
            Connection *c = &ipc_connections->items[i];
            if (!FD_ISSET(c->socket, &read_set)) {
                i++;
                continue;
            }

            char recv_buf[RECV_CHUNK];
            int n = recv(c->socket, recv_buf, sizeof(recv_buf), 0);

            if (n == 0) {
                remove_connection(ipc_connections, i);
                continue;
            }

            if (n == -1) {
                printf("[WARN] recv error from %s (err=%d)\n", c->label, errno);
                remove_connection(ipc_connections, i);
                continue;
            }

            if (!handle_ipc_incoming_data(peer_connections, ipc_connections, i, recv_buf, n)) {
                remove_connection(ipc_connections, i);
                continue;
            }

            i++;
        }
    }
}
