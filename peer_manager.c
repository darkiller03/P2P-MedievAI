#include "peer_manager.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <fcntl.h>
#include <errno.h>

#define INITIAL_PEER_CAPACITY 16
#define RECV_BUFFER_SIZE 65536

PeerManager* peer_manager_new(const char *my_player_id, uint16_t my_port) {
    if (!my_player_id) {
        fprintf(stderr, "[ERROR] peer_manager_new: my_player_id is NULL\n");
        return NULL;
    }

    PeerManager *pm = (PeerManager *)malloc(sizeof(PeerManager));
    if (!pm) {
        perror("malloc");
        return NULL;
    }

    strncpy(pm->my_player_id, my_player_id, sizeof(pm->my_player_id) - 1);
    pm->my_player_id[sizeof(pm->my_player_id) - 1] = '\0';

    pm->my_port = my_port;
    pm->listen_sock = -1;

    pm->peers = (Peer *)malloc(INITIAL_PEER_CAPACITY * sizeof(Peer));
    if (!pm->peers) {
        perror("malloc");
        free(pm);
        return NULL;
    }

    pm->count = 0;
    pm->capacity = INITIAL_PEER_CAPACITY;

    return pm;
}

void peer_manager_free(PeerManager *pm) {
    if (!pm) return;

    // Close all peer connections
    for (size_t i = 0; i < pm->count; i++) {
        if (pm->peers[i].socket >= 0) {
            close(pm->peers[i].socket);
        }
        if (pm->peers[i].receiver) {
            receiver_free(pm->peers[i].receiver);
        }
    }

    if (pm->peers) free(pm->peers);
    if (pm->listen_sock >= 0) close(pm->listen_sock);
    free(pm);
}

bool peer_manager_init_listen(PeerManager *pm) {
    if (!pm) return false;

    pm->listen_sock = socket(AF_INET, SOCK_STREAM, 0);
    if (pm->listen_sock < 0) {
        perror("socket");
        return false;
    }

    // Allow reuse of address
    int reuse = 1;
    if (setsockopt(pm->listen_sock, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse)) < 0) {
        perror("setsockopt");
        close(pm->listen_sock);
        pm->listen_sock = -1;
        return false;
    }

    // Set non-blocking
    int flags = fcntl(pm->listen_sock, F_GETFL, 0);
    if (fcntl(pm->listen_sock, F_SETFL, flags | O_NONBLOCK) < 0) {
        perror("fcntl");
        close(pm->listen_sock);
        pm->listen_sock = -1;
        return false;
    }

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(pm->my_port);

    if (bind(pm->listen_sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind");
        close(pm->listen_sock);
        pm->listen_sock = -1;
        return false;
    }

    if (listen(pm->listen_sock, 5) < 0) {
        perror("listen");
        close(pm->listen_sock);
        pm->listen_sock = -1;
        return false;
    }

    printf("[INFO] P2P listening on port %u\n", pm->my_port);
    return true;
}

static bool ensure_peer_capacity(PeerManager *pm) {
    if (pm->count < pm->capacity) {
        return true;
    }

    size_t new_cap = pm->capacity * 2;
    Peer *new_peers = (Peer *)realloc(pm->peers, new_cap * sizeof(Peer));
    if (!new_peers) {
        perror("realloc");
        return false;
    }

    pm->peers = new_peers;
    pm->capacity = new_cap;
    return true;
}

bool peer_manager_connect_to_peer(PeerManager *pm, const char *peer_ip, uint16_t peer_port, const char *peer_id) {
    if (!pm || !peer_ip || !peer_id) {
        fprintf(stderr, "[ERROR] peer_manager_connect_to_peer: invalid args\n");
        return false;
    }

    // Check if already connected
    if (peer_manager_find_peer_by_id(pm, peer_id) != (size_t)-1) {
        printf("[WARN] Already connected to peer %s\n", peer_id);
        return true;
    }

    if (!ensure_peer_capacity(pm)) {
        return false;
    }

    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        perror("socket");
        return false;
    }

    // Set non-blocking
    int flags = fcntl(sock, F_GETFL, 0);
    if (fcntl(sock, F_SETFL, flags | O_NONBLOCK) < 0) {
        perror("fcntl");
        close(sock);
        return false;
    }

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(peer_port);

    if (inet_pton(AF_INET, peer_ip, &addr.sin_addr) <= 0) {
        fprintf(stderr, "[ERROR] invalid peer IP: %s\n", peer_ip);
        close(sock);
        return false;
    }

    if (connect(sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        if (errno != EINPROGRESS) {
            perror("connect");
            close(sock);
            return false;
        }
    }

    // Add peer
    Peer *peer = &pm->peers[pm->count];
    peer->socket = sock;
    peer->is_outbound = true;
    peer->receiver = receiver_new(RECV_BUFFER_SIZE);
    if (!peer->receiver) {
        close(sock);
        return false;
    }

    strncpy(peer->player_id, peer_id, sizeof(peer->player_id) - 1);
    peer->player_id[sizeof(peer->player_id) - 1] = '\0';
    peer->addr = addr;

    pm->count++;

    printf("[INFO] Connecting to peer %s at %s:%u\n", peer_id, peer_ip, peer_port);
    return true;
}

