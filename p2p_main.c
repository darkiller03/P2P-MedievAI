#include "p2p_node.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>

static P2PNode *g_node = NULL;

static void signal_handler(int sig) {
    printf("\n[INFO] Received signal %d, shutting down...\n", sig);
    if (g_node) {
        p2p_node_stop(g_node);
    }
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("Usage: %s <player_id> [listen_port] [config_file]\n", argv[0]);
        printf("  player_id:    Unique identifier (e.g., 'player_a')\n");
        printf("  listen_port:  Port to listen on (default: 9001)\n");
        printf("  config_file:  peers.conf file (default: ./peers.conf)\n");
        printf("\nExample: %s player_a 9001 peers.conf\n", argv[0]);
        return 1;
    }

    const char *player_id = argv[1];
    uint16_t listen_port = 9001;
    const char *config_file = "peers.conf";

    if (argc > 2) {
        listen_port = (uint16_t)atoi(argv[2]);
    }
    if (argc > 3) {
        config_file = argv[3];
    }

    // Setup signal handlers
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

    // Create and initialize node
    g_node = p2p_node_new(player_id, listen_port);
    if (!g_node) {
        fprintf(stderr, "[ERROR] Failed to create P2P node\n");
        return 1;
    }

    if (!p2p_node_init(g_node)) {
        fprintf(stderr, "[ERROR] Failed to initialize P2P node\n");
        p2p_node_free(g_node);
        return 1;
    }

    // Connect to initial peers
    if (!p2p_node_connect_initial_peers(g_node, config_file)) {
        fprintf(stderr, "[WARN] Some peers failed to connect\n");
    }

    // Run event loop
    p2p_node_run(g_node);

    // Cleanup
    p2p_node_free(g_node);
    return 0;
}
