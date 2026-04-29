#include "tcp_relay_server.h"
#include "server.h"
#include "connection.h"

socket_t init_server(unsigned short listen_port) {
    socket_t listen_sock = socket(AF_INET, SOCK_STREAM, 0);
#ifdef _WIN32
    if (listen_sock == INVALID_SOCKET) {
#else
    if (listen_sock == -1) {
#endif
        printf("[ERROR] socket failed: %d\n", SOCKET_ERRNO);
        return (socket_t)-1;
    }

    int opt = 1;
    if (setsockopt(listen_sock, SOL_SOCKET, SO_REUSEADDR, (const char *)&opt, sizeof(opt))
#ifdef _WIN32
        == SOCKET_ERROR
#else
        == -1
#endif
    ) {
        printf("[WARN] SO_REUSEADDR failed: %d\n", SOCKET_ERRNO);
    }

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(listen_port);

    if (bind(listen_sock, (struct sockaddr *)&addr, sizeof(addr))
#ifdef _WIN32
        == SOCKET_ERROR
#else
        == -1
#endif
    ) {
        printf("[ERROR] bind failed on port %u (err=%d)\n", listen_port, SOCKET_ERRNO);
        close(listen_sock);
        return (socket_t)-1;
    }

    if (listen(listen_sock, SOMAXCONN)
#ifdef _WIN32
        == SOCKET_ERROR
#else
        == -1
#endif
    ) {
        printf("[ERROR] listen failed (err=%d)\n", SOCKET_ERRNO);
        close(listen_sock);
        return (socket_t)-1;
    }

    return listen_sock;
}

bool accept_new_connection(socket_t listen_sock, ConnectionList *list) {
    struct sockaddr_in addr;
    socklen_t addr_len = sizeof(addr);
    socket_t incoming = accept(listen_sock, (struct sockaddr *)&addr, &addr_len);
#ifdef _WIN32
    if (incoming == INVALID_SOCKET) {
#else
    if (incoming == -1) {
#endif
        printf("[WARN] accept failed (err=%d)\n", SOCKET_ERRNO);
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
    socket_t sock = socket(AF_INET, SOCK_STREAM, 0);
#ifdef _WIN32
    if (sock == INVALID_SOCKET) {
#else
    if (sock == -1) {
#endif
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

    if (connect(sock, (struct sockaddr *)&peer_addr, sizeof(peer_addr))
#ifdef _WIN32
        == SOCKET_ERROR
#else
        == -1
#endif
    ) {
        printf("[WARN] connect failed to %s:%u (err=%d)\n", ip, port, SOCKET_ERRNO);
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

void run_event_loop(socket_t listen_sock, ConnectionList *connections) {
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
        if (ready
#ifdef _WIN32
            == SOCKET_ERROR
#else
            == -1
#endif
        ) {
            printf("[ERROR] select failed: %d\n", SOCKET_ERRNO);
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

            if (n
#ifdef _WIN32
                == SOCKET_ERROR
#else
                == -1
#endif
            ) {
                printf("[WARN] recv error from %s (err=%d)\n", c->label, SOCKET_ERRNO);
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