#ifndef IPC_SERVER_H
#define IPC_SERVER_H

#include "message_protocol.h"
#include <stdint.h>
#include <stdbool.h>

/**
 * IPC Server: Handles communication between Python and C process
 * 
 * On Windows: Uses named pipes (\\.\pipe\...)
 * On Unix: Uses Unix domain sockets (/tmp/...)
 */

typedef struct {
    int fd;                         // File descriptor (socket/pipe)
    MessageReceiver *receiver;      // For parsing messages from Python
    char pipe_name[256];            // Name/path of IPC endpoint
} IPCConnection;

typedef struct {
    IPCConnection conn;
    bool is_connected;
    char player_id[64];             // Will be set by first message from Python
} IPCServer;

/**
 * Create IPC server
 * player_id: player ID (used to name the IPC endpoint)
 * Returns NULL on failure
 */
IPCServer* ipc_server_new(const char *player_id);

/**
 * Free IPC server
 */
void ipc_server_free(IPCServer *server);

/**
 * Initialize IPC server (create named pipe/socket and listen)
 * Returns true on success
 */
bool ipc_server_init(IPCServer *server);

/**
 * Try to accept connection from Python
 * Returns true if connection established
 */
bool ipc_server_accept(IPCServer *server);

/**
 * Try to receive data from Python
 * Returns true if complete message received (call ipc_server_get_message)
 */
bool ipc_server_recv(IPCServer *server);

/**
 * Get message from Python (only valid after ipc_server_recv returns true)
 */
Message* ipc_server_get_message(IPCServer *server);

/**
 * Send message to Python
 * Returns true on success
 */
bool ipc_server_send(IPCServer *server, const Message *msg);

/**
 * Check if Python is connected
 */
bool ipc_server_is_connected(const IPCServer *server);

/**
 * Disconnect Python client
 */
void ipc_server_disconnect(IPCServer *server);

#endif // IPC_SERVER_H
