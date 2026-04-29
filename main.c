#include "server.h"
#include "connection.h"
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>

// Global state for signal handler
static int g_peer_listen_sock = -1;
static int g_ipc_listen_sock = -1;
static ConnectionList g_peer_connections;
static ConnectionList g_ipc_connections;
static volatile int g_running = 1;

static void signal_handler(int sig) {
    printf("\n[INFO] Received signal %d, shutting down...\n", sig);
    g_running = 0;
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <node_port> [peer_addr:port ...]\n", argv[0]);
        fprintf(stderr, "Example: %s 9001\n", argv[0]);
        fprintf(stderr, "Example: %s 9002 127.0.0.1:9001\n", argv[0]);
        return 1;
    }

    // Parse node's own port
    unsigned short node_port = (unsigned short)atoi(argv[1]);
    if (node_port == 0) {
        fprintf(stderr, "[ERROR] Invalid port number: %s\n", argv[1]);
        return 1;
    }

    // Initialize connection lists
    g_peer_connections.items = NULL;
    g_peer_connections.count = 0;
    g_peer_connections.cap = 0;

    g_ipc_connections.items = NULL;
    g_ipc_connections.count = 0;
    g_ipc_connections.cap = 0;

    // Create peer listening socket (other P2P nodes connect here)
    g_peer_listen_sock = init_server(node_port);
    if (g_peer_listen_sock == -1) {
        fprintf(stderr, "[ERROR] Failed to create peer listening socket on port %u\n", node_port);
        return 1;
    }
    printf("[INFO] Peer listening socket on port %u\n", node_port);

    // Create IPC listening socket (local Python process connects here)
    unsigned short ipc_port = node_port + 1000;  // Offset IPC port
    g_ipc_listen_sock = init_server(ipc_port);
    if (g_ipc_listen_sock == -1) {
        fprintf(stderr, "[ERROR] Failed to create IPC listening socket on port %u\n", ipc_port);
        close(g_peer_listen_sock);
        return 1;
    }
    printf("[INFO] IPC listening socket on port %u\n", ipc_port);

    // Setup signal handlers
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

    // Connect to initial peers (if provided)
    for (int i = 2; i < argc; i++) {
        char ip[64];
        unsigned short port;
        
        // Parse "ip:port" format
        if (sscanf(argv[i], "%63[^:]:%hu", ip, &port) != 2) {
            fprintf(stderr, "[WARN] Invalid peer format '%s', skipping\n", argv[i]);
            continue;
        }

        printf("[INFO] Connecting to peer %s:%u\n", ip, port);
        if (!connect_to_peer(&g_peer_connections, ip, port)) {
            fprintf(stderr, "[WARN] Failed to connect to %s:%u\n", ip, port);
        }
    }

    printf("[INFO] Starting P2P node (peer_port=%u, ipc_port=%u)\n", node_port, ipc_port);
    printf("[INFO] Python client should connect to port %u\n", ipc_port);

    // Run the main event loop
    run_event_loop(g_peer_listen_sock, g_ipc_listen_sock, 
                   &g_peer_connections, &g_ipc_connections, node_port);

    // Cleanup
    printf("[INFO] Shutting down...\n");
    close(g_peer_listen_sock);
    close(g_ipc_listen_sock);
    free_connection_list(&g_peer_connections);
    free_connection_list(&g_ipc_connections);

    printf("[INFO] Node shut down cleanly.\n");
    return 0;
}
