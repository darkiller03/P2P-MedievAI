#include "ipc_server.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>

#ifdef _WIN32
    #include <windows.h>
    #include <io.h>
#else
    #include <sys/socket.h>
    #include <sys/un.h>
    #include <sys/stat.h>
#endif

#define RECV_BUFFER_SIZE 65536

IPCServer* ipc_server_new(const char *player_id) {
    if (!player_id) {
        fprintf(stderr, "[ERROR] ipc_server_new: player_id is NULL\n");
        return NULL;
    }

    IPCServer *server = (IPCServer *)malloc(sizeof(IPCServer));
    if (!server) {
        perror("malloc");
        return NULL;
    }

    memset(server, 0, sizeof(IPCServer));
    strncpy(server->player_id, player_id, sizeof(server->player_id) - 1);
    server->player_id[sizeof(server->player_id) - 1] = '\0';
    server->conn.fd = -1;

#ifdef _WIN32
    // Named pipe name on Windows
    snprintf(server->conn.pipe_name, sizeof(server->conn.pipe_name),
             "\\\\.\\pipe\\p2p_game_%s", player_id);
#else
    // Unix socket path
    snprintf(server->conn.pipe_name, sizeof(server->conn.pipe_name),
             "/tmp/p2p_game_%s.sock", player_id);
#endif

    return server;
}

void ipc_server_free(IPCServer *server) {
    if (!server) return;

    ipc_server_disconnect(server);

    if (server->conn.receiver) {
        receiver_free(server->conn.receiver);
        server->conn.receiver = NULL;
    }

#ifndef _WIN32
    // Clean up Unix socket file
    unlink(server->conn.pipe_name);
#endif

    free(server);
}

bool ipc_server_init(IPCServer *server) {
    if (!server) {
        return false;
    }

    server->conn.receiver = receiver_new(RECV_BUFFER_SIZE);
    if (!server->conn.receiver) {
        return false;
    }

#ifdef _WIN32
    // Windows named pipe
    HANDLE hPipe = CreateNamedPipeA(
        server->conn.pipe_name,
        PIPE_ACCESS_DUPLEX | FILE_FLAG_OVERLAPPED,
        PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT,
        1,          // max instances
        4096,       // output buffer
        4096,       // input buffer
        0,          // default timeout
        NULL        // default security
    );

    if (hPipe == INVALID_HANDLE_VALUE) {
        fprintf(stderr, "[ERROR] CreateNamedPipeA failed: %lu\n", GetLastError());
        return false;
    }

    server->conn.fd = (int)(intptr_t)hPipe;
    printf("[INFO] IPC named pipe created: %s\n", server->conn.pipe_name);

#else
    // Unix domain socket
    int sock = socket(AF_UNIX, SOCK_STREAM, 0);
    if (sock < 0) {
        perror("socket");
        return false;
    }

    // Remove old socket file if exists
    unlink(server->conn.pipe_name);

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, server->conn.pipe_name, sizeof(addr.sun_path) - 1);

    if (bind(sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind");
        close(sock);
        return false;
    }

    if (listen(sock, 1) < 0) {
        perror("listen");
        close(sock);
        unlink(server->conn.pipe_name);
        return false;
    }

    // Set non-blocking
    int flags = fcntl(sock, F_GETFL, 0);
    if (fcntl(sock, F_SETFL, flags | O_NONBLOCK) < 0) {
        perror("fcntl");
        close(sock);
        unlink(server->conn.pipe_name);
        return false;
    }

    server->conn.fd = sock;
    printf("[INFO] IPC socket created: %s\n", server->conn.pipe_name);

#endif

    return true;
}

bool ipc_server_accept(IPCServer *server) {
    if (!server || server->is_connected) {
        return false;
    }

#ifdef _WIN32
    // Windows named pipe - wait for client
    HANDLE hPipe = (HANDLE)(intptr_t)server->conn.fd;
    
    OVERLAPPED overlap;
    memset(&overlap, 0, sizeof(overlap));
    overlap.hEvent = CreateEventA(NULL, TRUE, FALSE, NULL);

    BOOL connected = ConnectNamedPipe(hPipe, &overlap);
    if (!connected && GetLastError() != ERROR_IO_PENDING) {
        if (GetLastError() != ERROR_PIPE_CONNECTED) {
            fprintf(stderr, "[WARN] ConnectNamedPipe failed: %lu\n", GetLastError());
            CloseHandle(overlap.hEvent);
            return false;
        }
    }

    // For this simple implementation, we'll just assume connection succeeds
    server->is_connected = true;
    printf("[INFO] Python client connected via IPC\n");
    CloseHandle(overlap.hEvent);

#else
    // Unix domain socket - accept connection
    struct sockaddr_un client_addr;
    socklen_t client_addr_len = sizeof(client_addr);

    int client_sock = accept(server->conn.fd, (struct sockaddr *)&client_addr, &client_addr_len);
    if (client_sock < 0) {
        if (errno == EAGAIN || errno == EWOULDBLOCK) {
            return false;
        }
        perror("accept");
        return false;
    }

    // Set non-blocking
    int flags = fcntl(client_sock, F_GETFL, 0);
    if (fcntl(client_sock, F_SETFL, flags | O_NONBLOCK) < 0) {
        perror("fcntl");
        close(client_sock);
        return false;
    }

    // Store client socket
    if (server->conn.fd >= 0) {
        close(server->conn.fd);
    }
    server->conn.fd = client_sock;
    server->is_connected = true;
    printf("[INFO] Python client connected via IPC\n");

#endif

    return true;
}

