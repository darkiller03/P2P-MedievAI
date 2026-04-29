#ifndef PEER_DISCOVERY_H
#define PEER_DISCOVERY_H

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

/**
 * Peer discovery configuration
 * Reads peers.conf file to discover initial peer connections
 */

typedef struct {
    char ip[64];
    uint16_t port;
    char player_id[64];
} DiscoveredPeer;

typedef struct {
    DiscoveredPeer *peers;
    size_t count;
    size_t capacity;
} PeerList;

/**
 * Load peers from configuration file (peers.conf)
 * Format:
 *   my_player_id=player_a
 *   my_port=9001
 *   peers=127.0.0.1:9002|player_b 127.0.0.1:9003|player_c
 * 
 * Returns allocated PeerList or NULL on error
 */
PeerList* load_peers_from_file(const char *config_file);

/**
 * Free peer list
 */
void peer_list_free(PeerList *list);

/**
 * Get discovered peer by index
 */
const DiscoveredPeer* peer_list_get(const PeerList *list, size_t index);

/**
 * Get number of discovered peers
 */
size_t peer_list_count(const PeerList *list);

#endif // PEER_DISCOVERY_H
