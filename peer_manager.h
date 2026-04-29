#ifndef PEER_MANAGER_H
#define PEER_MANAGER_H

#include "message_protocol.h"
#include <stdint.h>
#include <stdbool.h>
#include <netinet/in.h>

/**
 * Manages direct P2P connections to peer nodes
 * 
 * Each peer is directly connected to all other peers.
 * This is a mesh topology (not a relay).
 */

typedef struct Peer {
    int socket;                  // -1 if not connected
    char player_id[64];
    struct sockaddr_in addr;
    MessageReceiver *receiver;   // For parsing incoming messages
    bool is_outbound;            // true if we initiated connection, false if peer connected to us
} Peer;

typedef struct {
    Peer *peers;
    size_t count;
    size_t capacity;
    
    // Our own identity
    char my_player_id[64];
    uint16_t my_port;
    
    // Listening socket for inbound connections
    int listen_sock;
} PeerManager;

/**
 * Create peer manager
 * my_player_id: unique ID for this node (e.g., "player_a")
 * my_port: port to listen for incoming peer connections
 */
PeerManager* peer_manager_new(const char *my_player_id, uint16_t my_port);

/**
 * Free peer manager
 */
void peer_manager_free(PeerManager *pm);

/**
 * Initialize listening socket
 * Returns true on success
 */
bool peer_manager_init_listen(PeerManager *pm);

/**
 * Connect to a peer
 * Returns true on success
 */
bool peer_manager_connect_to_peer(PeerManager *pm, const char *peer_ip, uint16_t peer_port, const char *peer_id);

/**
 * Accept new inbound connection
 * Returns true if new peer was added, false if no pending connection
 */
bool peer_manager_accept_inbound(PeerManager *pm);

/**
 * Send message to specific peer
 * Returns true on success
 */
bool peer_manager_send_to_peer(PeerManager *pm, size_t peer_index, const Message *msg);

/**
 * Broadcast message to all peers except sender
 * sender_index: use (size_t)-1 if message originates locally
 */
bool peer_manager_broadcast(PeerManager *pm, size_t sender_index, const Message *msg);

/**
 * Check if any peer has incoming data and parse it
 * Returns peer index if message received, (size_t)-1 if no complete message
 * Caller must call peer_manager_get_message() to retrieve the message
 */
size_t peer_manager_recv_any(PeerManager *pm);

/**
 * Get parsed message from peer (only valid after peer_manager_recv_any returns a peer index)
 */
Message* peer_manager_get_message(PeerManager *pm, size_t peer_index);

/**
 * Get peer info
 */
const Peer* peer_manager_get_peer(const PeerManager *pm, size_t peer_index);

/**
 * Get number of connected peers
 */
size_t peer_manager_count(const PeerManager *pm);

/**
 * Get index of peer by player_id
 * Returns (size_t)-1 if not found
 */
size_t peer_manager_find_peer_by_id(const PeerManager *pm, const char *player_id);

/**
 * Close connection to specific peer
 */
void peer_manager_close_peer(PeerManager *pm, size_t peer_index);

#endif // PEER_MANAGER_H
