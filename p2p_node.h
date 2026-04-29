#ifndef P2P_NODE_H
#define P2P_NODE_H

#include "peer_manager.h"
#include "ipc_server.h"
#include "conflict_resolution.h"
#include <stdbool.h>

/**
 * Main P2P Game Node
 * 
 * Coordinates:
 * - Peer connections (P2P mesh)
 * - IPC with Python
 * - Conflict resolution
 * - State synchronization
 */

typedef struct {
    PeerManager *peers;
    IPCServer *ipc;
    ClockManager *clock;
    
    bool running;
} P2PNode;

/**
 * Create P2P node
 */
P2PNode* p2p_node_new(const char *player_id, uint16_t listen_port);

/**
 * Free P2P node
 */
void p2p_node_free(P2PNode *node);

/**
 * Initialize node (create listening sockets, etc.)
 */
bool p2p_node_init(P2PNode *node);

/**
 * Connect to initial peers from configuration
 */
bool p2p_node_connect_initial_peers(P2PNode *node, const char *config_file);

/**
 * Run main event loop
 * Returns when running is set to false
 */
void p2p_node_run(P2PNode *node);

/**
 * Signal node to stop
 */
void p2p_node_stop(P2PNode *node);

#endif // P2P_NODE_H