bool peer_manager_accept_inbound(PeerManager *pm) {
    if (!pm || pm->listen_sock < 0) {
        return false;
    }

    struct sockaddr_in client_addr;
    socklen_t client_addr_len = sizeof(client_addr);

    int client_sock = accept(pm->listen_sock, (struct sockaddr *)&client_addr, &client_addr_len);
    if (client_sock < 0) {
        if (errno == EAGAIN || errno == EWOULDBLOCK) {
            return false;  // No pending connection
        }
        perror("accept");
        return false;
    }

    if (!ensure_peer_capacity(pm)) {
        close(client_sock);
        return false;
    }

    // Set non-blocking
    int flags = fcntl(client_sock, F_GETFL, 0);
    if (fcntl(client_sock, F_SETFL, flags | O_NONBLOCK) < 0) {
        perror("fcntl");
        close(client_sock);
        return false;
    }

    Peer *peer = &pm->peers[pm->count];
    peer->socket = client_sock;
    peer->is_outbound = false;
    peer->receiver = receiver_new(RECV_BUFFER_SIZE);
    if (!peer->receiver) {
        close(client_sock);
        return false;
    }

    peer->addr = client_addr;
    strcpy(peer->player_id, "unknown");  // Will be set by HELLO message

    pm->count++;

    char ip_str[INET_ADDRSTRLEN];
    inet_ntop(AF_INET, &client_addr.sin_addr, ip_str, sizeof(ip_str));
    printf("[INFO] Accepted inbound connection from %s:%u\n", ip_str, ntohs(client_addr.sin_port));

    return true;
}

bool peer_manager_send_to_peer(PeerManager *pm, size_t peer_index, const Message *msg) {
    if (!pm || peer_index >= pm->count || !msg) {
        return false;
    }

    Peer *peer = &pm->peers[peer_index];
    if (peer->socket < 0) {
        return false;
    }

    if (!message_send_all(peer->socket, msg)) {
        fprintf(stderr, "[WARN] Failed to send message to peer %s\n", peer->player_id);
        // Don't close here, let upper layer decide
        return false;
    }

    return true;
}

bool peer_manager_broadcast(PeerManager *pm, size_t sender_index, const Message *msg) {
    if (!pm || !msg) {
        return false;
    }

    bool all_success = true;
    for (size_t i = 0; i < pm->count; i++) {
        if (sender_index != (size_t)-1 && i == sender_index) {
            continue;  // Don't send back to sender
        }

        if (!peer_manager_send_to_peer(pm, i, msg)) {
            all_success = false;
        }
    }

    return all_success;
}

size_t peer_manager_recv_any(PeerManager *pm) {
    if (!pm) return (size_t)-1;

    for (size_t i = 0; i < pm->count; i++) {
        Peer *peer = &pm->peers[i];
        if (peer->socket < 0) continue;

        // Try to receive data
        uint8_t buffer[RECV_BUFFER_SIZE];
        ssize_t n = recv(peer->socket, buffer, sizeof(buffer), 0);

        if (n > 0) {
            // Feed data into receiver
            int result = receiver_feed_data(peer->receiver, buffer, n);
            if (result < 0) {
                fprintf(stderr, "[ERROR] Message parsing failed for peer %s\n", peer->player_id);
                close(peer->socket);
                peer->socket = -1;
                continue;
            }

            if (result == 1) {
                // Complete message available
                return i;
            }
        } else if (n == 0) {
            // Connection closed
            printf("[INFO] Peer %s closed connection\n", peer->player_id);
            close(peer->socket);
            peer->socket = -1;
        } else {
            if (errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR) {
                perror("recv");
                close(peer->socket);
                peer->socket = -1;
            }
        }
    }

    return (size_t)-1;
}

Message* peer_manager_get_message(PeerManager *pm, size_t peer_index) {
    if (!pm || peer_index >= pm->count) {
        return NULL;
    }

    Peer *peer = &pm->peers[peer_index];
    if (!receiver_has_message(peer->receiver)) {
        return NULL;
    }

    return receiver_get_message(peer->receiver);
}

const Peer* peer_manager_get_peer(const PeerManager *pm, size_t peer_index) {
    if (!pm || peer_index >= pm->count) {
        return NULL;
    }

    return &pm->peers[peer_index];
}

size_t peer_manager_count(const PeerManager *pm) {
    if (!pm) return 0;
    return pm->count;
}

size_t peer_manager_find_peer_by_id(const PeerManager *pm, const char *player_id) {
    if (!pm || !player_id) return (size_t)-1;

    for (size_t i = 0; i < pm->count; i++) {
        if (strcmp(pm->peers[i].player_id, player_id) == 0) {
            return i;
        }
    }

    return (size_t)-1;
}

void peer_manager_close_peer(PeerManager *pm, size_t peer_index) {
    if (!pm || peer_index >= pm->count) {
        return;
    }

    Peer *peer = &pm->peers[peer_index];
    if (peer->socket >= 0) {
        close(peer->socket);
        peer->socket = -1;
    }
}
