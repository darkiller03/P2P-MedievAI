#include "peer_discovery.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <ctype.h>

#define INITIAL_PEER_CAPACITY 16

PeerList* load_peers_from_file(const char *config_file) {
    if (!config_file) {
        fprintf(stderr, "[ERROR] load_peers_from_file: config_file is NULL\n");
        return NULL;
    }

    FILE *f = fopen(config_file, "r");
    if (!f) {
        fprintf(stderr, "[ERROR] Cannot open config file: %s\n", config_file);
        return NULL;
    }

    PeerList *list = (PeerList *)malloc(sizeof(PeerList));
    if (!list) {
        perror("malloc");
        fclose(f);
        return NULL;
    }

    list->peers = (DiscoveredPeer *)malloc(INITIAL_PEER_CAPACITY * sizeof(DiscoveredPeer));
    if (!list->peers) {
        perror("malloc");
        free(list);
        fclose(f);
        return NULL;
    }

    list->count = 0;
    list->capacity = INITIAL_PEER_CAPACITY;

    char line[512];
    while (fgets(line, sizeof(line), f)) {
        // Trim whitespace
        size_t len = strlen(line);
        while (len > 0 && isspace(line[len - 1])) {
            line[--len] = '\0';
        }

        if (len == 0 || line[0] == '#') {
            continue;  // Skip empty lines and comments
        }

        // Parse: peer_ip:peer_port|player_id
        char *pipe_pos = strchr(line, '|');
        if (!pipe_pos) {
            fprintf(stderr, "[WARN] Invalid peer line (missing |): %s\n", line);
            continue;
        }

        *pipe_pos = '\0';
        const char *player_id = pipe_pos + 1;
        const char *ip_port = line;

        // Parse IP:port
        char *colon_pos = strchr(ip_port, ':');
        if (!colon_pos) {
            fprintf(stderr, "[WARN] Invalid peer address (missing :): %s\n", ip_port);
            continue;
        }

        *colon_pos = '\0';
        const char *ip = ip_port;
        const char *port_str = colon_pos + 1;

        uint16_t port = (uint16_t)atoi(port_str);
        if (port == 0) {
            fprintf(stderr, "[WARN] Invalid port number: %s\n", port_str);
            continue;
        }

        // Ensure capacity
        if (list->count >= list->capacity) {
            size_t new_cap = list->capacity * 2;
            DiscoveredPeer *new_peers = (DiscoveredPeer *)realloc(list->peers, new_cap * sizeof(DiscoveredPeer));
            if (!new_peers) {
                perror("realloc");
                break;
            }
            list->peers = new_peers;
            list->capacity = new_cap;
        }

        // Add peer
        DiscoveredPeer *peer = &list->peers[list->count];
        strncpy(peer->ip, ip, sizeof(peer->ip) - 1);
        peer->ip[sizeof(peer->ip) - 1] = '\0';
        peer->port = port;
        strncpy(peer->player_id, player_id, sizeof(peer->player_id) - 1);
        peer->player_id[sizeof(peer->player_id) - 1] = '\0';

        list->count++;
        printf("[INFO] Discovered peer: %s at %s:%u\n", player_id, ip, port);
    }

    fclose(f);
    return list;
}

void peer_list_free(PeerList *list) {
    if (!list) return;
    if (list->peers) free(list->peers);
    free(list);
}

const DiscoveredPeer* peer_list_get(const PeerList *list, size_t index) {
    if (!list || index >= list->count) {
        return NULL;
    }
    return &list->peers[index];
}

size_t peer_list_count(const PeerList *list) {
    if (!list) return 0;
    return list->count;
}