bool ipc_server_recv(IPCServer *server) {
    if (!server || !server->is_connected) {
        return false;
    }

    if (receiver_has_message(server->conn.receiver)) {
        return true;  // Already have a complete message
    }

#ifdef _WIN32
    // Windows named pipe
    HANDLE hPipe = (HANDLE)(intptr_t)server->conn.fd;
    uint8_t buffer[RECV_BUFFER_SIZE];
    DWORD bytes_read = 0;

    BOOL success = ReadFile(hPipe, buffer, sizeof(buffer), &bytes_read, NULL);
    if (!success) {
        DWORD err = GetLastError();
        if (err != ERROR_NO_DATA && err != ERROR_INVALID_HANDLE) {
            fprintf(stderr, "[WARN] ReadFile failed: %lu\n", err);
        }
        return false;
    }

    if (bytes_read == 0) {
        printf("[INFO] Python client disconnected\n");
        server->is_connected = false;
        return false;
    }

#else
    // Unix socket
    uint8_t buffer[RECV_BUFFER_SIZE];
    ssize_t n = recv(server->conn.fd, buffer, sizeof(buffer), 0);

    if (n < 0) {
        if (errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR) {
            perror("recv");
            server->is_connected = false;
        }
        return false;
    }

    if (n == 0) {
        printf("[INFO] Python client disconnected\n");
        server->is_connected = false;
        return false;
    }

    size_t bytes_read = (size_t)n;

#endif

    // Feed data into receiver
    int result = receiver_feed_data(server->conn.receiver, buffer, bytes_read);
    if (result < 0) {
        fprintf(stderr, "[ERROR] IPC message parsing failed\n");
        server->is_connected = false;
        return false;
    }

    return result == 1;  // Return true if complete message available
}

Message* ipc_server_get_message(IPCServer *server) {
    if (!server || !receiver_has_message(server->conn.receiver)) {
        return NULL;
    }

    return receiver_get_message(server->conn.receiver);
}

bool ipc_server_send(IPCServer *server, const Message *msg) {
    if (!server || !server->is_connected || !msg) {
        return false;
    }

#ifdef _WIN32
    // Windows named pipe
    HANDLE hPipe = (HANDLE)(intptr_t)server->conn.fd;
    
    // Create buffer with header + payload
    size_t total_len = MSG_HEADER_SIZE + msg->len;
    uint8_t *buffer = (uint8_t *)malloc(total_len);
    if (!buffer) {
        perror("malloc");
        return false;
    }

    // Write header (network byte order)
    uint32_t len_net = htonl((uint32_t)msg->len);
    memcpy(buffer, &len_net, MSG_HEADER_SIZE);
    memcpy(buffer + MSG_HEADER_SIZE, msg->data, msg->len);

    DWORD bytes_written = 0;
    BOOL success = WriteFile(hPipe, buffer, (DWORD)total_len, &bytes_written, NULL);
    free(buffer);

    if (!success || bytes_written != total_len) {
        fprintf(stderr, "[WARN] WriteFile failed\n");
        return false;
    }

#else
    // Unix socket
    if (!message_send_all(server->conn.fd, msg)) {
        fprintf(stderr, "[WARN] Failed to send IPC message\n");
        return false;
    }

#endif

    return true;
}

bool ipc_server_is_connected(const IPCServer *server) {
    if (!server) return false;
    return server->is_connected;
}

void ipc_server_disconnect(IPCServer *server) {
    if (!server) return;

    if (server->conn.fd >= 0) {
#ifdef _WIN32
        HANDLE hPipe = (HANDLE)(intptr_t)server->conn.fd;
        FlushFileBuffers(hPipe);
        DisconnectNamedPipe(hPipe);
        CloseHandle(hPipe);
#else
        close(server->conn.fd);
#endif
        server->conn.fd = -1;
    }

    server->is_connected = false;
}
